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

from unittest.mock import ANY

import pytest

from craft_parts.sources.local import Local
from craft_parts.utils import file_utils


@pytest.fixture
def handler(mocker) -> Local:
    def _abspath(x):
        return f"/abspath/{x}"

    mocker.patch("os.path.abspath", side_effect=_abspath)
    mocker.patch("os.getcwd", return_value="current_dir")

    return Local(
        source="source",
        source_dir="source_dir",
        source_checksum="source-checksum",
        source_branch="source-branch",
        source_tag="source-tag",
        source_depth="source-depth",
        source_commit="source-commit",
    )


def test_pull(handler, mocker):
    mocked_link_or_copy_tree = mocker.patch(
        "craft_parts.utils.file_utils.link_or_copy_tree"
    )

    handler.pull()
    mocked_link_or_copy_tree.assert_called_with(
        "/abspath/source",
        "source_dir",
        ignore=ANY,
        copy_function=file_utils.link_or_copy,
    )
