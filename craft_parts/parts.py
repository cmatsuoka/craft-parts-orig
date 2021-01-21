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

"""Definitions and helpers to handle parts."""

from pathlib import Path
from typing import Any, Dict, List, Set

from craft_parts import errors


class Part:
    """Each of the components used in the project specification.

    During the craft-parts lifecycle each part is processed through
    different steps in order to obtain its final artifacts. The Part
    class holds the part specification data and additional configuration
    information used during step processing.
    """

    def __init__(self, name: str, data: Dict[str, Any], *, work_dir: str = "."):
        self._name = name
        self._data = data
        self._work_dir = Path(work_dir)
        self._part_dir = self._work_dir / "parts" / name

    def __repr__(self):
        return f"Part({self.name!r})"

    @property
    def name(self) -> str:
        """The part name."""
        return self._name

    @property
    def data(self) -> Dict[str, Any]:
        """The part properties."""
        return self._data

    @property
    def part_src_dir(self) -> Path:
        """The subdirectory containing this part's source code."""
        return self._part_dir / "src"

    @property
    def part_build_dir(self) -> Path:
        """The subdirectory containing this part's build tree."""
        return self._part_dir / "build"

    @property
    def part_install_dir(self) -> Path:
        """The subdirectory to install this part's build artifacts."""
        return self._part_dir / "install"

    @property
    def part_state_dir(self) -> Path:
        """The subdirectory containing this part's lifecycle state."""
        return self._part_dir / "state"

    @property
    def part_run_dir(self) -> Path:
        """The subdirectory containing this part's plugin scripts."""
        return self._part_dir / "run"

    @property
    def stage_dir(self) -> Path:
        """The staging area containing the installed file for all parts."""
        return self._work_dir / "stage"

    @property
    def prime_dir(self) -> Path:
        """The primed tree containing the artifacts to deploy."""
        return self._work_dir / "prime"


def part_by_name(name: str, part_list: List[Part]) -> Part:
    """Obtain the part with the given name from the part list."""

    for part in part_list:
        if part.name is name:
            return part

    raise errors.InvalidPartName(name)


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
    """Returns a set of all the parts upon which the named part depends."""

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
