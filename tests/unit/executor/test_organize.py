# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2021 Canonical Ltd
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

import os
import re
from pathlib import Path
from typing import Any, List

import pytest

from craft_parts.executor.organize import organize_filesets
from craft_parts.filesets import Fileset


class TestOrganize:
    @pytest.mark.parametrize(
        "tc,data",
        [
            (
                "simple_file",
                dict(
                    setup_dirs=[],
                    setup_files=["foo"],
                    organize_set={"foo": "bar"},
                    expected=[(["bar"], "")],
                    expected_message=None,
                    expected_overwrite=None,
                ),
            ),
        ],
    )
    def test_organize(self, tmpdir, tc, data):
        self._organize_and_assert(
            tmp_path=Path(tmpdir),
            setup_dirs=data["setup_dirs"],
            setup_files=data["setup_files"],
            organize_set=data["organize_set"],
            expected=data["expected"],
            expected_message=data["expected_message"],
            expected_overwrite=data["expected_overwrite"],
            overwrite=False,
        )

        # Verify that it can be organized again by overwriting
        self._organize_and_assert(
            tmp_path=Path(tmpdir),
            setup_dirs=data["setup_dirs"],
            setup_files=data["setup_files"],
            organize_set=data["organize_set"],
            expected=data["expected"],
            expected_message=data["expected_message"],
            expected_overwrite=data["expected_overwrite"],
            overwrite=True,
        )

    def _organize_and_assert(
        self,
        *,
        tmp_path: Path,
        setup_dirs,
        setup_files,
        organize_set,
        expected: List[Any],
        expected_message,
        expected_overwrite,
        overwrite,
    ):
        base_dir = tmp_path / "install"
        base_dir.mkdir(parents=True, exist_ok=True)

        for directory in setup_dirs:
            (base_dir / directory).mkdir(exist_ok=True)

        for file_entry in setup_files:
            (base_dir / file_entry).touch()

        if overwrite and expected_overwrite is not None:
            expected = expected_overwrite

        organize_fileset = Fileset(organize_set)

        if isinstance(expected, type) and issubclass(expected, Exception):
            with pytest.raises(expected) as error:
                organize_filesets(
                    part_name="part-name",
                    fileset=organize_fileset,
                    base_dir=base_dir,
                    overwrite=overwrite,
                )
            assert re.match(expected_message, str(error)) is not None

        else:
            organize_filesets(
                part_name="part-name",
                fileset=Fileset(organize_set),
                base_dir=base_dir,
                overwrite=overwrite,
            )
            for expect in expected:
                dir_path = (base_dir / expect[1]).as_posix()
                dir_contents = os.listdir(dir_path)
                dir_contents.sort()
                assert dir_contents == expect[0]
