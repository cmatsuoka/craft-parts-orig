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

import pytest

from craft_parts.filesets import Fileset

FilesetTC = namedtuple("FilesetTC", ["entries", "includes", "excludes"])


@pytest.mark.parametrize(
    "tc",
    [
        FilesetTC([], [], []),
        FilesetTC(["a", "b"], ["a", "b"], []),
        FilesetTC(["a", "-b"], ["a"], ["b"]),
    ],
)
def test_fileset(tc):
    fs = Fileset(tc.entries)
    assert fs.entries == tc.entries
    assert fs.includes == tc.includes
    assert fs.excludes == tc.excludes


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


CombineTC = namedtuple("CombineTC", ["fs1", "fs2", "result"])


@pytest.mark.parametrize(
    "tc",
    [
        CombineTC([], [], []),
        CombineTC(["foo"], ["bar"], ["bar"]),
        # combine if fs2 has a wildcard
        CombineTC(["foo"], ["bar", "*"], ["foo", "bar"]),
        # combine if fs2 is only excludes
        CombineTC(["foo"], ["-bar"], ["foo", "-bar"]),
        CombineTC(["foo", "*"], ["bar"], ["bar"]),
        CombineTC(["-foo"], ["-bar"], ["-foo", "-bar"]),
        CombineTC(["-foo"], ["bar"], ["bar"]),
        CombineTC(["foo"], ["-bar", "baz"], ["-bar", "baz"]),
        CombineTC(["-foo", "bar"], ["bar"], ["bar"]),
    ],
)
def test_combine(tc):
    fs1 = Fileset(tc.fs1)
    fs2 = Fileset(tc.fs2)
    fs1.combine(fs2)
    assert sorted(fs1.entries) == sorted(tc.result)


# TODO: test migratable_filesets
