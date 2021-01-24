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

from collections import namedtuple

import pytest

from craft_parts import steps
from craft_parts.steps import Step

TC = namedtuple("TC", ["step", "result"])


def test_step():
    assert f"{Step.PULL!r}" == "Step.PULL"
    assert f"{Step.BUILD!r}" == "Step.BUILD"
    assert f"{Step.STAGE!r}" == "Step.STAGE"
    assert f"{Step.PRIME!r}" == "Step.PRIME"


def test_ordering():
    slist = list(Step)
    assert sorted(slist) == [Step.PULL, Step.BUILD, Step.STAGE, Step.PRIME]


@pytest.mark.parametrize(
    "tc",
    [
        TC(Step.PULL, []),
        TC(Step.BUILD, [Step.PULL]),
        TC(Step.STAGE, [Step.PULL, Step.BUILD]),
        TC(Step.PRIME, [Step.PULL, Step.BUILD, Step.STAGE]),
    ],
)
def test_previous_steps(tc):
    assert tc.step.previous_steps() == tc.result


@pytest.mark.parametrize(
    "tc",
    [
        TC(Step.PULL, [Step.BUILD, Step.STAGE, Step.PRIME]),
        TC(Step.BUILD, [Step.STAGE, Step.PRIME]),
        TC(Step.STAGE, [Step.PRIME]),
        TC(Step.PRIME, []),
    ],
)
def test_next_steps(tc):
    assert tc.step.next_steps() == tc.result


@pytest.mark.parametrize(
    "tc",
    [
        TC(Step.PULL, None),
        TC(Step.BUILD, Step.STAGE),
        TC(Step.STAGE, Step.STAGE),
        TC(Step.PRIME, Step.PRIME),
    ],
)
def test_prerequisite_step(tc):
    assert steps.dependency_prerequisite_step(tc.step) == tc.result
