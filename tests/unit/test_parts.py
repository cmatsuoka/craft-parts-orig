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

from craft_parts import errors, parts
from craft_parts.parts import Part


class TestPartBasics:
    """Test basic part creation and representation."""

    def test_part(self):
        p = Part("foo", {"bar": "baz"})
        assert f"{p!r}" == "Part('foo')"
        assert p.name == "foo"
        assert p.data == {"bar": "baz"}
        assert p.part_src_dir == Path("./parts/foo/src")
        assert p.part_build_dir == Path("./parts/foo/build")
        assert p.part_state_dir == Path("./parts/foo/state")
        assert p.part_run_dir == Path("./parts/foo/run")
        assert p.stage_dir == Path("./stage")
        assert p.prime_dir == Path("./prime")

    def test_part_work_dir(self):
        p = Part("foo", {}, work_dir="foobar")
        assert p.part_src_dir == Path("foobar/parts/foo/src")
        assert p.part_build_dir == Path("foobar/parts/foo/build")
        assert p.part_state_dir == Path("foobar/parts/foo/state")
        assert p.part_run_dir == Path("foobar/parts/foo/run")
        assert p.stage_dir == Path("foobar/stage")
        assert p.prime_dir == Path("foobar/prime")


class TestPartOrdering:
    """Test part ordering.

    Parts should be ordered primarily by dependencies, and then by
    part name.
    """

    def test_sort_parts(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {"after": ["baz"]})
        p3 = Part("baz", {"after": ["foo"]})

        x = parts.sort_parts([p1, p2, p3])
        assert x == [p1, p3, p2]

    def test_sort_parts_multiple(self):
        p1 = Part("foo", {"after": ["bar", "baz"]})
        p2 = Part("bar", {"after": ["baz"]})
        p3 = Part("baz", {})

        x = parts.sort_parts([p1, p2, p3])
        assert x == [p3, p2, p1]

    def test_sort_parts_name(self):
        p1 = Part("baz", {"after": ["foo"]})
        p2 = Part("bar", {"after": ["foo"]})
        p3 = Part("foo", {})

        x = parts.sort_parts([p1, p2, p3])
        assert x == [p3, p2, p1]

    def test_sort_parts_cycle(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {"after": ["baz"]})
        p3 = Part("baz", {"after": ["bar"]})

        with pytest.raises(errors.PartDependencyCycle) as ei:
            parts.sort_parts([p1, p2, p3])
        assert ei.value.get_brief() == "A circular dependency chain was detected."


class TestPartHelpers:
    """Test part-related helper functions."""

    def test_part_by_name(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {})
        p3 = Part("baz", {})

        x = parts.part_by_name("bar", [p1, p2, p3])
        assert x == p2

        with pytest.raises(errors.InvalidPartName) as ei:
            parts.part_by_name("invalid", [p1, p2, p3])
        assert (
            ei.value.get_brief()
            == "A part named 'invalid' is not defined in the parts list."
        )

    def test_part_dependencies(self):
        p1 = Part("foo", {"after": ["bar", "baz"]})
        p2 = Part("bar", {"after": ["qux"]})
        p3 = Part("baz", {})
        p4 = Part("qux", {})

        x = parts.part_dependencies("foo", part_list=[p1, p2, p3, p4])
        assert x == {p2, p3}

        x = parts.part_dependencies("foo", part_list=[p1, p2, p3, p4], recursive=True)
        assert x == {p2, p3, p4}

        with pytest.raises(errors.InvalidPartName) as ei:
            parts.part_dependencies("invalid", part_list=[p1, p2, p3, p4])
        assert (
            ei.value.get_brief()
            == "A part named 'invalid' is not defined in the parts list."
        )
