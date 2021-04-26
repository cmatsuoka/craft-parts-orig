# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2021 Canonical Ltd.
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

"""Definition and helpers for the repository base class."""

import abc
import contextlib
import logging
import os
from pathlib import Path
from typing import List, Optional, Set, Tuple, Type

from craft_parts import xattrs

from .normalize import normalize

logger = logging.getLogger(__name__)


class BaseRepository(abc.ABC):
    """Base implementation for a platform specific repository handler.

    Generally any new repository handling system would inherit from
    this and implement:

    - get
    - unpack
    - get_packages_for_source_type
    - refresh_build_packages_list
    - install_build_packages
    - is_package_installed
    - get_installed_packages
    - fetch_stage_packages
    - unpack_stage_packages
    - refresh_stage_package_list

    At the end of the :meth:`unpack` method :meth:`normalize` must be
    called to make the artifacts downloaded generic and consistent.
    """

    @classmethod
    @abc.abstractmethod
    def get_package_libraries(cls, package_name: str) -> Set[str]:
        """Return a list of libraries in package_name.

        Given the contents of package_name, return the subset of what are
        considered libraries from those contents, be it static or shared.

        :param package_name: The package name to get library contents from.
        :return: A list of libraries that package_name provides, with paths.
        """

    @classmethod
    @abc.abstractmethod
    def get_packages_for_source_type(cls, source_type: str) -> Set[str]:
        """Return a list of packages required to to work with source_type.

        :param source_type: A source type to handle.

        :return: A set of packages that need to be installed on the host.
        """

    @classmethod
    @abc.abstractmethod
    def refresh_build_packages_list(cls) -> None:
        """Refresh the build packages cache.

        If refreshing is not possible
        craft_parts.packages.errors.CacheUpdateFailed should be raised
        """

    @classmethod
    @abc.abstractmethod
    def install_build_packages(cls, package_names: List[str]) -> List[str]:
        """Install packages on the host required to build.

        This method needs to be implemented by using the appropriate method
        to install packages on the system. If possible they should be marked
        as automatically installed to allow for easy removal.
        The method should return a list of the actually installed packages
        in the form "package=version".

        If one of the packages cannot be found
        craft_parts.packages.errors.BuildPackageNotFound should be raised.
        If dependencies for a package cannot be resolved
        craft_parts.packages.errors.PackageBroken should be raised.
        If installing a package on the host failed
        craft_parts.packages.errors.BuildPackagesNotInstalled should be raised.

        :param package_names: A list of package names to install.

        :return: A list with the packages installed and their versions.
        """

    @classmethod
    @abc.abstractmethod
    def is_package_installed(cls, package_name: str) -> bool:
        """Return a bool indicating if package_name is installed.

        :param package_name: The package name to query.

        :return: Whether the package_name is installed.
        """

    @classmethod
    @abc.abstractmethod
    def get_installed_packages(cls) -> List[str]:
        """Obtain a list of the installed packages and their versions.

        :return: A list of installed packages in the form package=version.
        """

    @classmethod
    @abc.abstractmethod
    def fetch_stage_packages(
        cls,
        *,
        application_name: str,
        package_names: List[str],
        base: str,
        stage_packages_path: Path,
        target_arch: str,
        list_only: bool = False,
    ) -> List[str]:
        """Fetch stage packages to stage_packages_path."""

    @classmethod
    @abc.abstractmethod
    def unpack_stage_packages(
        cls, *, stage_packages_path: Path, install_path: Path
    ) -> None:
        """Unpack stage packages to install_path."""

    @classmethod
    @abc.abstractmethod
    def refresh_stage_packages_list(
        cls, *, application_name: str, target_arch: str
    ) -> None:
        """Refresh the list of packages available in the repository."""

    @classmethod
    def normalize(cls, unpack_dir: str) -> None:
        normalize(unpack_dir, cls)


class DummyRepository(BaseRepository):
    """A dummy repository."""

    @classmethod
    def get_package_libraries(cls, package_name: str) -> Set[str]:
        """Return a list of libraries in package_name."""
        return set()

    @classmethod
    def get_packages_for_source_type(cls, source_type: str) -> Set[str]:
        """Return a list of packages required to to work with source_type."""
        return set()

    @classmethod
    def refresh_build_package_list(cls) -> None:
        """Refresh the build packages cache."""

    @classmethod
    def install_build_packages(cls, package_names: List[str]) -> List[str]:
        """Install packages on the host required to build."""
        return []

    @classmethod
    def is_package_installed(cls, package_name: str) -> bool:
        """Return a bool indicating if package_name is installed."""
        return False

    @classmethod
    def get_installed_packages(cls) -> List[str]:
        """Obtain a list of the installed packages and their versions."""
        return []

    @classmethod
    def fetch_stage_packages(
        cls,
        **kwargs,  # pylint: disable=unused-argument
    ) -> List[str]:
        """Fetch stage packages to stage_packages_path."""
        return []

    @classmethod
    def unpack_stage_packages(
        cls, *, stage_packages_path: Path, install_path: Path
    ) -> None:
        """Unpack stage packages to install_path."""

    @classmethod
    def update_package_list(cls, *, application_name: str, target_arch: str) -> None:
        """Refresh the list of packages available in the repository."""


def get_pkg_name_parts(pkg_name: str) -> Tuple[str, Optional[str]]:
    """Break package name into base parts."""
    name = pkg_name
    version = None
    with contextlib.suppress(ValueError):
        name, version = pkg_name.split("=")

    return name, version


def mark_origin_stage_package(sources_dir: str, stage_package: str) -> Set[str]:
    """Mark all files in sources_dir as coming from stage_package."""
    file_list = set()
    for (root, _, files) in os.walk(sources_dir):
        for file_name in files:
            file_path = os.path.join(root, file_name)

            # Mark source.
            xattrs.write_origin_stage_package(file_path, stage_package)

            file_path = os.path.relpath(root, sources_dir)
            file_list.add(file_path)

    return file_list


RepositoryType = Type[BaseRepository]
