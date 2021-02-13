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

"""Base classes for source type handling."""

import abc
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

import requests

from craft_parts import utils
from craft_parts.cache import FileCache
from craft_parts.utils import url_utils

from . import errors
from .checksum import split_checksum, verify_checksum


class SourceHandler(abc.ABC):
    """The base class for source type handlers."""

    # pylint: disable=too-many-arguments

    def __init__(
        self,
        source: str,
        source_dir: Path,
        *,
        application_name: Optional[str] = None,
        source_tag: Optional[str] = None,
        source_commit: Optional[str] = None,
        source_branch: Optional[str] = None,
        source_depth: Optional[str] = None,
        source_checksum: Optional[str] = None,
        command: Optional[List[str]] = None,
    ):
        if not application_name:
            application_name = utils.package_name()

        self._application_name = application_name
        self.source = source
        self.source_dir = str(source_dir)
        self.source_tag = source_tag
        self.source_commit = source_commit
        self.source_branch = source_branch
        self.source_depth = source_depth
        self.source_checksum = source_checksum
        self.source_details = None

        self.command = command
        self._checked = False

    # pylint: enable=too-many-arguments

    @abc.abstractmethod
    def pull(self):
        """Retrieve the source file."""

    def check(self, target: str, ignore_files: Optional[List[str]] = None) -> bool:
        """Check if pulled sources have changed since target was created.

        :param str target: Path to target file.
        """
        self._checked = True
        return self._check(target, ignore_files=ignore_files)

    def update(self):
        """Update pulled source.

        :raises RuntimeError: If this function is called before `check()`.
        """
        if not self._checked:
            # This is programmer error
            raise RuntimeError("source must be checked before it's updated")
        self._update()

    def _check(self, target: str, ignore_files: Optional[List[str]]):
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

    # pylint: enable=no-self-use


class FileSourceHandler(SourceHandler, abc.ABC):
    """Base class for file source types."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        source: str,
        source_dir: Path,
        *,
        application_name: Optional[str],
        source_tag: Optional[str] = None,
        source_commit: Optional[str] = None,
        source_branch: Optional[str] = None,
        source_depth: Optional[str] = None,
        source_checksum: Optional[str] = None,
        command: Optional[List[str]] = None,
    ):
        super().__init__(
            source,
            source_dir,
            application_name=application_name,
            source_tag=source_tag,
            source_commit=source_commit,
            source_branch=source_branch,
            source_depth=source_depth,
            source_checksum=source_checksum,
            command=command,
        )
        self._file = ""

    # pylint: enable=too-many-arguments

    def pull(self):
        """Retrieve this source from its origin."""

        source_file = None
        is_source_url = url_utils.isurl(self.source)

        # First check if it is a url and download and if not
        # it is probably locally referenced.
        if is_source_url:
            source_file = self.download()
        else:
            basename = os.path.basename(self.source)
            source_file = os.path.join(self.source_dir, basename)
            # We make this copy as the provisioning logic can delete
            # this file and we don't want that.
            try:
                shutil.copy2(self.source, source_file)
            except FileNotFoundError as err:
                raise errors.SourceNotFound(self.source) from err

        # Verify before provisioning
        if self.source_checksum:
            verify_checksum(self.source_checksum, source_file)

        # We finally provision, but we don't clean the target so override-pull
        # can actually have meaning when using these sources.
        self.provision(self.source_dir, src=source_file, clean_target=False)

    def download(self, filepath: str = None) -> str:
        """Download the URL from a remote location.

        :param filepath: the destination file to download to.
        """

        if filepath is None:
            self._file = os.path.join(self.source_dir, os.path.basename(self.source))
        else:
            self._file = filepath

        digest: str = ""

        # First check if we already have the source file cached.
        file_cache = FileCache(self._application_name)
        if self.source_checksum:
            algorithm, digest = split_checksum(self.source_checksum)
            cache_file = file_cache.get(algorithm=algorithm, digest=digest)
            if cache_file:
                # We make this copy as the provisioning logic can delete
                # this file and we don't want that.
                shutil.copy2(cache_file, self._file)
                return self._file

        # If not we download and store
        if url_utils.get_url_scheme(self.source) == "ftp":
            url_utils.download(self.source, self._file)
        else:
            try:
                request = requests.get(self.source, stream=True, allow_redirects=True)
                request.raise_for_status()
            except requests.exceptions.RequestException as err:
                raise errors.NetworkRequestError(
                    message=f"network request failed (request={err.request!r}, "
                    "response={err.response!r}"
                )

            url_utils.download_and_show_progress(request, self._file)

        # We verify the file if source_checksum is defined
        # and we cache the file for future reuse.
        if self.source_checksum:
            algorithm, digest = verify_checksum(self.source_checksum, self._file)
            file_cache.cache(filename=self._file, algorithm=algorithm, digest=digest)
        return self._file

    @abc.abstractmethod
    def provision(self, dst, clean_target=True, keep=False, src=None):
        """Process the source file to extract its payload."""
