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
from craft_parts.steps import Step


class TestPartBasics:
    """Test basic part creation and representation."""

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        self._cwd = Path.cwd()

    def test_part(self):
        p = Part("foo", {"bar": "baz"})
        assert f"{p!r}" == "Part('foo')"
        assert p.name == "foo"
        assert p.properties == {"bar": "baz"}
        assert p.part_src_dir == self._cwd / "parts/foo/src"
        assert p.part_build_dir == self._cwd / "./parts/foo/build"
        assert p.part_state_dir == self._cwd / "./parts/foo/state"
        assert p.part_package_dir == self._cwd / "./parts/foo/stage_packages"
        assert p.part_run_dir == self._cwd / "./parts/foo/run"
        assert p.stage_dir == self._cwd / "./stage"
        assert p.prime_dir == self._cwd / "./prime"

    def test_part_work_dir(self):
        p = Part("foo", {}, work_dir="foobar")
        assert p.part_src_dir == self._cwd / "foobar/parts/foo/src"
        assert p.part_build_dir == self._cwd / "foobar/parts/foo/build"
        assert p.part_state_dir == self._cwd / "foobar/parts/foo/state"
        assert p.part_package_dir == self._cwd / "foobar/parts/foo/stage_packages"
        assert p.part_run_dir == self._cwd / "foobar/parts/foo/run"
        assert p.stage_dir == self._cwd / "foobar/stage"
        assert p.prime_dir == self._cwd / "foobar/prime"

    def test_part_src_build_work_dir(self):
        p = Part("foo", {"source-subdir": "foobar"})
        assert p.part_src_dir == self._cwd / "./parts/foo/src"
        assert p.part_src_work_dir == self._cwd / "./parts/foo/src/foobar"
        assert p.part_build_dir == self._cwd / "./parts/foo/build"
        assert p.part_build_work_dir == self._cwd / "./parts/foo/build/foobar"

    def test_part_source(self):
        p = Part("foo", {})
        assert p.source is None

        p = Part("foo", {"source": "foobar"})
        assert p.source == "foobar"

    def test_part_properties(self):
        p = Part("foo", {"foo": "bar"})
        x = p.properties
        assert x == {"foo": "bar"}

        # should be immutable
        x["foo"] = "something else"
        assert p.properties == {"foo": "bar"}

    def test_part_stage_fileset(self):
        p = Part("foo", {"stage": ["a", "b", "c"]})
        x = p.stage_fileset
        assert x == ["a", "b", "c"]

        # should be immutable
        x.append("extra")
        assert p.stage_fileset == ["a", "b", "c"]

    def test_part_prime_fileset(self):
        p = Part("foo", {"prime": ["a", "b", "c"]})
        x = p.prime_fileset
        assert x == ["a", "b", "c"]

        # should be immutable
        x.append("extra")
        assert p.prime_fileset == ["a", "b", "c"]

    def test_part_dependencies(self):
        p = Part("foo", {"after": ["bar"]})
        x = p.dependencies
        assert x == ["bar"]

        # should be immutable
        x.append("extra")
        assert p.dependencies == ["bar"]

    def test_part_plugin(self):
        p = Part("foo", {"plugin": "nil"})
        assert p.plugin == "nil"

    def test_part_build_environment(self):
        p = Part("foo", {"build-environment": [{"BAR": "bar"}]})
        x = p.build_environment
        assert x == [{"BAR": "bar"}]

        # should be immutable
        x[0]["BAR"] = "something else"
        x.append({"FOOBAR": "foobar"})
        assert p.build_environment == [{"BAR": "bar"}]

    @pytest.mark.parametrize(
        "tc_step,tc_content",
        [
            (Step.PULL, "pull"),
            (Step.BUILD, "build"),
            (Step.STAGE, "stage"),
            (Step.PRIME, "prime"),
        ],
    )
    def test_part_get_scriptlet(self, tc_step, tc_content):
        p = Part(
            "foo",
            {
                "override-pull": "pull",
                "override-build": "build",
                "override-stage": "stage",
                "override-prime": "prime",
            },
        )
        assert p.get_scriptlet(tc_step) == tc_content

    @pytest.mark.parametrize(
        "step",
        [Step.PULL, Step.BUILD, Step.STAGE, Step.PRIME],
    )
    def test_part_get_scriptlet_none(self, step):
        p = Part("foo", {})
        assert p.get_scriptlet(step) is None


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
