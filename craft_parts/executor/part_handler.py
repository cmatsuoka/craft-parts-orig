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
import time
from pathlib import Path

from craft_parts import plugins
from craft_parts.actions import Action
from craft_parts.parts import Part
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step

from . import scriptlets

logger = logging.getLogger(__name__)


class PartHandler:
    """Handle steps for a part using the appropriate plugins."""

    def __init__(self, part: Part, plugin_version: str):
        self._part = part
        self._plugin = plugins.get_plugin(part.data["plugin"], version=plugin_version)

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
        self._makedirs()

        scriptlet = self._part.data.get("override-pull")
        if scriptlet:
            scriptlets.run("override-pull", scriptlet, self._part.part_src_dir)
        # TODO: implement source handlers
        # elif self.source_handler:
        #    self.source_handler.pull()

        _save_state_file(self._part, "pull")

    def _run_build(self, step_info: StepInfo):
        time.sleep(0.1)
        _save_state_file(self._part, "build")

    def _run_stage(self, step_info: StepInfo):
        time.sleep(0.1)
        _save_state_file(self._part, "stage")

    def _run_prime(self, step_info: StepInfo):
        time.sleep(0.1)
        _save_state_file(self._part, "prime")

    def _makedirs(self):
        dirs = [
            self._part.part_src_dir,
            self._part.part_build_dir,
            self._part.part_install_dir,
            self._part.part_state_dir,
            self._part.stage_dir,
            self._part.prime_dir,
        ]
        for dir_name in dirs:
            os.makedirs(dir_name, exist_ok=True)


def _save_state_file(part: Part, name: str) -> None:
    os.makedirs(part.part_state_dir, exist_ok=True)
    state_file = os.path.join(part.part_state_dir, name)
    Path(state_file).touch()


def _remove(filename: str) -> None:
    if os.path.islink(filename) or os.path.isfile(filename):
        logging.debug("remove file %s", filename)
        os.remove(filename)
    elif os.path.isdir(filename):
        logging.debug("remove directory %s", filename)
        shutil.rmtree(filename)
