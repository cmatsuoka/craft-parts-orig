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

from abc import ABC
from pathlib import Path
from typing import List, Union

import jsonschema  # type: ignore

from craft_parts.utils import schema_helpers


class CraftPartsError(Exception, ABC):
    """Base class for Craft Parts exceptions."""

    fmt = "Daughter classes should redefine this"

    def __init__(self, **kwargs) -> None:
        super().__init__()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return self.fmt.format([], **self.__dict__)


class CraftPartsReportableError(CraftPartsError):
    """Base class for reportable Craft Parts exceptions."""


class InternalError(CraftPartsReportableError):
    """Internal error."""

    fmt = "Internal error: {message}"

    def __init__(self, message: str):
        super().__init__(message=message)


class InvalidArchitecture(CraftPartsError):
    """The machine architecture is not supported.

    :param arch_name: the unsupported architecture name.
    """

    fmt = "Architecture {arch_name!r} is not supported."

    def __init__(self, arch_name: str):
        super().__init__(arch_name=arch_name)


class PartDependencyCycle(CraftPartsError):
    """Dependency cycles have been detected in the parts definition."""

    fmt = (
        "A circular dependency chain was detected. Please review the parts "
        "definition to remove dependency cycles."
    )


class InvalidPartName(CraftPartsError):
    """An operation was requested on a part that's in the parts specification.

    :param part_name: the invalid part name.
    """

    fmt = "A part named {part_name!r} is not defined in the parts list."

    def __init__(self, part_name: str):
        super().__init__(part_name=part_name)


class InvalidAction(CraftPartsError):
    """An attempt was made to execute an action with invalid parameters."""

    fmt = "Action is invalid: {message}"

    def __init__(self, message: str):
        super().__init__(message=message)


class InvalidPluginAPIVersion(CraftPartsError):
    """A request was made to use an unsupported plugin API version.

    :param version: the invalid plugin API version.
    """

    fmt = "Plugin version {version!r} is not supported."

    def __init__(self, version: str):
        super().__init__(version=version)


class UndefinedPlugin(CraftPartsError):
    """The part didn't define a plugin and the part name is not a valid plugin name."""

    fmt = "Plugin not defined for part {part_name!r}."

    def __init__(self, part_name: str):
        super().__init__(part_name=part_name)


class InvalidPlugin(CraftPartsError):
    """A request was made to use a plugin that's not defined.

    :param plugin_name: The invalid plugin name."
    """

    fmt = "A plugin named {plugin_name!r} is not registered."

    def __init__(self, plugin_name: str):
        super().__init__(plugin_name=plugin_name)


class PluginBuildError(CraftPartsReportableError):
    """An exception to raise when the PluginV2 build fails at runtime.

    :param part_name: the name of the part where the plugin build failed.
    """

    fmt = "Failed to run the build script for part {part_name!r}."

    def __init__(self, part_name: str) -> None:
        super().__init__(part_name=part_name)


class ScriptletRunError(CraftPartsError):
    """A scriptlet execution failed.

    :param part_name: the name of the part where the scriptlet execution failed.
    :param scriptlet_name: the name of the scriptlet that failed to execute.
    :param exit_code: the execution error code.
    """

    fmt = (
        "The {scriptlet_name} scriptlet in part {part_name!r} failed "
        "with code {exit_code}."
    )

    def __init__(self, part_name: str, scriptlet_name: str, exit_code: int):
        super().__init__(
            part_name=part_name, scriptlet_name=scriptlet_name, exit_code=exit_code
        )


class InvalidControlAPICall(CraftPartsError):
    """A control API call was made with invalid parameters.

    :param scriptlet_name: the name of the scriptlet that originated the call.
    :param message: the error message.
    """

    fmt = (
        "The {scriptlet_name} in part {part_name!r} executed an invallid "
        "control API call: {self._message}"
    )

    def __init__(self, part_name, scriptlet_name: str, message: str):
        super().__init__(
            part_name=part_name, scriptlet_name=scriptlet_name, message=message
        )


class InvalidEnvironment(CraftPartsError):
    """The environment is incorrect.

    :param message: the error message.
    """

    fmt = "Environment error: {message}"

    def __init__(self, message: str):
        super().__init__(message=message)


class CallbackRegistration(CraftPartsError):
    """Error in callback function registration.

    :param message: the error message.
    """

    fmt = "Callback registration error: {message}"

    def __init__(self, message: str):
        super().__init__(message=message)


class CopyFileNotFound(CraftPartsError):
    """An attempt was made to copy a file that doesn't exist."""

    fmt = "Failed to copy {name!r}: no such file or directory."

    def __init__(self, name):
        super().__init__(name=name)


