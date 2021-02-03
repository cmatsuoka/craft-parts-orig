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

import contextlib
import logging
import os
import pathlib
import shutil
from typing import Dict, List, Optional, Union

from craft_parts import errors

logger = logging.getLogger(__name__)


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


def get_build_base() -> str:
    """Guess the built base to use."""
    # FIXME: implement get_build_base


def is_snap(*, application_name: Optional[str] = None) -> bool:
    """Verify whether we're running as a snap."""

    snap_name = os.environ.get("SNAP_NAME", "")
    if application_name:
        is_snap = snap_name == application_name
    else:
        is_snap = snap_name is not None

    logger.debug(
        "craft_parts is running as a snap: {!r}, "
        "SNAP_NAME set to {!r}".format(is_snap, snap_name)
    )
    return is_snap


def get_snap_tool_path(command_name: str) -> str:
    """Return the path command found in the snap.

    If snapcraft is not running as a snap, shutil.which() is used
    to resolve the command using PATH.

    :param command_name: the name of the command to resolve a path for.
    :raises MissingTool: if command_name was not found.
    :return: Path to command
    """

    if is_snap():
        snap_path = os.getenv("SNAP")
        if snap_path is None:
            raise RuntimeError("SNAP not defined, but SNAP_NAME is?")

        command_path = _find_command_path_in_root(snap_path, command_name)
    else:
        command_path = shutil.which(command_name)

    if command_path is None:
        raise errors.MissingTool(command_name=command_name)

    return command_path


def _find_command_path_in_root(root, command_name: str) -> Optional[str]:
    for bin_directory in (
        os.path.join("usr", "local", "sbin"),
        os.path.join("usr", "local", "bin"),
        os.path.join("usr", "sbin"),
        os.path.join("usr", "bin"),
        os.path.join("sbin"),
        os.path.join("bin"),
    ):
        path = os.path.join(root, bin_directory, command_name)
        if os.path.exists(path):
            return path

    return None


_ID_TO_UBUNTU_CODENAME = {
    "17.10": "artful",
    "17.04": "zesty",
    "16.04": "xenial",
    "14.04": "trusty",
}


class OsRelease:
    """A class to intelligently determine the OS on which we're running"""

    def __init__(self, *, os_release_file: str = "/etc/os-release") -> None:
        """Create a new OsRelease instance.

        :param str os_release_file: Path to os-release file to be parsed.
        """

        self._os_release = {}  # type: Dict[str, str]
        with contextlib.suppress(FileNotFoundError):
            with open(os_release_file) as f:
                for line in f:
                    entry = line.rstrip().split("=")
                    if len(entry) == 2:
                        self._os_release[entry[0]] = entry[1].strip('"')

    def id(self) -> str:
        """Return the OS ID

        :raises OsReleaseIdError: If no ID can be determined.
        """
        with contextlib.suppress(KeyError):
            return self._os_release["ID"]

        raise errors.OsReleaseError("ID")

    def name(self) -> str:
        """Return the OS name

        :raises OsReleaseNameError: If no name can be determined.
        """
        with contextlib.suppress(KeyError):
            return self._os_release["NAME"]

        raise errors.OsReleaseError("name")

    def version_id(self) -> str:
        """Return the OS version ID

        :raises OsReleaseVersionIdError: If no version ID can be determined.
        """
        with contextlib.suppress(KeyError):
            return self._os_release["VERSION_ID"]

        raise errors.OsReleaseError("version ID")

    def version_codename(self) -> str:
        """Return the OS version codename

        This first tries to use the VERSION_CODENAME. If that's missing, it
        tries to use the VERSION_ID to figure out the codename on its own.

        :raises OsReleaseCodenameError: If no version codename can be
                                        determined.
        """

        # pyright doesn't like "with contextlib.suppress(KeyError)"

        release = self._os_release.get("VERSION_CODENAME")
        if release:
            return release

        ver_id = self._os_release.get("VERSION_ID")
        if ver_id and release in _ID_TO_UBUNTU_CODENAME:
            return _ID_TO_UBUNTU_CODENAME[ver_id]

        raise errors.OsReleaseError("version codename")
