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

import pytest
import yaml

import craft_parts
from craft_parts import Action, ActionType, Step


@pytest.mark.parametrize("step", list(Step))
@pytest.mark.parametrize("action_type", list(ActionType))
def test_override(tmpdir, capfd, step, action_type):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: echo "override Step.PULL"
            override-build: echo "override Step.BUILD"
            override-stage: echo "override Step.STAGE"
            override-prime: echo "override Step.PRIME"
        """
    )

    parts = yaml.safe_load(parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_runner", work_dir=tmpdir
    )

    lf.execute(Action("foo", step, action_type=action_type))
    out, err = capfd.readouterr()
    assert not err
    if action_type in [ActionType.SKIP, ActionType.UPDATE]:
        assert not out
    else:
        assert out == f"override {step!r}\n"