class FilesetError(CraftPartsError):
    """An invalid fileset operation was performed."""

    fmt = "File specification error{where}: {message}"

    def __init__(self, name: str, message: str):
        where = ""
        if name:
            where = f" in {name!r}"
        super().__init__(where=where, message=message)


class OsReleaseIdError(CraftPartsError):
    """Failed to determine the host operating system identification string."""

    fmt = "Unable to determine host OS ID"


class OsReleaseNameError(CraftPartsError):
    """Failed to deterime the host operating system name."""

    fmt = "Unable to determine host OS name"


class OsReleaseVersionIdError(CraftPartsError):
    """Failed to deterime the host operating system version."""

    fmt = "Unable to determine host OS version ID"


class OsReleaseCodenameError(CraftPartsError):
    """Failed to deterime the host operating system version codename."""

    fmt = "Unable to determine host OS version codename"


class MissingTool(CraftPartsError):
    """A required tool was not found."""

    fmt = "A required tool could not be found: {command_name!r}."

    def __init__(self, command_name: str):
        super().__init__(command_name=command_name)


class StagePackageError(CraftPartsError):
    """Error when installing stage packages."""

    fmt = "Stage package error in part {part_name!r}: {message}"

    def __init__(self, part_name: str, message: str):
        super().__init__(part_name=part_name, message=message)


class CorruptedElfFile(CraftPartsError):
    """Failed to parse an ELF header from a binary file."""

    fmt = "Unable to parse ELF file {path!r}: {message}"

    def __init__(self, path: str, message: str) -> None:
        super().__init__(path=path, message=message)


class FileOrganizeError(CraftPartsError):
    """Failed to organize a file layout."""

    fmt = "Failed to organize part {part_name!r}: {message}"

    def __init__(self, part_name, message):
        super().__init__(part_name=part_name, message=message)


class PartConflictError(CraftPartsError):
    """Different parts list the same files with different contents."""

    fmt = (
        "Failed to stage: "
        "Parts {other_part_name!r} and {part_name!r} have the following "
        "files, but with different contents:\n"
        "{file_paths}"
    )

    def __init__(
        self, *, part_name: str, other_part_name: str, conflict_files: List[str]
    ):
        spaced_conflict_files = ("    {}".format(i) for i in conflict_files)
        super().__init__(
            part_name=part_name,
            other_part_name=other_part_name,
            file_paths="\n".join(sorted(spaced_conflict_files)),
        )


class StageFilesConflictError(CraftPartsError):
    """Files from a part conflict with files already being staged."""

    fmt = (
        "Failed to stage: "
        "The following files in part {part_name!r} are already being staged "
        "with different content:\n"
        "{file_paths}"
    )

    def __init__(self, *, part_name: str, conflict_files: List[str]):
        spaced_conflict_files = ("    {}".format(i) for i in conflict_files)
        super().__init__(
            part_name=part_name,
            file_paths="\n".join(sorted(spaced_conflict_files)),
        )


class SchemaNotFound(CraftPartsReportableError):
    """Failed to find a schema definition."""

    fmt = "Unable to find the schema definition file {path!r}."

    def __init__(self, path: Union[str, Path]) -> None:
        super().__init__(path=path)


class SchemaValidationError(CraftPartsError):
    """The parts data failed schema validation.

    :param message: the error message from the schema validator.
    """

    fmt = "Schema validation error: {message}"

    def __init__(self, message: str):
        super().__init__(message=message)

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


class XAttributeError(CraftPartsReportableError):
    """Failed to read or write an extended attribute."""

    fmt = "Unable to {action} attribute {key!r} on {path!r}."

    def __init__(self, action: str, key: str, path: str):
        super().__init__(action=action, key=key, path=path)


class XAttributeTooLongError(CraftPartsReportableError):
    """Failed to write an extended attribute because key and/or value is too long."""

    fmt = (
        "Failed to write attribute to {path!r}: key and/or value is too long\n"
        "key={key!r} value={value!r}"
    )

    def __init__(self, key: str, value: str, path: str):
        super().__init__(key=key, value=value, path=path)


class CleanLayerError(CraftPartsError):
    """Failed to clean a filesystem layer."""

    fmt = "Failed to clean layer: {message}"

    def __init__(self, message: str):
        super().__init__(message=message)


class ExportOverlayError(CraftPartsError):
    """Failed to export an overlay mount."""

    fmt = "Failed to export overlay: {message}"

    def __init__(self, message: str):
        super().__init__(message=message)
