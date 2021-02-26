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
from unittest.mock import ANY

import pytest

from craft_parts.executor.part_handler import PartHandler
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.parts import Part
from craft_parts.schemas import Validator
from craft_parts.steps import Step


@pytest.fixture(autouse=True)
def fake_installed_stuff(mocker):
    mocker.patch(
        "craft_parts.packages.Repository.get_installed_packages",
        return_value=["a_package"],
    )
    mocker.patch(
        "craft_parts.packages.snaps.get_installed_snaps", return_value=["a_snap"]
    )


@pytest.fixture
def fake_validator(mocker) -> Validator:
    mocker.patch("craft_parts.schemas.Validator._load_schema")
    mocker.patch("craft_parts.schemas.Validator.merge_schema", return_value=dict())
    mocker.patch("craft_parts.schemas.Validator.schema", return_value=dict())
    mocker.patch("craft_parts.schemas.Validator.validate", return_value=True)
    return Validator("")


class TestStagePackages:
    def test_unpack_stage_packages(self, mocker, new_dir, fake_validator):
        getpkg = mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )
        unpack = mocker.patch("craft_parts.packages.Repository.unpack_stage_packages")
        mocker.patch("craft_parts.executor.part_handler.PartHandler._run_step")

        part1 = Part("foo", {"plugin": "nil", "stage-packages": ["pkg1"]})
        part_info = PartInfo(ProjectInfo(), part1)

        handler = PartHandler(
            part1,
            plugin_version="v2",
            part_info=part_info,
            part_list=[part1],
            validator=fake_validator,
        )

        state = handler._run_pull(StepInfo(part_info, Step.PULL))
        getpkg.assert_called_once_with(
            application_name="craft_parts",
            base=ANY,
            list_only=False,
            package_names=["pkg1"],
            stage_packages_path=Path(new_dir / "parts/foo/stage_packages"),
            target_arch=ANY,
        )

        assert state.assets["stage-packages"] == ["pkg1", "pkg2"]

        handler._run_build(StepInfo(part_info, Step.BUILD))
        unpack.assert_called_once()

    def test_dont_unpack_stage_packages(self, new_dir, mocker, fake_validator):
        getpkg = mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )
        unpack = mocker.patch("craft_parts.packages.Repository.unpack_stage_packages")
        mocker.patch("craft_parts.executor.part_handler.PartHandler._run_step")

        part1 = Part("foo", {"plugin": "nil", "stage-packages": ["pkg1"]})
        part_info = PartInfo(ProjectInfo(), part1)

        handler = PartHandler(
            part1,
            plugin_version="v2",
            part_info=part_info,
            part_list=[part1],
            validator=fake_validator,
            disable_stage_packages=True,
        )

        state = handler._run_pull(StepInfo(part_info, Step.PULL))
        getpkg.assert_called_once_with(
            application_name="craft_parts",
            base=ANY,
            list_only=True,
            package_names=["pkg1"],
            stage_packages_path=Path(new_dir / "parts/foo/stage_packages"),
            target_arch=ANY,
        )

        assert state.assets["stage-packages"] == ["pkg1", "pkg2"]

        handler._run_build(StepInfo(part_info, Step.BUILD))
        unpack.assert_not_called()
