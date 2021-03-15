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

import os.path
from pathlib import Path
from typing import List, Optional

import pychroot  # type: ignore

from craft_parts import packages, utils

from .overlays import Overlay


class LayerInfo:
    def __init__(self, *, layer_dir: Path, base_dir: Path):
        self._layer_dir = layer_dir
        self._base_dir = base_dir

    @property
    def base(self) -> Path:
        return self._base_dir

    @property
    def stage_packages_upper(self) -> Path:
        return self._layer_dir / "stage_packages"

    @property
    def stage_packages_work(self) -> Path:
        return self._layer_dir / "stage_packages_work"

    @property
    def stage_packages_overlay(self) -> Path:
        return self._layer_dir / "stage_packages_overlay"


class LayerManager:
    def __init__(self, *, layer_dir: Path, base_dir: Path):
        self._info = LayerInfo(layer_dir=layer_dir, base_dir=base_dir)
        self._spool_name = "{}-spool".format(utils.package_name())

        dirs = [
            self._info.stage_packages_overlay,
            self._info.stage_packages_upper,
            self._info.stage_packages_work,
        ]
        for dir_name in dirs:
            os.makedirs(dir_name, exist_ok=True)
            
        self._stage_packages_overlay = Overlay(
            mountpoint=self._info.stage_packages_overlay,
            upperdir=self._info.stage_packages_upper,
            lowerdir=base_dir,
            workdir=self._info.stage_packages_work,
        )

    def mount_stage_packages_overlay(self) -> None:
        self._stage_packages_overlay.mount()

    def unmount_stage_packages_overlay(self) -> None:
        self._stage_packages_overlay.unmount()

    def install_packages(self, *, package_list: Optional[List[str]]) -> List[str]:
        if not package_list:
            return []

        print("==== package_list", package_list)

        with pychroot.Chroot(self._info.stage_packages_overlay):
            # FIXME: do at start, rename because it's not only for build packages
            packages.Repository.refresh_build_packages()

            return packages.Repository.install_build_packages(package_list)
