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

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Set

from craft_parts import errors
from craft_parts.dirs import ProjectDirs
from craft_parts.steps import Step

if TYPE_CHECKING:
    from craft_parts.plugins.options import PluginProperties

# pylint: disable=too-many-public-methods
# We use many property getters to prevent unintentional value overwrites


@dataclass(frozen=True)
class _PartSpecs:
    plugin: str
    source: Optional[str]
    source_checksum: str
    source_branch: str
    source_commit: str
    source_depth: int
    source_subdir: str
    source_tag: str
    source_type: str
    disable_parallel: bool
    after: List[str]
    stage_snaps: List[str]
    stage_packages: List[str]
    build_snaps: List[str]
    build_packages: List[str]
    build_environment: List[Dict[str, str]]
    build_attributes: List[str]
    organize_fileset: Dict[str, str]
    stage_fileset: List[str]
    prime_fileset: List[str]
    override_pull: Optional[str]
    override_build: Optional[str]
    override_stage: Optional[str]
    override_prime: Optional[str]

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "_PartSpecs":

        # TODO: validate stuff

        return cls(
            plugin=data.pop("plugin", None),
            source=data.pop("source", None),
            source_checksum=data.pop("source-checksum", ""),
            source_branch=data.pop("source-branch", ""),
            source_commit=data.pop("source-commit", ""),
            source_depth=data.pop("source-depth", ""),
            source_subdir=data.pop("source-subdir", ""),
            source_tag=data.pop("source-tag", ""),
            source_type=data.pop("source-type", ""),
            disable_parallel=data.pop("disable_parallel", False),
            after=data.pop("after", []),
            stage_snaps=data.pop("stage-snaps", []),
            stage_packages=data.pop("stage-packages", []),
            build_snaps=data.pop("build-snaps", []),
            build_packages=data.pop("build-packages", []),
            build_environment=data.pop("build-environment", []),
            build_attributes=data.pop("build-attributes", []),
            organize_fileset=data.pop("organize", {}),
            stage_fileset=data.pop("stage", ["*"]),
            prime_fileset=data.pop("prime", ["*"]),
            override_pull=data.pop("override-pull", None),
            override_build=data.pop("override-build", None),
            override_stage=data.pop("override-stage", None),
            override_prime=data.pop("override-prime", None),
        )

    def marshal(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "source": self.source,
            "source-checksum": self.source_checksum,
            "source-branch": self.source_branch,
            "source-commit": self.source_commit,
            "source-depth": self.source_depth,
            "source-subdir": self.source_subdir,
            "source-tag": self.source_tag,
            "source-type": self.source_type,
            "disable-parallel": self.disable_parallel,
            "after": self.after,
            "stage-snaps": self.stage_snaps,
            "stage-packages": self.stage_packages,
            "build-snaps": self.build_snaps,
            "build-packages": self.build_packages,
            "build-environment": self.build_environment,
            "build-attributes": self.build_attributes,
            "organize": self.organize_fileset,
            "stage": self.stage_fileset,
            "prime": self.prime_fileset,
            "override-pull": self.override_pull,
            "override-build": self.override_build,
            "override-stage": self.override_stage,
            "override-prime": self.override_prime,
        }

    def get_scriptlet(self, step: Step) -> Optional[str]:
        """Return the scriptlet contents, if any, for the given step.

        :param step: the step corresponding to the scriptlet to be retrieved.
        """
        return {
            Step.PULL: self.override_pull,
            Step.BUILD: self.override_build,
            Step.STAGE: self.override_stage,
            Step.PRIME: self.override_prime,
        }[step]


