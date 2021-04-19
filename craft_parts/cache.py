# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016-2021 Canonical Ltd
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

"""Implement the tar source handler."""

import logging
import os
import shutil
from typing import Optional

from xdg import BaseDirectory  # type: ignore

logger = logging.getLogger(__name__)


class Cache:
    """Generic cache base class.

    This class is responsible for cache location, notification and pruning.
    """

    def __init__(self, name: str):
        self.cache_root = os.path.join(
            BaseDirectory.xdg_cache_home, name, "craft-parts"
        )


class FileCache(Cache):
    """Generic file cache."""

    def __init__(self, name: str, *, namespace: str = "files") -> None:
        """Create a FileCache under namespace.

        :param str namespace: set the namespace for the cache
                              (default: "files").
        """
        super().__init__(name)
        self.file_cache = os.path.join(self.cache_root, namespace)

    def cache(self, *, filename: str, key: str) -> Optional[str]:
        """Cache a file revision with hash in XDG cache, unless it already exists.
        :param str filename: path to the file to cache.
        :param str algorithm: algorithm used to calculate the hash as
                              understood by hashlib.
        :param str digest: hash for filename calculated with algorithm.
        :returns: path to cached file.
        """
        cached_file_path = os.path.join(self.file_cache, key)
        os.makedirs(os.path.dirname(cached_file_path), exist_ok=True)
        try:
            if not os.path.isfile(cached_file_path):
                # this must not be hard-linked, as rebuilding a snap
                # with changes should invalidate the cache, hence avoids
                # using fileutils.link_or_copy.
                shutil.copyfile(filename, cached_file_path)
        except OSError:
            logger.warning("Unable to cache file %s.", cached_file_path)
            return None
        return cached_file_path

    def get(self, *, key):
        """Get the filepath which matches the hash calculated with algorithm.

        :param str algorithm: algorithm used to calculate the hash as
                              understood by hashlib.
        :param str digest: hash for filename calculated with algorithm.
        :returns: path to cached file.
        """
        cached_file_path = os.path.join(self.file_cache, key)
        if os.path.exists(cached_file_path):
            logger.debug("Cache hit for key %s", key)
            return cached_file_path

        return None
