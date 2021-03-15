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

from pathlib import Path

from craft_parts.utils import os_utils


class Overlay:
    def __init__(
        self, *, mountpoint: Path, lowerdir: Path, upperdir: Path, workdir: Path
    ):
        self._mountpoint = str(mountpoint)
        self._lower_dir = str(lowerdir)
        self._upper_dir = str(upperdir)
        self._work_dir = str(workdir)

    def mount(self):
        os_utils.mount(
            "overlay",
            self._mountpoint,
            "-toverlay",
            "-olowerdir={},upperdir={},workdir={}".format(
                self._lower_dir, self._upper_dir, self._work_dir
            ),
        )

    def unmount(self):
        os_utils.umount(self._mountpoint)
