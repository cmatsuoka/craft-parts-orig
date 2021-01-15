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

import logging
import os
import os.path
import time
from pathlib import Path

from craft_parts.actions import Action, ActionType
from craft_parts.parts import Part
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step

logger = logging.getLogger(__name__)


def run_action(action: Action, *, part: Part, step_info: StepInfo):
    """Execute the given action for a part using the provided step information."""

    logger.debug("execute action %s:%s", part.name, action)

    if action.type == ActionType.SKIP:
        return

    # TODO: load plugin for part, instantiate part handler, etc.

    if action.step == Step.PULL:
        _run_pull(part, step_info)

    if action.step == Step.BUILD:
        _run_build(part, step_info)

    if action.step == Step.STAGE:
        _run_stage(part, step_info)

    if action.step == Step.PRIME:
        _run_prime(part, step_info)


def _run_pull(part: Part, step_info: StepInfo):
    time.sleep(0.1)
    _save_state_file(part, "pull")


def _run_build(part: Part, step_info: StepInfo):
    time.sleep(0.1)
    _save_state_file(part, "build")


def _run_stage(part: Part, step_info: StepInfo):
    time.sleep(0.1)
    _save_state_file(part, "stage")


def _run_prime(part: Part, step_info: StepInfo):
    time.sleep(0.1)
    _save_state_file(part, "prime")


def _save_state_file(part: Part, name: str) -> None:
    os.makedirs(part.part_state_dir, exist_ok=True)
    state_file = os.path.join(part.part_state_dir, name)
    Path(state_file).touch()
