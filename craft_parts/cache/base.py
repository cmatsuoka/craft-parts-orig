# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016, 2017 Canonical Ltd
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

"""Base class for caches."""

import os

from xdg import BaseDirectory  # type: ignore


# pylint: disable=too-few-public-methods
class Cache:
    """Generic cache base class.

    This class is responsible for cache location, notification and pruning.
    """

    def __init__(self, name: str):
        self.cache_root = os.path.join(
            BaseDirectory.xdg_cache_home, name, "craft-parts"
        )


class StagePackageCache(Cache):
    """Cache specific to stage-packages."""

    def __init__(self, name: str):
        super().__init__(name)
        self.stage_package_cache_root = os.path.join(
            self.cache_root, name, "stage-packages"
        )
