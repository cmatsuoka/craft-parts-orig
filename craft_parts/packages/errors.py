# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2019 Canonical Ltd
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

"""Exceptions raised by the packages handling subsystem."""

from abc import ABC
from typing import List, Sequence

from craft_parts import errors
from craft_parts.utils import os_utils

from ._platform import is_deb_based

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

# Enforce our constructor arguments
# pylint: disable=useless-super-delegation


class PackagesError(errors.CraftPartsError, ABC):
    pass


class NoNativeBackendError(PackagesError):

    fmt = "Native builds aren't supported on {distro}."

    def __init__(self):
        try:
            distro = os_utils.OsRelease().name()
        except errors.OsReleaseNameError:
            distro = "this system"
        super().__init__(distro=distro)


class CacheUpdateFailed(PackagesError):

    fmt = (
        "Failed to update the package cache: "
        "Some files could not be downloaded:{errors}"
        "Check that the sources on your host are configured correctly."
    )

    # pylint: disable=redefined-outer-name
    def __init__(self, errors: str) -> None:
        if errors:
            errors = "\n\n{}\n\n".format(errors.replace(", ", "\n"))
        else:
            errors = " "
        super().__init__(errors=errors)

    # pylint: enable=redefined-outer-name


class FileProviderNotFound(PackagesError):

    fmt = "{file_path} is not provided by any package."

    def __init__(self, *, file_path: str) -> None:
        super().__init__(file_path=file_path)


class BuildPackageNotFound(PackagesError):

    fmt = "Could not find a required package in 'build-packages': {package}"

    def __init__(self, package):
        super().__init__(package=package)


class BuildPackagesNotInstalled(PackagesError):

    fmt = "Could not install all requested build packages: {packages}"

    def __init__(self, *, packages: List[str]) -> None:
        super().__init__(packages=" ".join(packages))


class PackageFetchError(PackagesError):

    fmt = "Package fetch error: {message}"

    def __init__(self, message: str) -> None:
        super().__init__(message=message)


class PackageBroken(PackagesError):

    fmt = "The package {package} has unmet dependencies: {deps}"

    def __init__(self, package: str, deps: List[str]) -> None:
        super().__init__(package=package, deps=" ".join(deps))


class PackageNotFound(PackagesError):
    @property
    def message(self):
        message = "Package {!r} was not found.".format(self.package_name)
        # If the package was multiarch, try to help.
        distro = os_utils.OsRelease().id()
        if is_deb_based(distro) and ":" in self.package_name:
            (_, arch) = self.package_name.split(":", 2)
            if arch:
                message += (
                    "\nYou may need to add support for this architecture with "
                    "'dpkg --add-architecture {}'.".format(arch)
                )
        return message

    def __init__(self, package_name):
        super().__init__()
        self.package_name = package_name

    def __str__(self):
        return self.message


class UnpackError(PackagesError):

    fmt = "Error while provisioning {package!r}"

    def __init__(self, package):
        super().__init__(package=package)


class SnapUnavailableError(PackagesError):

    fmt = (
        "Failed to install or refresh a snap: {snap_name!r} does not exist "
        "or is not available on the desired channel {snap_channel!r}. "
        "Use `snap info {snap_name}` to get a list of channels the "
        "snap is available on."
    )

    def __init__(self, *, snap_name: str, snap_channel: str) -> None:
        super().__init__(snap_name=snap_name, snap_channel=snap_channel)


class SnapFindError(PackagesError):

    fmt = (
        "Could not find the snap {snap_name!r} installed on this host.\n"
        "Install the snap and try again."
    )

    def __init__(self, *, snap_name):
        super().__init__(snap_name=snap_name)


class SnapInstallError(PackagesError):

    fmt = "Error while installing snap {snap_name!r} from channel {snap_channel!r}"

    def __init__(self, *, snap_name, snap_channel):
        super().__init__(snap_name=snap_name, snap_channel=snap_channel)


class SnapDownloadError(PackagesError):

    fmt = "Error while downloading snap {snap_name!r} from channel {snap_channel!r}"

    def __init__(self, *, snap_name, snap_channel):
        super().__init__(snap_name=snap_name, snap_channel=snap_channel)


class SnapGetAssertionError(PackagesError):

    fmt = (
        "Error while retrieving assertion with parameters "
        "{assertion_params!r}\n"
        "Verify the assertion exists and try again."
    )

    def __init__(self, *, assertion_params: Sequence[str]) -> None:
        super().__init__(assertion_params=assertion_params)


class SnapRefreshError(PackagesError):

    fmt = "Error while refreshing snap {snap_name!r} to channel {snap_channel!r}"

    def __init__(self, *, snap_name, snap_channel):
        super().__init__(snap_name=snap_name, snap_channel=snap_channel)


class SnapdConnectionError(PackagesError):

    fmt = (
        "Failed to get information for snap {snap_name!r}: "
        "could not connect to {url!r}."
    )

    def __init__(self, snap_name: str, url: str) -> None:
        super().__init__(snap_name=snap_name, url=url)
