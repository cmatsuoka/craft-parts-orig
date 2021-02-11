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

from craft_parts.filesets import Fileset


@pytest.mark.parametrize(
    "tc_data,tc_entries,tc_includes,tc_excludes",
    [
        ([], [], [], []),
        (["a", "b"], ["a", "b"], ["a", "b"], []),
        (["a", "-b"], ["a", "-b"], ["a"], ["b"]),
        ({"a": "1", "b": "2"}, ["a", "b"], ["a", "b"], []),
    ],
)
def test_fileset(tc_data, tc_entries, tc_includes, tc_excludes):
    fs = Fileset(tc_data)
    assert fs.entries == tc_entries
    assert fs.includes == tc_includes
    assert fs.excludes == tc_excludes


def test_representation():
    fs = Fileset(["foo", "bar"])
    assert f"{fs!r}" == "Fileset(['foo', 'bar'])"


def test_entries():
    fs = Fileset(["foo", "bar"])
    fs.entries.append("baz")
    assert fs.entries == ["foo", "bar"]


def test_remove():
    fs = Fileset(["foo", "bar", "baz"])
    fs.remove("bar")
    assert fs.entries == ["foo", "baz"]


@pytest.mark.parametrize(
    "tc_fs1,tc_fs2,tc_result",
    [
        ([], [], []),
        (["foo"], ["bar"], ["bar"]),
        # combine if fs2 has a wildcard
        (["foo"], ["bar", "*"], ["foo", "bar"]),
        # combine if fs2 is only excludes
        (["foo"], ["-bar"], ["foo", "-bar"]),
        (["foo", "*"], ["bar"], ["bar"]),
        (["-foo"], ["-bar"], ["-foo", "-bar"]),
        (["-foo"], ["bar"], ["bar"]),
        (["foo"], ["-bar", "baz"], ["-bar", "baz"]),
        (["-foo", "bar"], ["bar"], ["bar"]),
    ],
)
def test_combine(tc_fs1, tc_fs2, tc_result):
    fs1 = Fileset(tc_fs1)
    fs2 = Fileset(tc_fs2)
    fs1.combine(fs2)
    assert sorted(fs1.entries) == sorted(tc_result)


# TODO: test migratable_filesets
