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

import io
import logging
import os
import os.path
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from craft_parts import errors, plugins, schemas
from craft_parts.actions import Action
from craft_parts.parts import Part
from craft_parts.schemas import Validator
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step

from . import environment, scriptlets

logger = logging.getLogger(__name__)


class _Options:
    pass


class PartHandler:
    """Handle steps for a part using the appropriate plugins."""

    def __init__(self, part: Part, *, plugin_version: str, validator: Validator):
        self._part = part
        self._validator = validator

        plugin_class = plugins.get_plugin(part.data["plugin"], version=plugin_version)

        plugin_schema = _merged_part_and_plugin_schemas(
            validator.part_schema,
            validator.definitions_schema,
            plugin_class.get_schema(),
        )

        schemas.validate_schema(data=part.data, schema=plugin_schema)

        options = _make_options(properties=part.data, schema=plugin_schema)
        self._plugin = plugin_class(part_name=part.name, options=options)

    def run_action(self, action: Action, step_info: StepInfo) -> None:
        """Run the given action for this part using a plugin."""

        # TODO: handle action_type

        if action.step == Step.PULL:
            self._run_pull(step_info)
        elif action.step == Step.BUILD:
            self._run_build(step_info)
        elif action.step == Step.STAGE:
            self._run_stage(step_info)
        elif action.step == Step.PRIME:
            self._run_prime(step_info)

    def _run_pull(self, step_info: StepInfo):
        _remove(self._part.part_src_dir)
        self._make_dirs()

        # TODO: fetch and install stage packages/snaps

        scriptlet = self._part.data.get("override-pull")
        if scriptlet:
            part_env = self._generate_part_env(step=Step.PULL, step_info=step_info)
            scriptlets.run(
                scriptlet_name="override-pull",
                scriptlet=scriptlet,
                workdir=self._part.part_src_dir,
                env=part_env,
            )
        # TODO: implement source handlers
        # elif self.source_handler:
        #    self.source_handler.pull()

        _save_state_file(self._part, "pull")

    def _run_build(self, step_info: StepInfo, *, update=False):
        self._make_dirs()
        _remove(self._part.part_build_dir)
        shutil.copytree(
            self._part.part_src_dir, self._part.part_build_dir, symlinks=True
        )

        scriptlet = self._part.data.get("override-build")
        if scriptlet:
            part_env = self._generate_part_env(step=Step.BUILD, step_info=step_info)
            scriptlets.run(
                scriptlet_name="override-build",
                scriptlet=scriptlet,
                workdir=self._part.part_build_dir,
                env=part_env,
            )
        else:
            self._do_v2_build(step_info=step_info)

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
        time.sleep(0.1)
        _save_state_file(self._part, "stage")

    def _run_prime(self, step_info: StepInfo):
        time.sleep(0.1)
        _save_state_file(self._part, "prime")

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

    def _generate_part_env(self, *, step: Step, step_info: StepInfo) -> str:
        """Generates an environment suitable to run during a step.

        :returns: str with the build step environment.
        """
        if not isinstance(self._plugin, plugins.PluginV2):
            raise errors.InternalError("Plugin version not supported.")

        # Craft parts' say.
        our_build_environment = environment.get_part_environment(
            part=self._part, step=step, step_info=step_info
        )

        # Plugin's say.
        if step == Step.BUILD:
            plugin_environment = self._plugin.get_build_environment()
        else:
            plugin_environment = dict()

        # Part's (user) say.
        user_build_environment = self._part.data.get("build-environment", {})

        # TODO: fix environment setting

        # Create the script.
        with io.StringIO() as run_environment:
            print("#!/bin/sh", file=run_environment)
            print("set -e", file=run_environment)

            print("# Environment", file=run_environment)

            print("## Part Environment", file=run_environment)
            for key, val in our_build_environment.items():
                print(f'export {key}="{val}"', file=run_environment)

            print("## Plugin Environment", file=run_environment)
            for key, val in plugin_environment.items():
                print(f'export {key}="{val}"', file=run_environment)

            print("## User Environment", file=run_environment)
            for env in user_build_environment:
                for key, val in env.items():
                    print(f'export {key}="{val}"', file=run_environment)

            # Return something suitable for Runner.
            return run_environment.getvalue()

    def _do_v2_build(self, *, step_info: StepInfo):
        if not isinstance(self._plugin, plugins.PluginV2):
            raise errors.InternalError("Plugin version not supported.")

        # Save script to execute.
        build_script_path = self._part.part_run_dir / "build.sh"

        # Plugin commands.
        plugin_build_commands = self._plugin.get_build_commands()

        with build_script_path.open("w") as run_file:
            part_env = self._generate_part_env(step=Step.BUILD, step_info=step_info)
            print(part_env, file=run_file)
            print("set -x", file=run_file)

            for build_command in plugin_build_commands:
                print(build_command, file=run_file)

            run_file.flush()

        source_subdir = self._part.data.get("source-subdir", "")
        build_work_dir = os.path.join(self._part.part_build_dir, source_subdir)

        try:
            subprocess.run([build_script_path], check=True, cwd=build_work_dir)
        except subprocess.CalledProcessError as process_error:
            raise errors.PluginBuildError(part_name=self._part.name) from process_error


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


def _merged_part_and_plugin_schemas(
    part_schema, definitions_schema, plugin_schema
) -> Dict[str, Any]:
    plugin_schema = plugin_schema.copy()
    if "properties" not in plugin_schema:
        plugin_schema["properties"] = {}

    if "definitions" not in plugin_schema:
        plugin_schema["definitions"] = {}

    # The part schema takes precedence over the plugin's schema.
    plugin_schema["properties"].update(part_schema)
    plugin_schema["definitions"].update(definitions_schema)

    return plugin_schema


def _make_options(*, properties, schema) -> _Options:
    options = _Options()

    schema_properties = schema.get("properties", {})
    for key in schema_properties:
        attr_name = key.replace("-", "_")
        default_value = schema_properties[key].get("default")
        attr_value = properties.get(key, default_value)
        setattr(options, attr_name, attr_value)

    return options
