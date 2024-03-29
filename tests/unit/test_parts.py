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

from craft_parts import errors, parts
from craft_parts.infos import ProjectDirs
from craft_parts.parts import Part
from craft_parts.steps import Step


class TestPartBasics:
    """Test basic part creation and representation."""

    def test_part(self, new_dir):
        p = Part("foo", {"plugin": "nil"})
        assert f"{p!r}" == "Part('foo')"
        assert p.name == "foo"
        assert p.parts_dir == new_dir / "parts"
        assert p.part_src_dir == new_dir / "parts/foo/src"
        assert p.part_build_dir == new_dir / "parts/foo/build"
        assert p.part_state_dir == new_dir / "parts/foo/state"
        assert p.part_packages_dir == new_dir / "parts/foo/stage_packages"
        assert p.part_snaps_dir == new_dir / "parts/foo/stage_snaps"
        assert p.part_run_dir == new_dir / "parts/foo/run"
        assert p.stage_dir == new_dir / "stage"
        assert p.prime_dir == new_dir / "prime"

    def test_part_work_dir(self, new_dir):
        p = Part("foo", {}, project_dirs=ProjectDirs(work_dir="foobar"))
        assert p.parts_dir == new_dir / "foobar/parts"
        assert p.part_src_dir == new_dir / "foobar/parts/foo/src"
        assert p.part_build_dir == new_dir / "foobar/parts/foo/build"
        assert p.part_state_dir == new_dir / "foobar/parts/foo/state"
        assert p.part_packages_dir == new_dir / "foobar/parts/foo/stage_packages"
        assert p.part_snaps_dir == new_dir / "foobar/parts/foo/stage_snaps"
        assert p.part_run_dir == new_dir / "foobar/parts/foo/run"
        assert p.stage_dir == new_dir / "foobar/stage"
        assert p.prime_dir == new_dir / "foobar/prime"

    def test_part_src_build_work_dir(self, new_dir):
        p = Part("foo", {"source-subdir": "foobar"})
        assert p.part_src_dir == new_dir / "parts/foo/src"
        assert p.part_src_subdir == new_dir / "parts/foo/src/foobar"
        assert p.part_build_dir == new_dir / "parts/foo/build"
        assert p.part_build_subdir == new_dir / "parts/foo/build/foobar"

    def test_part_source(self):
        p = Part("foo", {})
        assert p.spec.source is None

        p = Part("foo", {"source": "foobar"})
        assert p.spec.source == "foobar"

    def test_part_stage_fileset(self):
        p = Part("foo", {"stage": ["a", "b", "c"]})
        assert p.spec.stage_fileset == ["a", "b", "c"]

    def test_part_prime_fileset(self):
        p = Part("foo", {"prime": ["a", "b", "c"]})
        assert p.spec.prime_fileset == ["a", "b", "c"]

    def test_part_organize_fileset(self):
        p = Part("foo", {"organize": {"a": "b", "c": "d"}})
        assert p.spec.organize_fileset == {"a": "b", "c": "d"}

    def test_part_dependencies(self):
        p = Part("foo", {"after": ["bar"]})
        assert p.dependencies == ["bar"]

    def test_part_plugin(self):
        p = Part("foo", {"plugin": "nil"})
        assert p.spec.plugin == "nil"

    def test_part_plugin_missing(self):
        p = Part("foo", {})
        assert p.spec.plugin is None

    def test_part_build_environment(self):
        p = Part("foo", {"build-environment": [{"BAR": "bar"}]})
        assert p.spec.build_environment == [{"BAR": "bar"}]

    @pytest.mark.parametrize(
        "tc_spec,tc_result",
        [
            ({}, []),
            ({"stage-packages": []}, []),
            ({"stage-packages": ["foo", "bar"]}, ["foo", "bar"]),
        ],
    )
    def test_part_stage_packages(self, tc_spec, tc_result):
        p = Part("foo", tc_spec)
        assert p.spec.stage_packages == tc_result

    @pytest.mark.parametrize(
        "tc_spec,tc_result",
        [
            ({}, []),
            ({"build-packages": []}, []),
            ({"build-packages": ["foo", "bar"]}, ["foo", "bar"]),
        ],
    )
    def test_part_build_packages(self, tc_spec, tc_result):
        p = Part("foo", tc_spec)
        assert p.spec.build_packages == tc_result

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
        assert p.spec.get_scriptlet(tc_step) == tc_content

    @pytest.mark.parametrize(
        "step",
        [Step.PULL, Step.BUILD, Step.STAGE, Step.PRIME],
    )
    def test_part_get_scriptlet_none(self, step):
        p = Part("foo", {})
        assert p.spec.get_scriptlet(step) is None


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

        with pytest.raises(errors.PartDependencyCycle) as raised:
            parts.sort_parts([p1, p2, p3])
        assert (
            str(raised.value) == "A circular dependency chain was detected. "
            "Please review the parts definition to remove dependency cycles."
        )


class TestPartHelpers:
    """Test part-related helper functions."""

    def test_part_by_name(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {})
        p3 = Part("baz", {})

        x = parts.part_by_name("bar", [p1, p2, p3])
        assert x == p2

        with pytest.raises(errors.InvalidPartName) as raised:
            parts.part_by_name("invalid", [p1, p2, p3])
        assert (
            str(raised.value) == "A part named 'invalid' is not defined "
            "in the parts list."
        )

    def test_part_list_by_name(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {})
        p3 = Part("baz", {})

        x = parts.part_list_by_name(["bar", "baz"], [p1, p2, p3])
        assert x == [p2, p3]

        x = parts.part_list_by_name(("bar", "baz"), [p1, p2, p3])
        assert x == [p2, p3]

        # If the list is empty or not defined, return all parts
        x = parts.part_list_by_name([], [p1, p2, p3])
        assert x == [p1, p2, p3]

        x = parts.part_list_by_name(None, [p1, p2, p3])
        assert x == [p1, p2, p3]

        with pytest.raises(errors.InvalidPartName) as raised:
            parts.part_list_by_name(["bar", "invalid"], [p1, p2, p3])
        assert (
            str(raised.value) == "A part named 'invalid' is not defined "
            "in the parts list."
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

        with pytest.raises(errors.InvalidPartName) as raised:
            parts.part_dependencies("invalid", part_list=[p1, p2, p3, p4])
        assert (
            str(raised.value) == "A part named 'invalid' is not defined "
            "in the parts list."
        )
