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

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from craft_parts import errors
from craft_parts.dirs import ProjectDirs
from craft_parts.steps import Step

# pylint: disable=too-many-public-methods
# We use many property getters to prevent unintentional value overwrites


class Part:
    """Each of the components used in the project specification.

    During the craft-parts lifecycle each part is processed through
    different steps in order to obtain its final artifacts. The Part
    class holds the part specification data and additional configuration
    information used during step processing.
    """

    def __init__(
        self,
        name: str,
        data: Dict[str, Any],
        *,
        project_dirs: ProjectDirs = None,
    ):
        if not project_dirs:
            project_dirs = ProjectDirs()

        self._name = name
        self._data = data
        self._dirs = project_dirs
        self._part_dir = project_dirs.parts_dir / name

    def __repr__(self):
        return f"Part({self.name!r})"

    @property
    def name(self) -> str:
        """The part name."""
        return self._name

    @property
    def properties(self) -> Dict[str, Any]:
        """The part properties."""
        return self._data.copy()

    @property
    def parts_dir(self) -> Path:
        """The directory containing work files for each part."""
        return self._dirs.parts_dir

    @property
    def part_src_dir(self) -> Path:
        """The subdirectory containing this part's source code."""
        return self._part_dir / "src"

    @property
    def part_src_work_dir(self) -> Path:
        """The subdirectory in source containing the source subtree (if any)."""
        source_subdir = self._data.get("source-subdir", "")
        return self.part_src_dir / source_subdir

    @property
    def part_build_dir(self) -> Path:
        """The subdirectory containing this part's build tree."""
        return self._part_dir / "build"

    @property
    def part_build_work_dir(self) -> Path:
        """The subdirectory in build containing the source subtree (if any)."""
        source_subdir = self._data.get("source-subdir", "")
        return self.part_build_dir / source_subdir

    @property
    def part_install_dir(self) -> Path:
        """The subdirectory to install this part's build artifacts."""
        return self._part_dir / "install"

    @property
    def part_state_dir(self) -> Path:
        """The subdirectory containing this part's lifecycle state."""
        return self._part_dir / "state"

    @property
    def part_packages_dir(self) -> Path:
        """The subdirectory containing this part's stage packages directory."""
        return self._part_dir / "stage_packages"

    @property
    def part_snaps_dir(self) -> Path:
        """The subdirectory containing this part's snap packages directory."""
        return self._part_dir / "stage_snaps"

    @property
    def part_run_dir(self) -> Path:
        """The subdirectory containing this part's plugin scripts."""
        return self._part_dir / "run"

    @property
    def stage_dir(self) -> Path:
        """The staging area containing the installed files from all parts."""
        return self._dirs.stage_dir

    @property
    def prime_dir(self) -> Path:
        """The primed tree containing the artifacts to deploy."""
        return self._dirs.prime_dir

    @property
    def source(self) -> Optional[str]:
        """This part's source property, if any."""
        source = self._data.get("source")
        if source:
            return str(source)

        return None

    @property
    def stage_fileset(self) -> List[str]:
        """The list of files to stage."""
        return self._data.get("stage", ["*"]).copy()

    @property
    def prime_fileset(self) -> List[str]:
        """The list of files to prime."""
        return self._data.get("prime", ["*"]).copy()

    @property
    def organize_fileset(self) -> Dict[str, str]:
        """The list of files to organize."""
        return self._data.get("organize", {}).copy()

    @property
    def dependencies(self) -> List[str]:
        """The list of parts this parts depends on."""
        return self._data.get("after", []).copy()

    @property
    def plugin(self) -> Optional[str]:
        """The name of this part's plugin."""
        return self._data.get("plugin")

    @property
    def build_environment(self) -> List[Dict[str, str]]:
        """The part's build environment."""
        return copy.deepcopy(self._data.get("build-environment", {}))

    @property
    def stage_packages(self) -> Optional[List[str]]:
        """The list of stage packages for this part."""
        packages = self._data.get("stage-packages")
        if packages:
            return packages.copy()
        return None

    @property
    def stage_snaps(self) -> Optional[List[str]]:
        """The list of stage snaps for this part."""
        snaps = self._data.get("stage-snaps")
        if snaps:
            return snaps.copy()
        return None

    @property
    def build_packages(self) -> Optional[List[str]]:
        """The list of build packages for this part."""
        packages = self._data.get("build-packages")
        if packages:
            return packages.copy()
        return None

    @property
    def build_snaps(self) -> Optional[List[str]]:
        """The list of build snaps for this part."""
        snaps = self._data.get("build-snaps")
        if snaps:
            return snaps.copy()
        return None

    def get_scriptlet(self, step: Step) -> Optional[str]:
        """Return the scriptlet contents, if any, for the given step.

        :param step: the step corresponding to the scriptlet to be retrieved.
        """

        scr = {
            Step.PULL: "override-pull",
            Step.BUILD: "override-build",
            Step.STAGE: "override-stage",
            Step.PRIME: "override-prime",
        }
        return self._data.get(scr[step])


def part_by_name(name: str, part_list: List[Part]) -> Part:
    """Obtain the part with the given name from the part list.

    :param name: The name of the part to return.
    :param part_list: The list of all known parts.
    """

    for part in part_list:
        if part.name == name:
            return part

    raise errors.InvalidPartName(name)


def part_list_by_name(
    part_names: Optional[List[str]], part_list: List[Part]
) -> List[Part]:
    """Return a list of parts from part_list that are named in part_names.

    :param part_names: The list of part names. If the list is empty or not
        defined, return all parts from part_list.
    :param part_list: The list of all known parts.
    """

    if part_names:
        # check if all part names are valid
        valid_part_names = [p.name for p in part_list]
        for name in part_names:
            if name not in valid_part_names:
                raise errors.InvalidPartName(name)

        selected_parts = [p for p in part_list if p.name in part_names]
    else:
        selected_parts = part_list

    return selected_parts


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
                if part.name in other.dependencies:
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

    dependency_names = set(part.dependencies)
    dependencies = {p for p in part_list if p.name in dependency_names}

    if recursive:
        # No need to worry about infinite recursion due to circular
        # dependencies since the YAML validation won't allow it.
        for dependency_name in dependency_names:
            dependencies |= part_dependencies(
                dependency_name, part_list=part_list, recursive=recursive
            )

    return dependencies
