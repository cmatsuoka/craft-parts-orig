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

"""The exceptions that can be raised when using craft_parts."""

import shlex
from abc import ABC, abstractmethod
from typing import List, Optional

import jsonschema  # type: ignore

from craft_parts.utils import schema_helpers


# pylint: disable=no-self-use
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


# pylint: enable=no-self-use


class InternalError(_ReportableError):
    """Internal error."""

    def __init__(self, msg: str):
        super().__init__()
        self._msg = msg

    def get_brief(self) -> str:
        return f"Internal error: {self._msg}"

    def get_resolution(self) -> str:
        return "Please contact the developers to report this bug."


class InvalidArchitecture(_Error):
    """The machine architecture is not supported.

    :param arch_name: the unsupported architecture name.
    """

    def __init__(self, arch_name: str):
        super().__init__()
        self._arch_name = arch_name

    def get_brief(self) -> str:
        return f"Architecture {self._arch_name!r} is invalid."

    def get_resolution(self) -> str:
        return "Make sure the requested architecture is supported."


class PartDependencyCycle(_Error):
    """Dependency cycles have been detected in the parts definition."""

    def get_brief(self) -> str:
        return "A circular dependency chain was detected."

    def get_resolution(self) -> str:
        return "Review the parts definition to remove dependency cycles."


class InvalidPartName(_Error):
    """An operation was requested on a part that's in the parts specification.

    :param part_name: the invalid part name.
    """

    def __init__(self, part_name: str):
        super().__init__()
        self._part_name = part_name

    def get_brief(self) -> str:
        return f"A part named {self._part_name!r} is not defined in the parts list."

    def get_resolution(self) -> str:
        return "Check for typos in the part name or in the parts definition."


class InvalidPluginAPIVersion(_Error):
    """A request was made to use an unsupported plugin API version.

    :param version: the invalid plugin API version.
    """

    def __init__(self, version: str):
        super().__init__()
        self._version = version

    def get_brief(self) -> str:
        return f"Plugin version {self._version!r} does not exist."

    def get_resolution(self) -> str:
        return "Check for typos in the plugin version."


class InvalidPlugin(_Error):
    """A request was made to use a plugin that's not defined.

    :param plugin_name: The invalid plugin name."
    """

    def __init__(self, plugin_name: str):
        super().__init__()
        self._plugin_name = plugin_name

    def get_brief(self) -> str:
        return f"Plugin {self._plugin_name!r} does not exist."

    def get_resolution(self) -> str:
        return (
            "Check for typos in the plugin name and make sure the plugin is supported."
        )


class PluginBuildError(_ReportableError):
    """An exception to raise when the PluginV2 build fails at runtime.

    :param part_name: the name of the part where the plugin build failed.
    """

    def __init__(self, *, part_name: str) -> None:
        super().__init__()
        self._part_name = part_name

    def get_brief(self) -> str:
        return f"Failed to build {self._part_name!r}."

    def get_resolution(self) -> str:
        return "Check the build logs and ensure the part configuration is correct."


class ScriptletRunError(_Error):
    """A scriptlet execution failed.

    :param scriptlet_name: the name of the scriptlet that failed to execute.
    :param code: the execution error code.
    """

    def __init__(self, scriptlet_name: str, code: int):
        super().__init__()
        self._name = scriptlet_name
        self._code = code

    def get_brief(self) -> str:
        return f"{self._name} scriptlet execution failed with code {self._code}."

    def get_resolution(self) -> str:
        return "Check the build logs and make sure the scriptlet is correct."


class InvalidControlAPICall(_Error):
    """A control API call was made with invalid parameters.

    :param scriptlet_name: the name of the scriptlet that originated the call.
    """

    def __init__(self, scriptlet_name: str, message: str):
        super().__init__()
        self._name = scriptlet_name
        self._message = message

    def get_brief(self) -> str:
        return f"{self._name} executed an invallid control API call: {self._message}"

    def get_resolution(self) -> str:
        return "Verify the scriptlet commands and make sure control calls are correct."


class InvalidEnvironment(_Error):
    """The environment is incorrect.

    :param message: the error message.
    """

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def get_brief(self) -> str:
        return f"Environment error: {self._message}"

    def get_resolution(self) -> str:
        return "Check the environment and make sure it's correct."