class Part:
    """Each of the components used in the project specification.

    During the craft-parts lifecycle each part is processed through
    different steps in order to obtain its final artifacts. The Part
    class holds the part specification data and additional configuration
    information used during step processing.

    :param name: The part name.
    :param data: A dictionary containing the part properties.
    :param project_dirs: The project work directories.
    """

    def __init__(
        self,
        name: str,
        data: Dict[str, Any],
        *,
        project_dirs: ProjectDirs = None,
        plugin_properties: "Optional[PluginProperties]" = None,
    ):

        if not project_dirs:
            project_dirs = ProjectDirs()

        plugin_name: str = data.get("plugin", "")
        # TODO: handle error

        self.name = name
        self.plugin = plugin_name
        self.plugin_options = plugin_properties
        self._dirs = project_dirs
        self._part_dir = project_dirs.parts_dir / name
        self.spec = _PartSpecs.unmarshal(data)

    def __repr__(self):
        return f"Part({self.name!r})"

    @property
    def parts_dir(self) -> Path:
        """Return the directory containing work files for each part."""
        return self._dirs.parts_dir

    @property
    def part_src_dir(self) -> Path:
        """Return the subdirectory containing the part source code."""
        return self._part_dir / "src"

    @property
    def part_src_work_dir(self) -> Path:
        """Return the subdirectory in source containing the source subtree (if any)."""
        return self.part_src_dir / self.spec.source_subdir

    @property
    def part_build_dir(self) -> Path:
        """Return the subdirectory containing the part build tree."""
        return self._part_dir / "build"

    @property
    def part_build_work_dir(self) -> Path:
        """Return the subdirectory in build containing the source subtree (if any)."""
        return self.part_build_dir / self.spec.source_subdir

    @property
    def part_install_dir(self) -> Path:
        """Return the subdirectory to install the part build artifacts."""
        return self._part_dir / "install"

    @property
    def part_state_dir(self) -> Path:
        """Return the subdirectory containing the part lifecycle state."""
        return self._part_dir / "state"

    @property
    def part_packages_dir(self) -> Path:
        """Return the subdirectory containing the part stage packages directory."""
        return self._part_dir / "stage_packages"

    @property
    def part_snaps_dir(self) -> Path:
        """Return the subdirectory containing the part snap packages directory."""
        return self._part_dir / "stage_snaps"

    @property
    def part_run_dir(self) -> Path:
        """Return the subdirectory containing the part plugin scripts."""
        return self._part_dir / "run"

    @property
    def stage_dir(self) -> Path:
        """Return the staging area containing the installed files from all parts."""
        return self._dirs.stage_dir

    @property
    def prime_dir(self) -> Path:
        """Return the primed tree containing the artifacts to deploy."""
        return self._dirs.prime_dir

    @property
    def dependencies(self) -> List[str]:
        return self.spec.after


def part_by_name(name: str, part_list: List[Part]) -> Part:
    """Obtain the part with the given name from the part list.

    :param name: The name of the part to return.
    :param part_list: The list of all known parts.

    :returns: The part with the given name.
    """
    for part in part_list:
        if part.name == name:
            return part

    raise errors.InvalidPartName(name)


def part_list_by_name(
    names: Optional[Sequence[str]], part_list: List[Part]
) -> List[Part]:
    """Return a list of parts from part_list that are named in names.

    :param names: The list of part names. If the list is empty or not
        defined, return all parts from part_list.
    :param part_list: The list of all known parts.

    :returns: The list of parts corresponding to the given names.
    """
    if names:
        # check if all part names are valid
        valid_names = [p.name for p in part_list]
        for name in names:
            if name not in valid_names:
                raise errors.InvalidPartName(name)

        selected_parts = [p for p in part_list if p.name in names]
    else:
        selected_parts = part_list

    return selected_parts


def sort_parts(part_list: List[Part]) -> List[Part]:
    """Perform an inneficient but easy to follow sorting of parts.

    :param part_list: The list of parts to sort.

    :returns: The sorted list of parts.
    """
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
    name: str, *, part_list: List[Part], recursive: bool = False
) -> Set[Part]:
    """Return a set of all the parts upon which the named part depends.

    :param name: The name of the dependent part.

    :returns: The set of parts the given part depends on.
    """
    part = next((p for p in part_list if p.name == name), None)
    if not part:
        raise errors.InvalidPartName(name)

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
