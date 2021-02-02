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

import yaml

import craft_parts
from craft_parts import Action, ActionType, Step

# See https://gist.github.com/sergiusens/dcae19c301eb59e091f92ab29d7d03fc

parts_yaml = textwrap.dedent(
    """\
    parts:
      bar:
        after: [foo]
        plugin: nil

      foo:
        plugin: nil

      foobar:
        plugin: nil"""
)


def test_actions_simple(tmpdir):
    parts = yaml.safe_load(parts_yaml)
    lf = craft_parts.LifecycleManager(parts, work_dir=tmpdir)

    # first run
    # command: pull
    actions = lf.plan(Step.PULL, update=False)
    assert actions == [
        Action("foo", Step.PULL),
        Action("bar", Step.PULL),
        Action("foobar", Step.PULL),
    ]

    # foobar part depends on nothing
    # command: prime foobar
    actions = lf.plan(Step.PRIME, ["foobar"], update=False)
    assert actions == [
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.BUILD),
        Action("foobar", Step.STAGE),
        Action("foobar", Step.PRIME),
    ]

    # Then running build for bar that depends on foo
    # command: build bar
    actions = lf.plan(Step.BUILD, ["bar"], update=False)
    assert actions == [
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, reason="required to build bar"),
        Action("foo", Step.STAGE, reason="required to build bar"),
        Action("bar", Step.BUILD),
    ]

    # Building bar again rebuilds it (explicit request)
    actions = lf.plan(Step.BUILD, ["bar"], update=False)
    assert actions == [
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "bar", Step.BUILD, action_type=ActionType.RERUN, reason="requested step"
        ),
    ]

    # Modifying foo’s source marks bar as dirty
    # command: build bar
    # TODO: add this test