class CallbackRegistration(_Error):
    """Error in callback function registration.

    :param message: the error message.
    """

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def get_brief(self) -> str:
        return f"Callback registration error: {self._message}"

    def get_resolution(self) -> str:
        return "The same callback shouldn't be registered more than once."


class SourceUpdateUnsupported(_Error):
    """Source don't support updating.

    :param source: the source specification.
    """

    def __init__(self, source):
        super().__init__()
        self._source = source

    def get_brief(self) -> str:
        return f"Cannot update source: {self._source!r} sources don't support updating."

    # TODO: add a resolution string
    def get_resolution(self) -> str:
        return ""


class InvalidSourceType(_Error):
    """Source type is unknown.

    :param source: the source specification.
    """

    def __init__(self, source):
        super().__init__()
        self._source = source

    def get_brief(self) -> str:
        return f"Source {self._source!r} type is not recognized."

    # TODO: add a resolution string
    def get_resolution(self) -> str:
        return "Verify the source specification and the supported source types."


class PullError(_Error):
    """Failed to pull source."""

    def __init__(self, command, exit_code):
        super().__init__()

        if isinstance(command, list):
            self._command = " ".join(shlex.quote(i) for i in command)
        else:
            self._command = command

        self._code = exit_code

    def get_brief(self) -> str:
        return (
            "Failed to pull source: command {self._command!r} exited with "
            "code {self._code!r}."
        )

    def get_resolution(self) -> str:
        return "Check the sources and try again."


class CopyFileNotFound(_Error):
    """An attempt was made to copy a file that doesn't exist."""

    def __init__(self, name):
        super().__init__()
        self._name = name

    def get_brief(self) -> str:
        return "Failed to copy {self._name!r}: no such file or directory."

    def get_resolution(self) -> str:
        return "Check the path and try again."


class ChecksumMismatch(_Error):
    """A checksum doesn't match the expected value."""

    def __init__(self, expected: str, actual: str):
        super().__init__()
        self._expected = expected
        self._actual = actual

    def get_brief(self) -> str:
        return f"Expected the digest to be {self._expected}, but it was {self._actual}"

    def get_resolution(self) -> str:
        return "Make sure the source file has not been modified or corrupt."


class NetworkError(_Error):
    """A network request failed."""

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def get_brief(self) -> str:
        return f"Network operation failed: {self._message}"

    def get_resolution(self) -> str:
        return "Make sure network is available and properly configured."


class SourceNotFound(_Error):
    """The source could not be pulled."""

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def get_brief(self) -> str:
        return f"Failed to pull source: {self._message}"

    def get_resolution(self) -> str:
        return "Make sure source path is correct and that it is accessible."


class InvalidSourceOption(_Error):
    """The specified options are invalid for the chosen source type."""

    def __init__(self, source_type: str, option: str):
        super().__init__()
        self._source_type = source_type
        self._option = option

    def get_brief(self) -> str:
        return f"{self._option!r} cannot be used with a {self._source_type} source."

    def get_resolution(self) -> str:
        return "Make sure source options are correct and try again."


class FilesetError(_Error):
    """The specified options are invalid for the chosen source type."""

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def get_brief(self) -> str:
        return f"File specification error: {self._message}"

    def get_resolution(self) -> str:
        return "Make sure files are correctly specified and try again."


class SchemaValidation(_Error):
    """The parts data failed schema validation.

    :param message: the error message from the schema validator.
    """

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def get_brief(self) -> str:
        return f"Schema validation error: {self._message}"

    def get_resolution(self) -> str:
        return "Check the parts definition and make sure it's correct."

    @property
    def message(self):
        """The schema validation error message."""
        return self._message

    @classmethod
    def from_validation_error(cls, error: jsonschema.ValidationError):
        """Take a jsonschema.ValidationError and create a SnapcraftSchemaError.

        The validation errors coming from jsonschema are a nightmare. This
        class tries to make them a bit more understandable.
        """

        messages: List[str] = []

        preamble = schema_helpers.determine_preamble(error)
        cause = schema_helpers.determine_cause(error)
        supplement = schema_helpers.determine_supplemental_info(error)

        if preamble:
            messages.append(preamble)

        # If we have a preamble we are not at the root
        if supplement and preamble:
            messages.append(error.message)
            messages.append(f"({supplement})")
        elif supplement:
            messages.append(supplement)
        elif cause:
            messages.append(cause)
        else:

            messages.append(error.message)

        return cls(" ".join(messages))
