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

"""Definitions and helpers for lifecycle actions."""

import enum
from typing import Optional

from craft_parts.steps import Step


@enum.unique
class ActionType(enum.IntEnum):
    """The type of the action to be executed.

    Action execution can be modified according to its type. An
    action of type ``RUN`` executes the expected commands for step
    processing, whereas an action of type ``RERUN`` clears the
    existing data and state before procceeding. An action of
    type ``UPDATE`` tries to continue processing the step. An
    action of type ``SKIP`` is not executed at all.
    """

    RUN = 0
    RERUN = 1
    SKIP = 2
    UPDATE = 3

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


class Action:
    """The action to be executed for a given part.

    Actions correspond to the operations required to run the lifecycle
    for each of the parts in the project specification.

    :param part_name: The name of the part this action will be
        executed for.
    :param step: The :class:`Step` this action corresponds to.
    :param action_type: Whether this action should run, re-run, update,
        or skip this step.
    :param reason: A textual description of why this action should be
        executed.
    """

    def __init__(
        self,
        part_name: str,
        step: Step,
        *,
        action_type: ActionType = ActionType.RUN,
        reason: Optional[str] = None,
    ):
        self._part_name = part_name
        self._step = step
        self._type = action_type
        self._reason = reason

    @property
    def part_name(self) -> str:
        """The name of part this action will be executed for."""
        return self._part_name

    @property
    def step(self) -> Step:
        """The step to be executed in this action."""
        return self._step

    @property
    def type(self) -> ActionType:
        """The type of this action."""
        return self._type

    @property
    def reason(self) -> Optional[str]:
        """The reason why this action is being executed."""
        return self._reason

    def __repr__(self):
        return f"{self.part_name}:{self.step!r}({self.type!r})"
