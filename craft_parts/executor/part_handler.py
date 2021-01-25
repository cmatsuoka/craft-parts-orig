# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2017-2021 Canonical Ltd
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

"""Definitions and helpers for part handlers."""

import logging
import os
import os.path
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from craft_parts import callbacks, plugins, sources
from craft_parts.actions import Action, ActionType
from craft_parts.parts import Part
from craft_parts.plugins.options import PluginOptions
from craft_parts.schemas import Validator
from craft_parts.sources import SourceHandler
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step
from craft_parts.utils import os_utils

from .runner import Runner

logger = logging.getLogger(__name__)


class PartHandler:
    """Handle steps for a part using the appropriate plugins."""

    def __init__(self, part: Part, *, plugin_version: str, validator: Validator):
        self._part = part

        plugin_class = plugins.get_plugin(part.data["plugin"], version=plugin_version)
        plugin_schema = validator.merge_schema(plugin_class.get_schema())

        options = PluginOptions(properties=part.data, schema=plugin_schema)
        self._plugin = plugin_class(part_name=part.name, options=options)

        part_properties = validator.expand_part_properties(part.properties)
        self._source_handler = _get_source_handler(
            part.source, part.part_src_dir, part_properties
        )

    def run_action(self, action: Action, step_info: StepInfo) -> None:
        """Run the given action for this part using a plugin."""

        if action.type == ActionType.UPDATE:
            if action.step == Step.PULL:
                self._update_pull()
            elif action.step == Step.BUILD:
                self._update_build()
            return

        if action.type == ActionType.RERUN:
            # TODO: clean part
            pass

        os_utils.reset_env()

        callbacks.run_pre(self._part, action.step, step_info=step_info)

        if action.step == Step.PULL:
            self._run_pull(step_info)
        elif action.step == Step.BUILD:
            self._run_build(step_info)
        elif action.step == Step.STAGE:
            self._run_stage(step_info)
        elif action.step == Step.PRIME:
            self._run_prime(step_info)

        callbacks.run_post(self._part, action.step, step_info=step_info)

    def _run_pull(self, step_info: StepInfo):
        _remove(self._part.part_src_dir)
        self._make_dirs()

        # TODO: fetch and unpack stage packages/snaps

        # TODO: handle part replacements

        self._run_step(
            Step.PULL,
            scriptlet_name="override-pull",
            step_info=step_info,
            workdir=self._part.part_src_dir,
        )

        _save_state_file(self._part, "pull")

    def _run_build(self, step_info: StepInfo, *, update=False):
        self._make_dirs()
        _remove(self._part.part_build_dir)

        # TODO: unpack stage packages/snaps
        # Stage packages are fetched and unpacked in the pull step, but we'll
        # unpack again here just in case the build step has been cleaned.

        # TODO: handle part replacements

        shutil.copytree(
            self._part.part_src_dir, self._part.part_build_dir, symlinks=True
        )

        self._run_step(
            Step.BUILD,
            step_info=step_info,
            scriptlet_name="override-build",
            workdir=self._part.part_build_dir,
        )

        # Organize the installed files as requested. We do this in the build step for
        # two reasons:
        #
        #   1. So cleaning and re-running the stage step works even if `organize` is
        #      used
        #   2. So collision detection takes organization into account, i.e. we can use
        #      organization to get around file collisions between parts when staging.
        #
        # If `update` is true, we give the snapcraft CLI permission to overwrite files
        # that already exist. Typically we do NOT want this, so that parts don't
        # accidentally clobber e.g. files brought in from stage-packages, but in the
        # case of updating build, we want the part to have the ability to organize over
        # the files it organized last time around. We can be confident that this won't
        # overwrite anything else, because to do so would require changing the
        # `organize` keyword, which will make the build step dirty and require a clean
        # instead of an update.

        # TODO: implement organize
        # self._organize(overwrite=update)

        _save_state_file(self._part, "build")

    def _run_stage(self, step_info: StepInfo):
        # TODO: handle part replacements
        self._make_dirs()

        self._run_step(
            Step.STAGE,
            step_info=step_info,
            scriptlet_name="override-stage",
            workdir=self._part.stage_dir,
        )

        _save_state_file(self._part, "stage")

    def _run_prime(self, step_info: StepInfo):
        # TODO: handle part replacements
        self._make_dirs()

        self._run_step(
            Step.PRIME,
            step_info=step_info,
            scriptlet_name="override-prime",
            workdir=self._part.prime_dir,
        )

        _save_state_file(self._part, "prime")

    def _run_step(
        self, step: Step, *, step_info: StepInfo, scriptlet_name: str, workdir: Path
    ):
        runner = Runner(
            self._part,
            step,
            step_info=step_info,
            plugin=self._plugin,
            source_handler=self._source_handler,
        )
        scriptlet = self._part.data.get(scriptlet_name)
        if scriptlet:
            runner.run_scriptlet(
                scriptlet, scriptlet_name=scriptlet_name, workdir=workdir
            )
        else:
            runner.run_builtin()

    def _update_pull(self):
        # TODO: implement update pull
        pass

    def _update_build(self):
        # TODO: implement update build
        pass

    def _make_dirs(self):
        dirs = [
            self._part.part_src_dir,
            self._part.part_build_dir,
            self._part.part_install_dir,
            self._part.part_state_dir,
            self._part.part_run_dir,
            self._part.stage_dir,
            self._part.prime_dir,
        ]
        for dir_name in dirs:
            os.makedirs(dir_name, exist_ok=True)


def _get_source_handler(
    source: Optional[str], source_dir: Path, properties: Optional[Dict[str, Any]]
) -> Optional[SourceHandler]:
    """Returns a source_handler for the source in properties."""

    if not properties:
        properties = dict()

    # TODO: we cannot pop source as it is used by plugins. We also make
    # the default '.'
    source_handler = None
    if source:
        handler_class = sources.get_source_handler(
            source, source_type=properties["source-type"]
        )
        source_handler = handler_class(
            source,
            source_dir,
            source_checksum=properties["source-checksum"],
            source_branch=properties["source-branch"],
            source_tag=properties["source-tag"],
            source_depth=properties["source-depth"],
            source_commit=properties["source-commit"],
        )

    return source_handler


def _save_state_file(part: Part, name: str) -> None:
    os.makedirs(part.part_state_dir, exist_ok=True)
    state_file = os.path.join(part.part_state_dir, name)
    Path(state_file).touch()


def _remove(filename: Path) -> None:
    if filename.is_symlink() or filename.is_file():
        logger.debug("remove file %s", filename)
        os.unlink(filename)
    elif filename.is_dir():
        logger.debug("remove directory %s", filename)
        shutil.rmtree(filename)
