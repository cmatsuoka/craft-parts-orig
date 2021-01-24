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

"""Register and execute callback functions."""

import copy
import logging
from collections import namedtuple
from typing import Callable, List

from craft_parts import errors
from craft_parts.parts import Part
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step

CallbackHook = namedtuple("CallbackHook", ["function", "step_list"])

_PRE_HOOKS: List[CallbackHook] = []
_POST_HOOKS: List[CallbackHook] = []

logger = logging.getLogger(__name__)


def register_pre(
    func: Callable[[StepInfo], bool], *, step_list: List[Step] = None
) -> None:
    """Register a pre-step callback function.

    :param func: The callback function to run.
    :param step_list: The steps before which the callback function should run.
        If not specified, the callback function will be executed before all steps.
    """

    _ensure_not_defined(func, _PRE_HOOKS)
    _PRE_HOOKS.append(CallbackHook(func, step_list))


def register_post(
    func: Callable[[StepInfo], bool], *, step_list: List[Step] = None
) -> None:
    """Register a post-step callback function.

    :param func: The callback function to run.
    :param step_list: The steps after which the callback function should run.
        If not specified, the callback function will be executed after all steps.
    """

    _ensure_not_defined(func, _POST_HOOKS)
    _POST_HOOKS.append(CallbackHook(func, step_list))


def clear() -> None:
    """Clear all existing registered callback functions."""

    # pylint: disable=global-statement
    global _PRE_HOOKS, _POST_HOOKS
    _PRE_HOOKS = []
    _POST_HOOKS = []


def run_pre(part: Part, step: Step, *, step_info: StepInfo) -> None:
    """Run all registered pre-step callback functions.
    :param step: the step being processed.
    :param step_info: the step information to be sent to the callback functions."
    """

    return _run(part, step, hook_list=_PRE_HOOKS, step_info=step_info)


def run_post(part: Part, step: Step, *, step_info: StepInfo) -> None:
    """Run all registered post-step callback functions.
    :param step: the step being processed.
    :param step_info: the step information to be sent to the callback functions."
    """

    return _run(part, step, hook_list=_POST_HOOKS, step_info=step_info)


def _run(part: Part, step: Step, *, hook_list: List[CallbackHook], step_info: StepInfo):
    info = copy.deepcopy(step_info)
    info.step = step

    # Populate part directories
    info.part_src_dir = part.part_src_dir
    info.part_build_dir = part.part_build_dir
    info.part_install_dir = part.part_install_dir
    info.stage_dir = part.stage_dir
    info.prime_dir = part.prime_dir

    for hook in hook_list:
        if not hook.step_list or step in hook.step_list:
            hook.function(step_info)


def _ensure_not_defined(
    func: Callable[[StepInfo], bool], hook_list: List[CallbackHook]
):
    for hook in hook_list:
        if func == hook.function:
            raise errors.CallbackRegistration(
                "the callback function is already registered."
            )
