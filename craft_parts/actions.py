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
    """The type of the action to be executed."""

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
    """

    def __init__(
        self,
        part_name: str,
        step: Step,
        *,
        action_type: ActionType = ActionType.RUN,
        reason: Optional[str] = None,
    ):
        self.part_name = part_name
        self.step = step
        self.type = action_type
        self.reason = reason

    def __repr__(self):
        return f"{self.part_name}:{self.step!r}({self.type!r})"
