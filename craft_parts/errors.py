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

from abc import ABC, abstractmethod
from typing import Optional


class _Error(Exception, ABC):
    """Base class for craft_parts exceptions."""

    @abstractmethod
    def get_brief(self) -> str:
        """Concise, single-line description of the error."""

    @abstractmethod
    def get_resolution(self) -> str:
        """Concise suggestion for user to resolve error."""

    def get_details(self) -> Optional[str]:
        """Detailed technical information, if required for user to debug issue."""
        return None

    def get_docs_url(self) -> Optional[str]:
        """Link to documentation, if applicable."""
        return None

    def get_reportable(self) -> bool:
        """Whether this error is reportable (an exception trace should be shown)."""
        return False

    def __str__(self) -> str:
        return self.get_brief()


class _ReportableError(_Error, ABC):
    """Helper class for reportable exceptions."""

    def get_reportable(self) -> bool:
        return True


class InternalError(_ReportableError):
    def __init__(self, msg: str):
        super().__init__()
        self._msg = msg

    def get_brief(self) -> str:
        return f"Internal error: {self._msg}"

    def get_resolution(self) -> str:
        return "Please contact the developers to report this bug."


class InvalidArchitecture(_Error):
    def __init__(self, arch_name: str):
        self._arch_name = arch_name

    def get_brief(self) -> str:
        return f"Architecture {self._arch_name!r} is invalid."

    def get_resolution(self) -> str:
        return "Make sure the requested architecture is supported."


class PartDependencyCycle(_Error):
    def get_brief(self) -> str:
        return "A circular dependency chain was detected."

    def get_resolution(self) -> str:
        return "Review the parts definition to remove dependency cycles."


class InvalidPartName(_Error):
    def __init__(self, part_name: str):
        self._part_name = part_name

    def get_brief(self) -> str:
        return f'A part named "{self._part_name}" is not defined in the parts list.'

    def get_resolution(self) -> str:
        return "Check for typos in the part name or in the parts definition."
