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

import textwrap
from pathlib import Path

import pytest

from craft_parts import sequencer
from craft_parts.actions import Action, ActionType
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part
from craft_parts.schemas import Validator
from craft_parts.steps import Step

_pull_state_foo = textwrap.dedent(
    """\
    !PullState
    properties:
      plugin: nil
    project_options:
      target_arch: amd64
    assets:
      stage-packages:
      - fake-package-foo=1
    """
)

_pull_state_bar = textwrap.dedent(
    """\
    !PullState
    properties:
      plugin: nil
    project_options:
      target_arch: amd64
    assets:
      stage-packages:
      - fake-package-bar=2
    """
)


@pytest.fixture
def fake_validator(mocker) -> Validator:
    mocker.patch("craft_parts.schemas.Validator._load_schema")
    mocker.patch("craft_parts.schemas.Validator.merge_schema", return_value=dict())
    mocker.patch("craft_parts.schemas.Validator.schema", return_value=dict())
    mocker.patch("craft_parts.schemas.Validator.validate", return_value=True)
    return Validator("")


@pytest.fixture
def pull_state(new_dir):
    # build current state
    Path(new_dir / "parts/foo/state").mkdir(parents=True)
    Path(new_dir / "parts/bar/state").mkdir(parents=True)
    Path(new_dir / "parts/foo/state/pull").write_text(_pull_state_foo)
    Path(new_dir / "parts/bar/state/pull").write_text(_pull_state_bar)


@pytest.mark.usefixtures("new_dir")
class TestSequencerPlan:
    """Verify action planning sanity."""

    def test_plan_default_parts(self, fake_validator):
        p1 = Part("foo", {"plugin": "nil"})
        p2 = Part("bar", {"plugin": "nil"})

        seq = sequencer.Sequencer(
            part_list=[p1, p2],
            validator=fake_validator,
            project_info=ProjectInfo(),
        )

        actions = seq.plan(Step.PRIME)
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.RUN),
            Action("foo", Step.PULL, action_type=ActionType.RUN),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("foo", Step.BUILD, action_type=ActionType.RUN),
            Action("bar", Step.STAGE, action_type=ActionType.RUN),
            Action("foo", Step.STAGE, action_type=ActionType.RUN),
            Action("bar", Step.PRIME, action_type=ActionType.RUN),
            Action("foo", Step.PRIME, action_type=ActionType.RUN),
        ]

    def test_plan_dependencies(self, fake_validator):
        p1 = Part("foo", {"plugin": "nil", "after": ["bar"]})
        p2 = Part("bar", {"plugin": "nil"})

        seq = sequencer.Sequencer(
            part_list=[p1, p2],
            validator=fake_validator,
            project_info=ProjectInfo(),
        )

        # pylint: disable=line-too-long
        # fmt: off
        actions = seq.plan(Step.PRIME)
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.RUN),
            Action("foo", Step.PULL, action_type=ActionType.RUN),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
            Action("bar", Step.STAGE, action_type=ActionType.RUN, reason="required to build 'foo'"),
            Action("foo", Step.BUILD, action_type=ActionType.RUN),
            Action("bar", Step.STAGE, action_type=ActionType.SKIP, reason="already ran"),
            Action("foo", Step.STAGE, action_type=ActionType.RUN),
            Action("bar", Step.PRIME, action_type=ActionType.RUN),
            Action("foo", Step.PRIME, action_type=ActionType.RUN),
        ]
        # fmt: on

    def test_plan_specific_part(self, fake_validator):
        p1 = Part("foo", {"plugin": "nil"})
        p2 = Part("bar", {"plugin": "nil"})

        seq = sequencer.Sequencer(
            part_list=[p1, p2],
            validator=fake_validator,
            project_info=ProjectInfo(),
        )

        actions = seq.plan(Step.PRIME, part_names=["bar"])
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.RUN),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("bar", Step.STAGE, action_type=ActionType.RUN),
            Action("bar", Step.PRIME, action_type=ActionType.RUN),
        ]


@pytest.mark.usefixtures("new_dir", "pull_state")
class TestSequencerStates:
    """Check existing state loading."""

    def test_plan_load_state(self, fake_validator):
        p1 = Part("foo", {"plugin": "nil"})
        p2 = Part("bar", {"plugin": "nil"})

        seq = sequencer.Sequencer(
            part_list=[p1, p2],
            validator=fake_validator,
            project_info=ProjectInfo(),
        )

        actions = seq.plan(Step.BUILD)
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("foo", Step.BUILD, action_type=ActionType.RUN),
        ]

    def test_plan_reload_state(self, fake_validator):
        p1 = Part("foo", {"plugin": "nil"})
        p2 = Part("bar", {"plugin": "nil"})

        seq = sequencer.Sequencer(
            part_list=[p1, p2],
            validator=fake_validator,
            project_info=ProjectInfo(),
        )

        Path("parts/foo/state/pull").unlink()
        Path("parts/bar/state/pull").unlink()

        actions = seq.plan(Step.BUILD)
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("foo", Step.BUILD, action_type=ActionType.RUN),
        ]

        seq.reload_state()

        actions = seq.plan(Step.BUILD)
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.RUN),
            Action("foo", Step.PULL, action_type=ActionType.RUN),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("foo", Step.BUILD, action_type=ActionType.RUN),
        ]