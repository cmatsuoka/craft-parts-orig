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

import os
from typing import Any, Dict, List, Set

from craft_parts import errors


class Part:
    def __init__(self, name: str, data: Dict[str, Any], *, work_dir: str = "."):
        self.name = name
        self.data = data
        parts_dir = os.path.join(work_dir, "parts")
        self.part_dir = os.path.join(parts_dir, name)
        self.part_src_dir = os.path.join(self.part_dir, "src")
        self.part_build_dir = os.path.join(self.part_dir, "build")
        self.part_install_dir = os.path.join(self.part_dir, "install")
        self.part_state_dir = os.path.join(self.part_dir, "state")

    def __repr__(self):
        return f"Part({self.name})"


def part_by_name(name: str, part_list: List[Part]) -> Part:
    """Obtain the part with the given name from the part list."""

    for p in part_list:
        if p.name is name:
            return p

    raise errors.InternalError(f"unknown part {name!r}")


def sort_parts(part_list: List[Part]) -> List[Part]:
    """Performs an inneficient but easy to follow sorting of parts."""
    sorted_parts = []  # type: List[Part]

    # We want to process parts in a consistent order between runs. The
    # simplest way to do this is to sort them by name.
    all_parts = sorted(part_list, key=lambda part: part.name, reverse=True)

    while all_parts:
        top_part = None

        for part in all_parts:
            mentioned = False
            for other in all_parts:
                if part.name in other.data.get("after", []):
                    mentioned = True
                    break
            if not mentioned:
                top_part = part
                break
        if not top_part:
            raise errors.PartDependencyCycle()

        sorted_parts = [top_part] + sorted_parts
        all_parts.remove(top_part)

    return sorted_parts


def part_dependencies(
    part_name: str, *, part_list: List[Part], recursive: bool = False
) -> Set[Part]:
    """Returns a set of all the parts upon which part_name depends."""

    part = next((p for p in part_list if p.name == part_name), None)
    if not part:
        raise errors.InvalidPartName(part_name)

    dependency_names = set(part.data.get("after", []))
    dependencies = {p for p in part_list if p.name in dependency_names}

    if recursive:
        # No need to worry about infinite recursion due to circular
        # dependencies since the YAML validation won't allow it.
        for dependency_name in dependency_names:
            dependencies |= part_dependencies(
                dependency_name, part_list=part_list, recursive=recursive
            )

    return dependencies
