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

"""Definitions and helpers to handle filesets."""

import os
from glob import iglob
from typing import Dict, List, Set, Tuple, Union

from craft_parts import errors
from craft_parts.utils import file_utils


class Fileset:
    """Helper class to process string lists."""

    def __init__(self, entries: Union[List[str], Dict[str, str]], *, name: str = ""):
        self._name = name
        if isinstance(entries, dict):
            self._dict = entries
            self._list = list(entries.keys())
        else:
            self._list = entries

    def __repr__(self):
        return f"Fileset({self._list})"

    @property
    def name(self) -> str:
        """Return the fileset name."""
        return self._name

    @property
    def entries(self) -> List[str]:
        """Return the list of entries in this fileset."""
        return self._list.copy()

    @property
    def includes(self) -> List[str]:
        """Return the list of files to be included."""
        return [x for x in self._list if x[0] != "-"]

    @property
    def excludes(self) -> List[str]:
        """Return the list of files to be excluded."""
        return [x[1:] for x in self._list if x[0] == "-"]

    def get(self, key: str) -> str:
        return self._dict[key]

    def remove(self, item: str) -> None:
        """Remove this entry from the list of files."""
        self._list.remove(item)

    def combine(self, other: "Fileset") -> None:
        """Combine the entries in this fileset with entries from another fileset."""

        my_excludes = set(self.excludes)
        other_includes = set(other.includes)

        contradicting_set = set.intersection(my_excludes, other_includes)

        if contradicting_set:
            pass
            # raise errors.FilesetConflict(list=contradicting_set)

        to_combine = False
        # combine if the other fileset has a wildcard
        # XXX: should this only be a single wildcard and possibly excludes?
        if "*" in other.entries:
            to_combine = True
            other.remove("*")

        # combine if the other fileset is only excludes
        if {x[0] for x in other.entries} == set("-"):
            to_combine = True

        if to_combine:
            self._list = list(set(self._list + other.entries))
        else:
            self._list = other.entries


def migratable_filesets(fileset: Fileset, srcdir: str) -> Tuple[Set[str], Set[str]]:
    """Return the list of files and directories that can be migrated."""

    includes, excludes = _get_file_list(fileset)

    include_files = _generate_include_set(srcdir, includes)
    exclude_files, exclude_dirs = _generate_exclude_set(srcdir, excludes)

    files = include_files - exclude_files
    for exclude_dir in exclude_dirs:
        files = {x for x in files if not x.startswith(exclude_dir + "/")}

    # Separate dirs from files.
    dirs = {
        x
        for x in files
        if os.path.isdir(os.path.join(srcdir, x))
        and not os.path.islink(os.path.join(srcdir, x))
    }

    # Remove dirs from files.
    files = files - dirs

    # Include (resolved) parent directories for each selected file.
    for filename in files:
        filename = file_utils.get_resolved_relative_path(filename, srcdir)
        dirname = os.path.dirname(filename)
        while dirname:
            dirs.add(dirname)
            dirname = os.path.dirname(dirname)

    # Resolve parent paths for dirs and files.
    resolved_dirs = set()
    for dirname in dirs:
        dirname = file_utils.get_resolved_relative_path(dirname, srcdir)
        resolved_dirs.add(dirname)

    resolved_files = set()
    for filename in files:
        filename = file_utils.get_resolved_relative_path(filename, srcdir)
        resolved_files.add(filename)

    return resolved_files, resolved_dirs


def _get_file_list(fileset: Fileset) -> Tuple[List[str], List[str]]:
    includes: List[str] = []
    excludes: List[str] = []

    for item in fileset.entries:
        if item.startswith("-"):
            excludes.append(item[1:])
        elif item.startswith("\\"):
            includes.append(item[1:])
        else:
            includes.append(item)

    # paths must be relative
    for entry in includes + excludes:
        if os.path.isabs(entry):
            raise errors.FilesetError(fileset.name, f"path {entry!r} must be relative.")

    includes = includes or ["*"]

    return includes, excludes


def _generate_include_set(directory: str, includes: List[str]) -> Set[str]:
    include_files = set()

    for include in includes:
        if "*" in include:
            pattern = os.path.join(directory, include)
            matches = iglob(pattern, recursive=True)
            include_files |= set(matches)
        else:
            include_files |= set([os.path.join(directory, include)])

    include_dirs = [x for x in include_files if os.path.isdir(x)]
    include_files = {os.path.relpath(x, directory) for x in include_files}

    # Expand includeFiles, so that an exclude like '*/*.so' will still match
    # files from an include like 'lib'
    for include_dir in include_dirs:
        for root, dirs, files in os.walk(include_dir):
            include_files |= {
                os.path.relpath(os.path.join(root, d), directory) for d in dirs
            }
            include_files |= {
                os.path.relpath(os.path.join(root, f), directory) for f in files
            }

    return include_files


def _generate_exclude_set(
    directory: str, excludes: List[str]
) -> Tuple[Set[str], Set[str]]:
    exclude_files = set()

    for exclude in excludes:
        pattern = os.path.join(directory, exclude)
        matches = iglob(pattern, recursive=True)
        exclude_files |= set(matches)

    exclude_dirs = {
        os.path.relpath(x, directory) for x in exclude_files if os.path.isdir(x)
    }
    exclude_files = {os.path.relpath(x, directory) for x in exclude_files}

    return exclude_files, exclude_dirs
