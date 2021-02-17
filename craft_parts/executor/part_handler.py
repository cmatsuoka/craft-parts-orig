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
from typing import Callable, Dict, List

from craft_parts import callbacks, common, errors, packages, plugins, sources
from craft_parts.actions import Action, ActionType
from craft_parts.filesets import Fileset
from craft_parts.infos import PartInfo, StepInfo
from craft_parts.packages import errors as packages_errors
from craft_parts.parts import Part
from craft_parts.plugins.options import PluginOptions
from craft_parts.schemas import Validator
from craft_parts.state_manager import PartState, states
from craft_parts.steps import Step
from craft_parts.utils import os_utils

from .organize import organize_filesets
from .step_handler import FilesAndDirs, StepHandler

logger = logging.getLogger(__name__)


class PartHandler:
    """Handle steps for a part using the appropriate plugins."""

    def __init__(
        self,
        part: Part,
        *,
        plugin_version: str,
        part_info: PartInfo,
        validator: Validator,
        part_list: List[Part],
    ):
        self._part = part
        self._part_info = part_info
        self._part_list = part_list

        plugin_class = plugins.get_plugin(part.plugin, version=plugin_version)
        plugin_schema = validator.merge_schema(plugin_class.get_schema())

        options = PluginOptions(properties=part.properties, schema=plugin_schema)
        self._plugin = plugin_class(options=options, part_info=part_info)

        self._part_properties = validator.expand_part_properties(part.properties)
        self._source_handler = sources.get_source_handler(
            application_name=part_info.application_name,
            source=part.source,
            source_dir=part.part_src_dir,
            properties=self._part_properties,
        )
        self._package_repo = packages.Repository()

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

        step_info = StepInfo(part_info=self._part_info, step=action.step)

        callbacks.run_pre(step_info=step_info)

        run_handlers: Dict[Step, Callable[[StepInfo], PartState]] = {
            Step.PULL: self._run_pull,
            Step.BUILD: self._run_build,
            Step.STAGE: self._run_stage,
            Step.PRIME: self._run_prime,
        }
        if action.step in run_handlers:
            state = run_handlers[action.step](step_info)
            state.write(self._part.part_state_dir / action.step.name.lower())

        callbacks.run_post(step_info=step_info)

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
                    target_arch=step_info.deb_arch,
                    base=os_utils.get_build_base(),
                    stage_packages_path=self._part.part_package_dir,
                )
            except packages_errors.PackageNotFound as err:
                raise errors.StagePackageError(self._part.name, err.message)

        # We don't need to expand environment variables in plugin options here because
        # the build script execution will expand them (assuming we're using plugins V2).

        self._run_step(
            step_info=step_info,
            scriptlet_name="override-pull",
            workdir=self._part.part_src_dir,
        )

        # TODO: check what else should be part of the pull state
        state = states.PullState(
            part_properties=self._part_properties,
            project_options=step_info.project_options,
            stage_packages=fetched_packages,
            source_details=getattr(self._source_handler, "source_details", None),
        )
        return state

    def _run_build(self, step_info: StepInfo, *, update=False) -> PartState:
        self._make_dirs()
        _remove(self._part.part_build_dir)

        build_packages = common.get_build_packages(self._part, self._package_repo)
        packages.Repository.install_build_packages(build_packages)

        # TODO: install build snaps

        # Unpack stage packages/snaps to part install dir
        # (stage packages are fetched and unpacked in the pull step, but we'll
        # unpack again here just in case the build step has been cleaned.)
        self._package_repo.unpack_stage_packages(
            stage_packages_path=self._part.part_package_dir,
            install_path=Path(self._part.part_install_dir),
        )

        # Copy source from the part source dir to the part build dir
        shutil.copytree(
            self._part.part_src_dir, self._part.part_build_dir, symlinks=True
        )

        # Perform the build step
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
        self._organize(overwrite=update)

        # TODO: check what else should be part of the build state
        state = states.BuildState(
            part_properties=self._part_properties,
            project_options=step_info.project_options,
            build_packages=build_packages,
            machine_assets=common.get_machine_manifest(),
        )
        return state

    def _run_stage(self, step_info: StepInfo) -> PartState:
        self._make_dirs()

        files, dirs = self._run_step(
            step_info=step_info,
            scriptlet_name="override-stage",
            workdir=self._part.stage_dir,
        )

        state = states.StageState(
            part_properties=self._part_properties,
            project_options=step_info.project_options,
            files=files,
            directories=dirs,
        )
        return state

    def _run_prime(self, step_info: StepInfo) -> PartState:
        self._make_dirs()

        files, dirs = self._run_step(
            step_info=step_info,
            scriptlet_name="override-prime",
            workdir=self._part.prime_dir,
        )

        state = states.PrimeState(
            part_properties=self._part_properties,
            project_options=step_info.project_options,
            files=files,
            directories=dirs,
        )
        return state

    def _run_step(
        self, *, step_info: StepInfo, scriptlet_name: str, workdir: Path
    ) -> FilesAndDirs:
        """Run the scriptlet if overriding, otherwise run the built-in handler."""

        if not step_info.step:
            raise errors.InternalError("request to run an undefined step")

        step_handler = StepHandler(
            self._part,
            step_info=step_info,
            plugin=self._plugin,
            source_handler=self._source_handler,
        )
        scriptlet = self._part.get_scriptlet(step_info.step)
        if scriptlet:
            step_handler.run_scriptlet(
                scriptlet, scriptlet_name=scriptlet_name, workdir=workdir
            )
            return FilesAndDirs(set(), set())

        return step_handler.run_builtin()

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

    def _organize(self, *, overwrite=False):
        fileset = Fileset(self._part.organize_fileset, name="organize")
        organize_filesets(
            part_name=self._part.name,
            fileset=fileset,
            base_dir=self._part.part_install_dir,
            overwrite=overwrite,
        )


def _remove(filename: Path) -> None:
    if filename.is_symlink() or filename.is_file():
        logger.debug("remove file %s", filename)
        os.unlink(filename)
    elif filename.is_dir():
        logger.debug("remove directory %s", filename)
        shutil.rmtree(filename)


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
                "Attempted to remove file '%s', but it didn't exist. " "Skipping...",
                each_file,
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
                "Attempted to remove directory '%s', but it didn't exist. "
                "Skipping...",
                each_dir,
            )
