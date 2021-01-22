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
from typing import Any, Dict

from craft_parts import plugins, schemas
from craft_parts.actions import Action
from craft_parts.parts import Part
from craft_parts.schemas import Validator
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step
from craft_parts.utils import os_utils

from . import builtin, environment, scriptlets

logger = logging.getLogger(__name__)


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

        os_utils.reset_env()

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

        # TODO: fetch and unpack stage packages/snaps

        # TODO: handle part replacements

        scriptlet = self._part.data.get("override-pull")
        if scriptlet:
            part_env = self._generate_environment(step=Step.PULL, step_info=step_info)
            scriptlets.run(
                scriptlet_name="override-pull",
                scriptlet=scriptlet,
                workdir=self._part.part_src_dir,
                env=part_env,
            )
        else:
            builtin.pull(part=self._part)
        # TODO: implement source handlers
        # elif self.source_handler:
        #    self.source_handler.pull()

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

        part_env = self._generate_environment(step=Step.BUILD, step_info=step_info)
        scriptlet = self._part.data.get("override-build")
        if scriptlet:
            scriptlets.run(
                scriptlet_name="override-build",
                scriptlet=scriptlet,
                workdir=self._part.part_build_dir,
                env=part_env,
            )
        else:
            builtin.build(part=self._part, plugin=self._plugin, env=part_env)

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

        scriptlet = self._part.data.get("override-stage")
        if scriptlet:
            part_env = self._generate_environment(step=Step.STAGE, step_info=step_info)
            scriptlets.run(
                scriptlet_name="override-stage",
                scriptlet=scriptlet,
                workdir=self._part.stage_dir,
                env=part_env,
            )
        else:
            builtin.stage(part=self._part)

        _save_state_file(self._part, "stage")

    def _run_prime(self, step_info: StepInfo):
        # TODO: handle part replacements
        self._make_dirs()

        scriptlet = self._part.data.get("override-prime")
        if scriptlet:
            part_env = self._generate_environment(step=Step.STAGE, step_info=step_info)
            scriptlets.run(
                scriptlet_name="override-prime",
                scriptlet=scriptlet,
                workdir=self._part.prime_dir,
                env=part_env,
            )
        else:
            builtin.prime(part=self._part)

        _save_state_file(self._part, "prime")

    def _generate_environment(self, *, step: Step, step_info: StepInfo) -> str:
        return environment.generate_part_environment(
            part=self._part, step=step, plugin=self._plugin, step_info=step_info
        )

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


# pylint: disable=too-few-public-methods
class _Options:
    pass


def _make_options(*, properties, schema) -> _Options:
    options = _Options()

    schema_properties = schema.get("properties", {})
    for key in schema_properties:
        attr_name = key.replace("-", "_")
        default_value = schema_properties[key].get("default")
        attr_value = properties.get(key, default_value)
        setattr(options, attr_name, attr_value)

    return options
