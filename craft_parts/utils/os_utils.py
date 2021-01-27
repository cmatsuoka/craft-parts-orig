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

"""Utilities related to the operating system."""

import os
import pathlib
from typing import List, Union


def get_bin_paths(*, root: Union[str, pathlib.Path], existing_only=True) -> List[str]:
    """List common system executable paths."""

    paths = (os.path.join("usr", "sbin"), os.path.join("usr", "bin"), "sbin", "bin")
    rooted_paths = (os.path.join(root, p) for p in paths)

    if existing_only:
        return [p for p in rooted_paths if os.path.exists(p)]

    return list(rooted_paths)


def get_include_paths(
    *, root: Union[str, pathlib.Path], arch_triplet: str
) -> List[str]:
    """List common include paths."""

    paths = [
        os.path.join(root, "include"),
        os.path.join(root, "usr", "include"),
        os.path.join(root, "include", arch_triplet),
        os.path.join(root, "usr", "include", arch_triplet),
    ]

    return [p for p in paths if os.path.exists(p)]


def get_library_paths(
    *, root: Union[str, pathlib.Path], arch_triplet: str, existing_only=True
) -> List[str]:
    """List common library paths.

    If existing_only is set the paths returned must exist for
    the root that was set.
    """
    paths = [
        os.path.join(root, "lib"),
        os.path.join(root, "usr", "lib"),
        os.path.join(root, "lib", arch_triplet),
        os.path.join(root, "usr", "lib", arch_triplet),
    ]

    if existing_only:
        paths = [p for p in paths if os.path.exists(p)]

    return paths


def get_pkg_config_paths(
    *, root: Union[str, pathlib.Path], arch_triplet: str
) -> List[str]:
    """List common pkg-config paths."""

    paths = [
        os.path.join(root, "lib", "pkgconfig"),
        os.path.join(root, "lib", arch_triplet, "pkgconfig"),
        os.path.join(root, "usr", "lib", "pkgconfig"),
        os.path.join(root, "usr", "lib", arch_triplet, "pkgconfig"),
        os.path.join(root, "usr", "share", "pkgconfig"),
        os.path.join(root, "usr", "local", "lib", "pkgconfig"),
        os.path.join(root, "usr", "local", "lib", arch_triplet, "pkgconfig"),
        os.path.join(root, "usr", "local", "share", "pkgconfig"),
    ]

    return [p for p in paths if os.path.exists(p)]


# FIXME: investigate environment setting
def reset_env() -> None:
    """Reset the environment."""
    # global env
    # env = []


def is_dumb_terminal() -> bool:
    """Return True if on a dumb terminal."""
    is_stdout_tty = os.isatty(1)
    is_term_dumb = os.environ.get("TERM", "") == "dumb"
    return not is_stdout_tty or is_term_dumb
