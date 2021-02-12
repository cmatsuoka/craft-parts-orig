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

"""Helpers to detect conflicting staging files from multiple parts."""

import filecmp
import os
from pathlib import Path
from typing import Any, Dict, List

from craft_parts import errors, filesets
from craft_parts.filesets import Fileset
from craft_parts.parts import Part


def check_for_stage_collisions(part_list: List[Part]) -> None:
    """Verify whether parts have conflicting files to stage.

    :param part_list: The list of parts to be tested.
    :raises PartConflictError: If conflicts are found.
    """

    all_parts_files: Dict[str, Dict[str, Any]] = {}
    for part in part_list:
        # Gather our own files up
        stage_fileset = Fileset(part.stage_fileset, name="stage")
        srcdir = str(part.part_install_dir)
        part_files, part_directories = filesets.migratable_filesets(
            stage_fileset, srcdir
        )
        part_contents = part_files | part_directories

        # Scan previous parts for collisions
        for other_part_name in all_parts_files:
            # our files that are also in a different part
            common = part_contents & all_parts_files[other_part_name]["files"]

            conflict_files = []
            for f in common:
                this = part.part_install_dir / f
                other = Path(all_parts_files[other_part_name]["installdir"], f)

                if _paths_collide(this, other):
                    conflict_files.append(f)

            if conflict_files:
                raise errors.PartConflictError(
                    other_part_name=other_part_name,
                    part_name=part.name,
                    conflict_files=conflict_files,
                )

        # And add our files to the list
        all_parts_files[part.name] = {
            "files": part_contents,
            "installdir": part.part_install_dir,
        }


def _paths_collide(path1: Path, path2: Path) -> bool:
    # Both paths must exist to have a collision
    if not (os.path.lexists(path1) and os.path.lexists(path2)):
        return False

    # Paths collide if they're both symlinks, but pointing to different places
    # note: Path.readlink() introduced in Python 3.9
    if path1.is_symlink() and path2.is_symlink():
        return os.readlink(str(path1)) != os.readlink(str(path2))

    # Paths collide if one is a symlink, but not the other
    if path1.is_symlink() or path2.is_symlink():
        return True

    # Paths collide if one is a directory, but not the other
    if path1.is_dir() != path2.is_dir():
        return True

    # Paths collide if neither path is a directory, and the files have
    # different contents
    if not (path1.is_dir() and path2.is_dir()) and _file_collides(path1, path2):
        return True

    # Otherwise, paths do not conflict
    return False


def _file_collides(file_this: Path, file_other: Path) -> bool:
    if not file_this.name.endswith(".pc"):
        return not filecmp.cmp(file_this, file_other, shallow=False)

    # pkgconfig files need special handling
    pc_file_1 = file_this.open()
    pc_file_2 = file_other.open()

    try:
        for lines in zip(pc_file_1, pc_file_2):
            for line in zip(lines[0].split("\n"), lines[1].split("\n")):
                if line[0].startswith("prefix="):
                    continue
                if line[0] != line[1]:
                    return True
    except Exception as e:
        raise e from e
    finally:
        pc_file_1.close()
        pc_file_2.close()
    return False