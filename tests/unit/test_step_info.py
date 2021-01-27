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
from pathlib import Path

import pytest

from craft_parts import errors
from craft_parts.parts import Part
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step

_MOCK_NATIVE_ARCH = "aarch64"

ArchTC = namedtuple("ArchTC", ["arch", "deb_arch", "triplet", "cross"])


@pytest.mark.parametrize(
    "tc",
    [
        ArchTC("aarch64", "arm64", "aarch64-linux-gnu", False),
        ArchTC("armv7l", "armhf", "arm-linux-gnueabihf", True),
        ArchTC("i686", "i386", "i386-linux-gnu", True),
        ArchTC("ppc", "powerpc", "powerpc-linux-gnu", True),
        ArchTC("ppc64le", "ppc64el", "powerpc64le-linux-gnu", True),
        ArchTC("riscv64", "riscv64", "riscv64-linux-gnu", True),
        ArchTC("s390x", "s390x", "s390x-linux-gnu", True),
        ArchTC("x86_64", "amd64", "x86_64-linux-gnu", True),
    ],
)
def test_step_info(mocker, tc):
    mocker.patch("platform.machine", return_value=_MOCK_NATIVE_ARCH)

    info = StepInfo(
        target_arch=tc.arch,
        parallel_build_count=16,
        local_plugins_dir="/some/path",
        foo="foo",
        bar=["bar"],
    )

    assert info.arch_triplet == tc.triplet
    assert info.is_cross_compiling == tc.cross
    assert info.parallel_build_count == 16
    assert info.local_plugins_dir == Path("/some/path")
    assert info.deb_arch == tc.deb_arch


PluginPathTC = namedtuple("PluginPathTC", ["param", "result"])


@pytest.mark.parametrize(
    "tc",
    [
        PluginPathTC(Path("/some/path"), Path("/some/path")),
        PluginPathTC("/some/path", Path("/some/path")),
        PluginPathTC(None, None),
    ],
)
def test_local_plugin_dir(tc):
    info = StepInfo(
        target_arch="x86_64", parallel_build_count=1, local_plugins_dir=tc.param
    )
    assert info.local_plugins_dir == tc.result


def test_invalid_arch():
    with pytest.raises(errors.InvalidArchitecture) as ei:
        StepInfo(target_arch="invalid", parallel_build_count=1, local_plugins_dir=None)
    assert ei.value.get_brief() == "Architecture 'invalid' is invalid."


def test_update_part_data():
    info = StepInfo()
    part = Part("foo", {})
    x = info.for_part(part)
    cwd = Path().absolute()
    assert x.part_src_dir == cwd / "parts/foo/src"
    assert x.part_src_work_dir == cwd / "parts/foo/src"
    assert x.part_build_dir == cwd / "parts/foo/build"
    assert x.part_build_work_dir == cwd / "parts/foo/build"
    assert x.part_install_dir == cwd / "parts/foo/install"
    assert x.stage_dir == cwd / "stage"
    assert x.prime_dir == cwd / "prime"

    # The original info shouldn't change
    assert info.part_src_dir == Path()
    assert info.part_src_work_dir == Path()
    assert info.part_build_dir == Path()
    assert info.part_build_work_dir == Path()
    assert info.part_install_dir == Path()
    assert info.stage_dir == Path()
    assert info.prime_dir == Path()


def test_update_step_data():
    info = StepInfo()
    x = info.for_step(Step.BUILD)
    assert x.step == Step.BUILD
    assert info.step is None
