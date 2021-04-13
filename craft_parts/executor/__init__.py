# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2021 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Definitions and helpers for the action executor."""

import contextlib
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union

from craft_parts import callbacks, layers, packages
from craft_parts.actions import Action, ActionType
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part, part_list_by_name
from craft_parts.steps import Step
from craft_parts.utils import os_utils

from .collisions import check_for_stage_collisions
from .part_handler import PartHandler

logger = logging.getLogger(__name__)


class Executor:
    """Execute lifecycle actions."""

    def __init__(
        self,
        *,
        part_list: List[Part],
        project_info: ProjectInfo,
        extra_build_packages: List[str] = None,
        extra_build_snaps: List[str] = None,
        base_packages: List[str] = None,
        base_dir: Union[str, Path] = None,
    ):
        self._part_list = part_list
        self._project_info = project_info
        self._base_packages = base_packages
        self._extra_build_packages = extra_build_packages
        self._extra_build_snaps = extra_build_snaps
        self._handler: Dict[str, PartHandler] = {}
        self._layer_stack: Optional[layers.BasePackagesLayerStack]

        if base_dir:
            self._layer_stack = layers.BasePackagesLayerStack(
                root=project_info.dirs.layer_dir,
                base=Path(base_dir),
            )
        else:
            self._layer_stack = None

    def prologue(self):
        """Prepare the execution environment."""

        self._install_build_packages()
        self._install_build_snaps()

        if self._layer_stack and not self._layer_stack.has_state():
            self._install_base_packages()

        callbacks.run_prologue(self._project_info, part_list=self._part_list)

    def epilogue(self):
        """Finish and clean the execution environment."""
        callbacks.run_epilogue(self._project_info, part_list=self._part_list)

    def run_action(self, action: Action, *, part: Part):
        """Execute the given action for a part using the provided step information."""

        logger.debug("execute action %s:%s", part.name, action)

        if action.type == ActionType.SKIP:
            logger.debug("Skip execution of %s (because %s)", action, action.reason)
            return

        if action.step == Step.STAGE:
            check_for_stage_collisions(self._part_list)

        self._create_part_handler(part)

        handler = self._handler[part.name]
        handler.run_action(action)

    def clean(self, initial_step: Step, *, part_names: List[str] = None):
        """Clean the given parts, or all parts if none is specified."""

        if not part_names:
            self._clean_all_parts(step=initial_step)
            return

        selected_parts = part_list_by_name(part_names, self._part_list)

        selected_steps = [initial_step] + initial_step.next_steps()
        selected_steps.reverse()

        for part in selected_parts:
            self._create_part_handler(part)
            handler = self._handler[part.name]

            for step in selected_steps:
                handler.clean_step(step=step)

    def clean_base_packages_layers(self):
        """Remove base packages state and files."""
        if self._layer_stack:
            self._layer_stack.clean_state()
            self._layer_stack.package_layers.clean()

    def load_base_packages_state(self) -> Optional[layers.BasePackagesLayerState]:
        """Obtain the base packages installation state."""
        if self._layer_stack:
            return self._layer_stack.load_state()
        return None

    def _clean_all_parts(self, *, step: Step):
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(self._project_info.prime_dir)
            if step <= Step.STAGE:
                shutil.rmtree(self._project_info.stage_dir)
            if step <= Step.PULL:
                shutil.rmtree(self._project_info.parts_dir)

    def _create_part_handler(self, part: Part):
        if part.name not in self._handler:
            # create the part handler for a new part
            self._handler[part.name] = PartHandler(
                part,
                part_info=PartInfo(self._project_info, part),
                part_list=self._part_list,
            )

    def refresh_base_packages_list(self):
        """Update the list of available base packages."""
        if self._layer_stack:
            with layers.BasePackagesOverlay(self._layer_stack.pkglist_layers) as ovl:
                ovl.refresh_package_list()

    def resolve_base_packages_dependencies(self, package_list: List[str]) -> List[str]:
        """Compute all the dependencies for the given list of base packages."""
        resolved_packages: List[str] = []
        if self._base_packages and self._layer_stack:
            with layers.BasePackagesOverlay(self._layer_stack.pkglist_layers) as ovl:
                resolved_packages = ovl.resolve_dependencies(self._base_packages)

            logger.debug("resolved base packages: %s", resolved_packages)

        return resolved_packages

    def _install_base_packages(self):
        if self._base_packages and self._layer_stack:
            installed_packages: List[str] = []
            with layers.BasePackagesOverlay(self._layer_stack.package_layers) as ovl:
                installed_packages = ovl.install_packages(self._base_packages)

            logger.debug("installed base packages: %s", installed_packages)

            self.clean(Step.STAGE)
            with layers.BasePackagesOverlay(self._layer_stack.combined_layers) as ovl:
                ovl.export_overlay(self._project_info.stage_dir)
                ovl.export_overlay(self._project_info.prime_dir)

            self._layer_stack.write_state(base_packages=installed_packages)

    def _install_build_packages(self):
        for part in self._part_list:
            self._create_part_handler(part)

        build_packages = set()
        for _, handler in self._handler.items():
            build_packages.update(handler.build_packages)

        if self._extra_build_packages:
            build_packages.update(self._extra_build_packages)

        packages.Repository.install_build_packages(sorted(build_packages))

    def _install_build_snaps(self):
        build_snaps = set()
        for _, handler in self._handler.items():
            build_snaps.update(handler.build_snaps)

        if self._extra_build_snaps:
            build_snaps.update(self._extra_build_snaps)

        if not build_snaps:
            return

        if os_utils.is_inside_container():
            logger.warning(
                (
                    "The following snaps are required but not installed as the "
                    "application is running inside docker or podman container: %s.\n"
                    "Please ensure the environment is properly setup before "
                    "continuing.\nIgnore this message if the appropriate measures "
                    "have already been taken",
                    ", ".join(build_snaps),
                )
            )
        else:
            packages.snaps.install_snaps(build_snaps)
