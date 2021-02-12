# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016-2021 Canonical Ltd
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

"""Helpers and definitions for lifecycle states."""

import contextlib
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, cast

from craft_parts import errors
from craft_parts.parts import Part
from craft_parts.steps import Step
from craft_parts.utils import file_utils, yaml_utils

from .build_state import BuildState
from .part_state import PartState
from .prime_state import PrimeState
from .pull_state import PullState
from .stage_state import StageState


def load_state(
    part: Part, step: Step
) -> Tuple[Optional[PartState], Optional[datetime]]:
    """Retrieve the persistent state for the given part and step."""

    state_data = {}
    filename = os.path.join(part.part_state_dir, step.name.lower())
    if not os.path.isfile(filename):
        return None, None

    with open(filename, "r") as state_file:
        data = yaml_utils.load(state_file)
        if data:
            state_data = data

    timestamp = file_utils.timestamp(filename)

    state: PartState

    if step == Step.PULL:
        state = cast(PullState, state_data)
    elif step == Step.BUILD:
        state = cast(BuildState, state_data)
    elif step == Step.STAGE:
        state = cast(StageState, state_data)
    elif step == Step.PRIME:
        state = cast(PrimeState, state_data)
    else:
        raise errors.InternalError(f"invalid step {step!r}")

    return state, timestamp


def load_part_states(step: Step, part_list: List[Part]) -> Dict[str, PartState]:
    """Return a dictionary of the state of the given step for all parts."""

    states: Dict[str, PartState] = {}
    for part in part_list:
        state, _ = load_state(part, step)
        if state:
            states[part.name] = state
    return states


def is_clean(part: Part, step: Step) -> bool:
    """Verify whether the persistent state for the given part and step is clean."""

    filename = os.path.join(part.part_state_dir, step.name.lower())
    return not os.path.isfile(filename)


def remove(part: Part, step: Step):
    """Remove the persistent state file for the given part and step."""
    with contextlib.suppress(FileNotFoundError):
        os.remove(part.part_state_dir / step.name.lower())
