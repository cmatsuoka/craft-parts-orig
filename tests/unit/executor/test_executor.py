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

import pytest

from craft_parts.executor import Executor
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part


@pytest.mark.usefixtures("new_dir")
class TestBuildPackages:
    def test_install_build_packages(self, mocker):
        install = mocker.patch("craft_parts.packages.Repository.install_build_packages")

        part1 = Part("foo", {"plugin": "nil", "build-packages": ["pkg1"]})
        part2 = Part("bar", {"plugin": "nil", "build-packages": ["pkg2"]})
        info = ProjectInfo()

        e = Executor(project_info=info, part_list=[part1, part2])
        e.prologue()

        install.assert_called_once_with(["pkg1", "pkg2"])

    def test_install_extra_build_packages(self, mocker):
        install = mocker.patch("craft_parts.packages.Repository.install_build_packages")

        part1 = Part("foo", {"plugin": "nil", "build-packages": ["pkg1"]})
        part2 = Part("bar", {"plugin": "nil", "build-packages": ["pkg2"]})
        info = ProjectInfo()

        e = Executor(
            project_info=info,
            part_list=[part1, part2],
            extra_build_packages=["pkg3"],
        )
        e.prologue()

        install.assert_called_once_with(["pkg1", "pkg2", "pkg3"])
