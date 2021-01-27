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
from craft_parts import Action, ActionType, Step, StepInfo, callbacks

_parts_yaml = textwrap.dedent(
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


def setup_function():
    callbacks.clear()


def teardown_module():
    callbacks.clear()


def _my_callback(info: StepInfo) -> bool:
    msg = getattr(info, "message")
    print(msg)
    return True


def _info_callback(info: StepInfo) -> bool:
    print(f"step = {info.step!r}")
    print(f"part_src_dir = {info.part_src_dir}")
    print(f"part_build_dir = {info.part_build_dir}")
    print(f"part_install_dir = {info.part_install_dir}")
    return True


@pytest.mark.parametrize("step", list(Step))
@pytest.mark.parametrize("action_type", list(ActionType))
def test_callback_pre(tmpdir, capfd, step, action_type):
    callbacks.register_pre(_my_callback, step_list=[step])

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(parts, work_dir=tmpdir, message="callback")

    lf.execute(Action("foo", step, action_type=action_type))
    out, err = capfd.readouterr()
    assert not err
    if action_type in [ActionType.SKIP, ActionType.UPDATE]:
        assert not out
    else:
        assert out == f"callback\noverride {step!r}\n"


@pytest.mark.parametrize("step", list(Step))
@pytest.mark.parametrize("action_type", list(ActionType))
def test_callback_post(tmpdir, capfd, step, action_type):
    callbacks.register_post(_my_callback, step_list=[step])

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(parts, work_dir=tmpdir, message="callback")

    lf.execute(Action("foo", step, action_type=action_type))
    out, err = capfd.readouterr()
    assert not err
    if action_type in [ActionType.SKIP, ActionType.UPDATE]:
        assert not out
    else:
        assert out == f"override {step!r}\ncallback\n"


@pytest.mark.parametrize("step", list(Step))
def test_callback_step_info(tmpdir, capfd, step):
    callbacks.register_pre(_info_callback, step_list=[step])

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(parts, work_dir=tmpdir)

    lf.execute(Action("foo", step))
    out, err = capfd.readouterr()
    assert not err
    assert out == (
        f"step = {step!r}\n"
        f"part_src_dir = {tmpdir}/parts/foo/src\n"
        f"part_build_dir = {tmpdir}/parts/foo/build\n"
        f"part_install_dir = {tmpdir}/parts/foo/install\n"
        f"override {step!r}\n"
    )
