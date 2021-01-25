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

"""Definitions and helpers for source type handling."""

import subprocess

from craft_parts import errors


class SourceHandlerBase:
    """The base class for source type handlers."""

    # pylint: disable=too-many-instance-attributes,too-many-arguments
    def __init__(
        self,
        source,
        source_dir,
        source_tag=None,
        source_commit=None,
        source_branch=None,
        source_depth=None,
        source_checksum=None,
        command=None,
    ):
        self.source = source
        self.source_dir = source_dir
        self.source_tag = source_tag
        self.source_commit = source_commit
        self.source_branch = source_branch
        self.source_depth = source_depth
        self.source_checksum = source_checksum
        self.source_details = None

        self.command = command
        self._checked = False

    def check(self, target: str):
        """Check if pulled sources have changed since target was created.

        :param str target: Path to target file.
        """
        self._checked = True
        return self._check(target)

    def update(self):
        """Update pulled source.

        :raises RuntimeError: If this function is called before `check()`.
        """
        if not self._checked:
            # This is programmer error
            raise RuntimeError("source must be checked before it's updated")
        self._update()

    def _check(self, target: str):
        """Check if pulled sources have changed since target was created.

        :param str target: Path to target file.
        """
        raise errors.SourceUpdateUnsupported(self)

    def _update(self):
        """Update pulled source."""
        raise errors.SourceUpdateUnsupported(self)

    # pylint: disable=no-self-use
    def _run(self, command, **kwargs):
        try:
            subprocess.check_call(command, **kwargs)
        except subprocess.CalledProcessError as err:
            raise errors.PullError(command, err.returncode)

    def _run_output(self, command, **kwargs) -> str:
        try:
            return (
                subprocess.check_output(command, **kwargs)
                # .decode(sys.getfilesystemencoding())
                .strip()
            )
        except subprocess.CalledProcessError as err:
            raise errors.PullError(command, err.returncode)
