# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2021, 2019 Canonical Ltd
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

"""Exceptions raised by the sources handling subsystem."""

import shlex
from abc import ABC
from typing import List

from craft_parts import errors
from craft_parts.utils import formatting_utils

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

# Enforce our constructor parameters
# pylint: disable=useless-super-delegation


class SourceError(errors.CraftPartsError, ABC):
    pass


class VCSError(SourceError):
    fmt = "{message}"


class SourceNotFound(SourceError):

    fmt = "Failed to pull source: {source!r} not found."

    def __init__(self, source: str):
        super().__init__(source=source)


class InvalidSourceType(SourceError):

    fmt = "Failed to pull source: unable to determine source type of {source!r}."

    def __init__(self, source: str):
        super().__init__(source=source)


class InvalidSourceOption(SourceError):

    fmt = (
        "Failed to pull source: {option!r} cannot be used with a {source_type} source."
    )

    def __init__(self, source_type: str, option: str) -> None:
        super().__init__(source_type=source_type, option=option)


class IncompatibleSourceOptions(SourceError):

    fmt = (
        "Failed to pull source: "
        "cannot specify both {humanized_options} for a {source_type} source.\n"
    )

    def __init__(self, source_type: str, options: List[str]) -> None:
        super().__init__(
            source_type=source_type,
            humanized_options=formatting_utils.humanize_list(options, "and"),
        )


class ChecksumMismatch(SourceError):
    """A checksum doesn't match the expected value."""

    fmt = "Expected the digest to be {expected}, but it was {actual}."

    def __init__(self, expected: str, actual: str):
        super().__init__(expected=expected, actual=actual)


class InvalidDebPackage(SourceError):

    fmt = (
        "The {deb_file} used does not contain valid data. "
        "Ensure a proper deb file is passed for .deb files "
        "as sources."
    )


class InvalidSnapPackage(SourceError):

    fmt = (
        "The snap file does not contain valid data. "
        "Ensure the source lists a proper snap file"
    )


class SourceUpdateUnsupported(SourceError):

    fmt = "Failed to update source: {source!s} sources don't support updating."

    def __init__(self, source):
        super().__init__(source=source)


class PullError(SourceError):

    fmt = "Failed to pull source: command {command!r} exited with code {exit_code}."

    def __init__(self, command, exit_code):
        if isinstance(command, list):
            string_command = " ".join(shlex.quote(i) for i in command)
        else:
            string_command = command
        super().__init__(command=string_command, exit_code=exit_code)


class NetworkRequestError(SourceError):

    fmt = "Network request error: {message}"


class GitCommandError(SourceError):

    fmt = "Git command {command!r} failed with code {exit_code}: {output}"

    def __init__(self, *, command: List[str], exit_code: int, output: str) -> None:
        cmd = " ".join(shlex.quote(i) for i in command)
        super().__init__(command=cmd, exit_code=exit_code, output=output)
