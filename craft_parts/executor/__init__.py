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

import logging
import shutil
from typing import Dict, List, Optional

from craft_parts.actions import Action, ActionType
from craft_parts.parts import Part
from craft_parts.schemas import Validator
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step

from .collisions import check_for_stage_collisions
from .part_handler import PartHandler

logger = logging.getLogger(__name__)


class Executor:
    """Execute lifecycle actions."""

    def __init__(
        self, *, part_list: List[Part], plugin_version: str, validator: Validator
    ):
        self._part_list = part_list
        self._plugin_version = plugin_version
        self._validator = validator
        self._handler: Dict[str, PartHandler] = {}

    def run_action(self, action: Action, *, part: Part, step_info: StepInfo):
        """Execute the given action for a part using the provided step information."""

        logger.debug("execute action %s:%s", part.name, action)

        if action.type == ActionType.SKIP:
            logger.debug("Skip execution of %s (because %s)", action, action.reason)
            return

        if action.step == Step.STAGE:
            check_for_stage_collisions(self._part_list)

        self._create_part_handler(part, step_info=step_info)

        handler = self._handler[part.name]
        handler.run_action(action)

    def clean(
        self,
        *,
        initial_step: Optional[Step],
        part_list: List[Part],
        step_info: StepInfo
    ):
        """Clean the given parts, or all parts if none is specified."""

        if initial_step:
            selected_steps = [initial_step] + initial_step.next_steps()
        else:
            selected_steps = list(Step)

        selected_steps.reverse()

        for part in part_list:
            self._create_part_handler(part, step_info=step_info)
            handler = self._handler[part.name]

            for step in selected_steps:
                handler.clean_step(step=step)

            shutil.rmtree(part.prime_dir)
            shutil.rmtree(part.stage_dir)

    def _create_part_handler(self, part: Part, *, step_info: StepInfo):
        if part.name not in self._handler:
            # create the part handler for a new part
            self._handler[part.name] = PartHandler(
                part,
                plugin_version=self._plugin_version,
                step_info=step_info.for_part(part),
                validator=self._validator,
                part_list=self._part_list,
            )
