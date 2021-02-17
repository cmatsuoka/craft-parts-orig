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
        source: a.tar.gz

      foobar:
        plugin: nil"""
)


def test_actions_simple(new_dir, mocker):
    parts = yaml.safe_load(parts_yaml)

    Path("a.tar.gz").touch()
    mocker.patch("craft_parts.sources.Tar.provision")  # don't try to untar the file

    # first run
    # command: pull
    lf = craft_parts.LifecycleManager(parts, application_name="test_demo")
    actions = lf.plan(Step.PULL)
    assert actions == [
        Action("foo", Step.PULL),
        Action("bar", Step.PULL),
        Action("foobar", Step.PULL),
    ]
    lf.execute(actions)

    # foobar part depends on nothing
    # command: prime foobar
    lf = craft_parts.LifecycleManager(parts, application_name="test_demo")
    actions = lf.plan(Step.PRIME, ["foobar"])
    assert actions == [
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.BUILD),
        Action("foobar", Step.STAGE),
        Action("foobar", Step.PRIME),
    ]
    lf.execute(actions)

    # Then running build for bar that depends on foo
    # command: build bar
    lf = craft_parts.LifecycleManager(parts, application_name="test_demo")
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, reason="required to build bar"),
        Action("foo", Step.STAGE, reason="required to build bar"),
        Action("bar", Step.BUILD),
    ]
    lf.execute(actions)

    # Building bar again rebuilds it (explicit request)
    lf = craft_parts.LifecycleManager(parts, application_name="test_demo")
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "bar", Step.BUILD, action_type=ActionType.RERUN, reason="requested step"
        ),
    ]
    lf.execute(actions)

    # Modifying foo’s source marks bar as dirty
    Path("b.tar.gz").touch()
    new_yaml = parts_yaml.replace("source: a.tar.gz", "source: b.tar.gz")
    parts = yaml.safe_load(new_yaml)

    lf = craft_parts.LifecycleManager(parts, application_name="test_demo")
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        # fmt: off
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.RERUN, reason="'source' property changed"),
        Action("foo", Step.BUILD, action_type=ActionType.RUN, reason="required to build bar"),
        Action("foo", Step.STAGE, action_type=ActionType.RUN, reason="required to build bar"),
        Action("bar", Step.BUILD, action_type=ActionType.RERUN, reason="requested step"),
        # fmt: on
    ]
    lf.execute(actions)
