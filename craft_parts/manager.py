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

"""The parts lifecycle manager definition and helpers."""

import os.path
from typing import Any, Dict, List

from craft_parts import executor, parts, sequencer
from craft_parts.actions import Action
from craft_parts.parts import Part
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step
from craft_parts.validator import Validator

_SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schema", "parts.json")


class LifecycleManager:
    """Coordinate the planning and execution of the parts lifecycle.

    The lifecycle manager determines the list of actions that needs be executed in
    order to obtain a tree of installed files from the specification on how to
    process its parts, and provides a mechanism to execute each of these actions.
    """

    def __init__(
        self,
        all_parts: Dict[str, Any],
        *,
        build_packages: List[str] = None,
        work_dir: str = ".",
        target_arch: str = "",
        platform_id: str = "",
        platform_version_id: str = "",
        parallel_build_count: int = 1,
        local_plugins_dir: str = "",
        plugin_version: str = "v2",
        **custom_args,  # custom passthrough args
    ):
        self._validator = Validator(_SCHEMA_DIR)
        self._validator.validate(all_parts)

        parts_data = all_parts.get("parts", {})
        self._parts = [
            Part(name, p, work_dir=work_dir) for name, p in parts_data.items()
        ]
        self._build_packages = build_packages
        self._sequencer = sequencer.Sequencer(self._parts)
        self._executor = executor.Executor(
            part_list=self._parts, plugin_version=plugin_version
        )

        self._step_info = StepInfo(
            work_dir=work_dir,
            target_arch=target_arch,
            platform_id=platform_id,
            platform_version_id=platform_version_id,
            parallel_build_count=parallel_build_count,
            local_plugins_dir=local_plugins_dir,
            custom_args=custom_args,
        )

    def clean(self, part_list: List[str] = None) -> None:
        """Clean the specified parts, or all parts if none is specified."""
        pass

    def actions(self, target_step: Step, part_names: List[str] = None) -> List[Action]:
        """Obtain the list of actions to be executed given the target step and parts."""
        act = self._sequencer.actions(target_step, part_names)
        return act

    def execute(self, actions: List[Action]):
        """Execute the specified actions."""

        for act in actions:
            part = parts.part_by_name(act.part_name, self._parts)
            self._executor.run_action(act, part=part, step_info=self._step_info)
