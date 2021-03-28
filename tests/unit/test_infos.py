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

from pathlib import Path

import pytest

from craft_parts import errors
from craft_parts.dirs import ProjectDirs
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.parts import Part
from craft_parts.steps import Step

_MOCK_NATIVE_ARCH = "aarch64"


@pytest.mark.parametrize(
    "tc_arch,tc_target_arch,tc_triplet,tc_cross",
    [
        ("aarch64", "arm64", "aarch64-linux-gnu", False),
        ("armv7l", "armhf", "arm-linux-gnueabihf", True),
        ("i686", "i386", "i386-linux-gnu", True),
        ("ppc", "powerpc", "powerpc-linux-gnu", True),
        ("ppc64le", "ppc64el", "powerpc64le-linux-gnu", True),
        ("riscv64", "riscv64", "riscv64-linux-gnu", True),
        ("s390x", "s390x", "s390x-linux-gnu", True),
        ("x86_64", "amd64", "x86_64-linux-gnu", True),
    ],
)
def test_project_info(mocker, new_dir, tc_arch, tc_target_arch, tc_triplet, tc_cross):
    mocker.patch("platform.machine", return_value=_MOCK_NATIVE_ARCH)

    x = ProjectInfo(
        application_name="test",
        target_arch=tc_arch,
        parallel_build_count=16,
        local_plugins_dir="/some/path",
        custom1="foobar",
        custom2=[1, 2],
    )

    assert x.application_name == "test"
    assert x.arch_triplet == tc_triplet
    assert x.is_cross_compiling == tc_cross
    assert x.plugin_version == "v2"
    assert x.parallel_build_count == 16
    assert x.local_plugins_dir == Path("/some/path")
    assert x.target_arch == tc_target_arch
    assert x.project_options == {
        "application_name": "test",
        "arch_triplet": tc_triplet,
        "target_arch": tc_target_arch,
    }

    assert x.parts_dir == new_dir / "parts"
    assert x.stage_dir == new_dir / "stage"
    assert x.prime_dir == new_dir / "prime"


def test_project_info_work_dir(new_dir):
    dirs = ProjectDirs(work_dir="work_dir")
    info = ProjectInfo(custom1="foobar", custom2=[1, 2], project_dirs=dirs)

    assert info.parts_dir == new_dir / "work_dir/parts"
    assert info.stage_dir == new_dir / "work_dir/stage"
    assert info.prime_dir == new_dir / "work_dir/prime"


def test_project_info_custom_args():
    info = ProjectInfo(custom1="foobar", custom2=[1, 2])

    assert info.custom_args == ["custom1", "custom2"]
    assert info.custom1 == "foobar"
    assert info.custom2 == [1, 2]


def test_project_info_default():
    x = ProjectInfo()

    assert x.application_name == "craft_parts"
    assert x.parallel_build_count == 1


@pytest.mark.parametrize(
    "tc_param,tc_result",
    [
        (Path("/some/path"), Path("/some/path")),
        ("/some/path", Path("/some/path")),
        (None, None),
    ],
)
def test_local_plugin_dir(tc_param, tc_result):
    info = ProjectInfo(
        target_arch="x86_64",
        local_plugins_dir=tc_param,
    )
    assert info.local_plugins_dir == tc_result


def test_invalid_arch():
    with pytest.raises(errors.InvalidArchitecture) as raised:
        ProjectInfo(
            target_arch="invalid",
        )
    assert str(raised.value) == "Architecture 'invalid' is not supported."


def test_part_info(new_dir):
    info = ProjectInfo(custom1="foobar", custom2=[1, 2])
    part = Part("foo", {})
    x = PartInfo(project_info=info, part=part)

    assert x.application_name == "craft_parts"
    assert x.parallel_build_count == 1

    assert x.part_name == "foo"
    assert x.part_src_dir == new_dir / "parts/foo/src"
    assert x.part_src_work_dir == new_dir / "parts/foo/src"
    assert x.part_build_dir == new_dir / "parts/foo/build"
    assert x.part_build_work_dir == new_dir / "parts/foo/build"
    assert x.part_install_dir == new_dir / "parts/foo/install"
    assert x.stage_dir == new_dir / "stage"
    assert x.prime_dir == new_dir / "prime"

    assert x.custom_args == ["custom1", "custom2"]
    assert x.custom1 == "foobar"
    assert x.custom2 == [1, 2]


def test_step_info(new_dir):
    info = ProjectInfo(custom1="foobar", custom2=[1, 2])
    part = Part("foo", {})
    part_info = PartInfo(project_info=info, part=part)
    x = StepInfo(part_info=part_info, step=Step.BUILD)

    assert x.application_name == "craft_parts"
    assert x.parallel_build_count == 1

    assert x.part_name == "foo"
    assert x.part_src_dir == new_dir / "parts/foo/src"
    assert x.part_src_work_dir == new_dir / "parts/foo/src"
    assert x.part_build_dir == new_dir / "parts/foo/build"
    assert x.part_build_work_dir == new_dir / "parts/foo/build"
    assert x.part_install_dir == new_dir / "parts/foo/install"
    assert x.stage_dir == new_dir / "stage"
    assert x.prime_dir == new_dir / "prime"

    assert x.step == Step.BUILD

    assert x.custom_args == ["custom1", "custom2"]
    assert x.custom1 == "foobar"
    assert x.custom2 == [1, 2]
