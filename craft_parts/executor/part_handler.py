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
from typing import Any, Callable, Dict, List, Optional

from craft_parts import callbacks, errors, plugins, repo, sources
from craft_parts.actions import Action, ActionType
from craft_parts.parts import Part
from craft_parts.plugins.options import PluginOptions
from craft_parts.schemas import Validator
from craft_parts.sources import SourceHandler
from craft_parts.state_manager import (
    BuildState,
    PartState,
    PrimeState,
    PullState,
    StageState,
    states,
)
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step
from craft_parts.utils import os_utils

from .runner import FilesAndDirs, Runner

logger = logging.getLogger(__name__)


class PartHandler:
    """Handle steps for a part using the appropriate plugins."""

    def __init__(
        self,
        part: Part,
        *,
        plugin_version: str,
        step_info: StepInfo,
        validator: Validator,
        part_list: List[Part],
    ):
        self._part = part
        self._step_info = step_info
        self._part_list = part_list

        plugin_class = plugins.get_plugin(part.plugin, version=plugin_version)
        plugin_schema = validator.merge_schema(plugin_class.get_schema())

        options = PluginOptions(properties=part.properties, schema=plugin_schema)
        self._plugin = plugin_class(
            part_name=part.name, options=options, step_info=step_info
        )

        self._part_properties = validator.expand_part_properties(part.properties)
        self._source_handler = _get_source_handler(
            step_info.application_name,
            part.source,
            part.part_src_dir,
            self._part_properties,
        )
        self._package_repo = repo.Repo()

    def clean_step(self, *, step: Step) -> None:
        """Remove the work files and the state of the given step."""

        logger.debug("clean %s:%s", self._part.name, step)

        # Don't try to shortcut it, always clean everything. A previous clean
        # attempt may have failed.
        # if states.is_clean(self._part, step):
        #    return

        clean_handlers: Dict[Step, Callable[[], None]] = {
            Step.PULL: self._clean_pull,
            Step.BUILD: self._clean_build,
            Step.STAGE: self._clean_stage,
            Step.PRIME: self._clean_prime,
        }
        if step in clean_handlers:
            states.remove(self._part, step)
            clean_handlers[step]()

    def _clean_pull(self) -> None:
        # remove dirs where stage packages and snaps are fetched
        _remove(self._part.part_package_dir)
        _remove(self._part.part_snaps_dir)

        # remove the source tree
        _remove(self._part.part_src_dir)

    def _clean_build(self) -> None:
        _remove(self._part.part_build_dir)
        _remove(self._part.part_install_dir)

    def _clean_stage(self) -> None:
        part_states = states.load_part_states(Step.STAGE, self._part_list)
        _clean_shared_area(
            part_name=self._part.name,
            shared_dir=self._part.stage_dir,
            part_states=part_states,
        )

    def _clean_prime(self) -> None:
        part_states = states.load_part_states(Step.PRIME, self._part_list)
        _clean_shared_area(
            part_name=self._part.name,
            shared_dir=self._part.stage_dir,
            part_states=part_states,
        )

    def run_action(self, action: Action) -> None:
        """Run the given action for this part using a plugin."""

        if action.type == ActionType.UPDATE:
            update_handlers: Dict[Step, Callable[[], None]] = {
                Step.PULL: self._update_pull,
                Step.BUILD: self._update_build,
            }
            if action.step in update_handlers:
                handler = update_handlers[action.step]
                handler()
            return

        if action.type == ActionType.RERUN:
            self.clean_step(step=action.step)

        os_utils.reset_env()

        step_info = self._step_info.for_step(action.step)

        callbacks.run_pre(self._part, action.step, step_info=step_info)

        run_handlers: Dict[Step, Callable[[StepInfo], PartState]] = {
            Step.PULL: self._run_pull,
            Step.BUILD: self._run_build,
            Step.STAGE: self._run_stage,
            Step.PRIME: self._run_prime,
        }
        if action.step in run_handlers:
            state = run_handlers[action.step](step_info)
            state.write(self._part.part_state_dir / action.step.name.lower())

        callbacks.run_post(self._part, action.step, step_info=step_info)

    def _run_pull(self, step_info: StepInfo) -> PartState:
        _remove(self._part.part_src_dir)
        self._make_dirs()

        # Fetch stage packages
        stage_packages = self._part.stage_packages
        fetched_packages = None

        if stage_packages:
            try:
                fetched_packages = self._package_repo.fetch_stage_packages(
                    application_name=step_info.application_name,
                    package_names=stage_packages,
                    target_arch=self._step_info.deb_arch,
                    base=os_utils.get_build_base(),
                    stage_packages_path=self._part.part_package_dir,
                )
            except errors.PackageNotFound as err:
                raise errors.StagePackageError(self._part.name, err.get_brief())

        # TODO: handle part replacements

        self._run_step(
            step_info=step_info,
            scriptlet_name="override-pull",
            workdir=self._part.part_src_dir,
        )

        # TODO: check what else should be part of the pull state
        state = PullState(
            property_names={},
            part_properties=self._part_properties,
            stage_packages=fetched_packages,
            source_details=getattr(self._source_handler, "source_details", None),
        )
        return state

    def _run_build(self, step_info: StepInfo, *, update=False) -> PartState:
        self._make_dirs()
        _remove(self._part.part_build_dir)

        build_packages = _get_build_packages(self._part, self._package_repo)
        repo.Repo.install_build_packages(build_packages)

        # unpack stage packages/snaps
        self._package_repo.unpack_stage_packages(
            stage_packages_path=self._part.part_package_dir,
            install_path=Path(self._part.part_install_dir),
        )

        # TODO: handle part replacements

        shutil.copytree(
            self._part.part_src_dir, self._part.part_build_dir, symlinks=True
        )

        self._run_step(
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

        # TODO: check what else should be part of the build state
        state = BuildState(
            property_names={},
            part_properties=self._part_properties,
            machine_assets=_get_machine_manifest(),
        )
        return state

    def _run_stage(self, step_info: StepInfo) -> PartState:
        # TODO: handle part replacements
        self._make_dirs()

        files, dirs = self._run_step(
            step_info=step_info,
            scriptlet_name="override-stage",
            workdir=self._part.stage_dir,
        )

        return StageState(files=files, directories=dirs)

    def _run_prime(self, step_info: StepInfo) -> PartState:
        # TODO: handle part replacements
        self._make_dirs()

        files, dirs = self._run_step(
            step_info=step_info,
            scriptlet_name="override-prime",
            workdir=self._part.prime_dir,
        )

        return PrimeState(files=files, directories=dirs)

    def _run_step(
        self, *, step_info: StepInfo, scriptlet_name: str, workdir: Path
    ) -> FilesAndDirs:
        """Run the scriptlet if overriding, otherwise run the built-in handler."""

        if not step_info.step:
            raise errors.InternalError("request to run an undefined step")

        runner = Runner(
            self._part,
            step_info=step_info,
            plugin=self._plugin,
            source_handler=self._source_handler,
        )
        scriptlet = self._part.get_scriptlet(step_info.step)
        if scriptlet:
            runner.run_scriptlet(
                scriptlet, scriptlet_name=scriptlet_name, workdir=workdir
            )
            return FilesAndDirs(set(), set())

        return runner.run_builtin()

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
    application_name: str,
    source: Optional[str],
    source_dir: Path,
    properties: Optional[Dict[str, Any]],
) -> Optional[SourceHandler]:
    """Returns a source_handler for the source in properties."""

    if not properties:
        properties = dict()

    # TODO: we cannot pop source as it is used by plugins. We also make
    # the default '.'
    source_handler = None
    if source:
        handler_class = sources.get_source_handler(
            source,
            source_type=properties["source-type"],
        )
        source_handler = handler_class(
            application_name=application_name,
            source=source,
            source_dir=source_dir,
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


def _get_build_packages(part: Part, repository) -> List[str]:
    packages: List[str] = []

    build_packages = part.build_packages
    if build_packages:
        logger.debug("part build packages: %s", build_packages)
        packages.extend(build_packages)

    source = part.source
    if source:
        source_type = sources.get_source_type_from_uri(source)
        source_build_packages = repository.get_packages_for_source_type(source_type)
        if source_build_packages:
            logger.debug("source build packages: %s", source_build_packages)
            packages.extend(source_build_packages)

    if isinstance(part.plugin, plugins.PluginV2):
        plugin_build_packages = part.plugin.get_build_packages()
        if plugin_build_packages:
            logger.debug("plugin build packages: %s", plugin_build_packages)
            packages.extend(plugin_build_packages)

    return packages


def _get_machine_manifest() -> Dict[str, Any]:
    return {
        "uname": os_utils.get_system_info(),
        "installed-packages": sorted(repo.Repo.get_installed_packages()),
        "installed-snaps": sorted(repo.snaps.get_installed_snaps()),
    }


def _clean_shared_area(
    *, part_name: str, shared_dir: Path, part_states: Dict[str, PartState]
) -> None:
    # no state defined for this part, we won't remove files
    if part_name not in part_states:
        return

    state = part_states[part_name]
    primed_files = state.files
    primed_directories = state.directories

    # We want to make sure we don't remove a file or directory that's
    # being used by another part. So we'll examine the state for all parts
    # in the project and leave any files or directories found to be in
    # common.
    for other_name, other_state in part_states.items():
        if other_state and (other_name != part_name):
            primed_files -= other_state.files
            primed_directories -= other_state.directories

    # Finally, clean the files and directories that are specific to this
    # part.
    _clean_migrated_files(primed_files, primed_directories, shared_dir)


def _clean_migrated_files(files, dirs, directory):
    for each_file in files:
        try:
            os.remove(os.path.join(directory, each_file))
        except FileNotFoundError:
            logger.warning(
                "Attempted to remove file {name!r}, but it didn't exist. "
                "Skipping...".format(name=each_file)
            )

    # Directories may not be ordered so that subdirectories come before
    # parents, and we want to be able to remove directories if possible, so
    # we'll sort them in reverse here to get subdirectories before parents.
    dirs = sorted(dirs, reverse=True)

    for each_dir in dirs:
        migrated_directory = os.path.join(directory, each_dir)
        try:
            if not os.listdir(migrated_directory):
                os.rmdir(migrated_directory)
        except FileNotFoundError:
            logger.warning(
                "Attempted to remove directory {name!r}, but it didn't exist. "
                "Skipping...".format(name=each_dir)
            )
