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

import pytest

from craft_parts import errors
from craft_parts.executor.collisions import check_for_stage_collisions
from craft_parts.parts import Part


@pytest.fixture
def part1(tmpdir) -> Part:
    part = Part("part1", {}, work_dir=tmpdir)
    p = part.part_install_dir
    (p / "a").mkdir(parents=True)
    (p / "a" / "1").write_text("")
    (p / "file.pc").write_text("prefix={}\nName: File".format(part.part_install_dir))
    return part


@pytest.fixture
def part2(tmpdir) -> Part:
    part = Part("part2", {}, work_dir=tmpdir)
    p = part.part_install_dir
    (p / "a").mkdir(parents=True)
    (p / "1").write_text("1")
    (p / "2").write_text("")
    (p / "a" / "2").write_text("a/2")
    (p / "a" / "file.pc").write_text(
        "prefix={}\nName: File".format(part.part_install_dir)
    )
    return part


@pytest.fixture
def part3(tmpdir) -> Part:
    part = Part("part3", {}, work_dir=tmpdir)
    p = part.part_install_dir
    (p / "a").mkdir(parents=True)
    (p / "b").mkdir()
    (p / "1").write_text("2")
    # (p / "2").write_text("1")
    (p / "a" / "2").write_text("")
    return part


@pytest.fixture
def part4(tmpdir) -> Part:
    part = Part("part4", {}, work_dir=tmpdir)
    p = part.part_install_dir
    (p / "a").mkdir(parents=True)
    (p / "a" / "2").write_text("")
    (p / "file.pc").write_text(
        "prefix={}\nName: ConflictFile".format(part.part_install_dir)
    )
    return part


@pytest.fixture
def part5(tmpdir) -> Part:
    # Create a new part with a symlink that collides with part1's
    # non-symlink.
    part = Part("part5", {}, work_dir=tmpdir)
    p = part.part_install_dir
    p.mkdir(parents=True)
    (p / "a").symlink_to("foo")

    return part


@pytest.fixture
def part6(tmpdir) -> Part:
    # Create a new part with a symlink that points to a different place
    # than part5's symlink.
    part = Part("part6", {}, work_dir=tmpdir)
    p = part.part_install_dir
    p.mkdir(parents=True)
    (p / "a").symlink_to("bar")

    return part


class TestCollisions:
    def test_no_collisions(self, part1, part2):
        """No exception is expected as there are no collisions."""
        check_for_stage_collisions([part1, part2])

    def test_collisions_between_two_parts(self, part1, part2, part3):
        with pytest.raises(errors.PartConflictError) as raised:
            check_for_stage_collisions([part1, part2, part3])

        assert raised.value.other_part_name == "part2"  # type: ignore
        assert raised.value.part_name == "part3"  # type: ignore
        assert raised.value.file_paths == "    1\n    a/2"  # type: ignore

    def test_collisions_checks_symlinks(self, part5, part6):
        with pytest.raises(errors.PartConflictError) as raised:
            check_for_stage_collisions([part5, part6])

        assert str(raised.value).__contains__(
            "Parts 'part5' and 'part6' have the following files, but with "
            "different contents:\n    a"
        )

    def test_collisions_not_both_symlinks(self, part1, part5):
        with pytest.raises(errors.PartConflictError) as raised:
            check_for_stage_collisions([part1, part5])

        assert str(raised.value).__contains__(
            "Parts 'part1' and 'part5' have the following files, but with "
            "different contents:\n    a"
        )

    def test_collisions_between_two_parts_pc_files(self, part1, part4):
        with pytest.raises(errors.PartConflictError) as raised:
            check_for_stage_collisions([part1, part4])

        assert raised.value.other_part_name == "part1"  # type: ignore
        assert raised.value.part_name == "part4"  # type: ignore
        assert raised.value.file_paths == "    file.pc"  # type: ignore

    def test_collision_with_part_not_built(self, tmpdir):
        part_built = Part("part_built", {"stage": ["collision"]}, work_dir=tmpdir)

        # a part built has the stage file in the installdir.
        part_built.part_install_dir.mkdir(parents=True)
        (part_built.part_install_dir / "collision").write_text("")

        part_not_built = Part(
            "part_not_built", {"stage": ["collision"]}, work_dir=tmpdir
        )

        # a part not built doesn't have the stage file in the installdir.
        check_for_stage_collisions([part_built, part_not_built])
