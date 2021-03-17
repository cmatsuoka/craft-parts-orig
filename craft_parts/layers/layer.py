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

import contextlib
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# import pychroot  # type: ignore

from craft_parts import packages

from .chroot import chroot_run
from .overlays import OverlayFS


logger = logging.getLogger(__name__)


class Layers:
    def __init__(
        self, *, upperdir: Path, lowerdir: Path, workdir: Path, mountpoint: Path
    ):
        self._upperdir = upperdir
        self._lowerdir = lowerdir
        self._workdir = workdir
        self._mountpoint = mountpoint

        self._overlayfs = OverlayFS(
            upperdir=upperdir,
            lowerdir=lowerdir,
            workdir=workdir,
            mountpoint=mountpoint,
        )

    @property
    def mountpoint(self) -> Path:
        return self._mountpoint

    def mount(self) -> None:
        self._overlayfs.mount()

    def unmount(self) -> None:
        self._overlayfs.unmount()

    def mkdirs(self) -> None:
        self._upperdir.mkdir(parents=True, exist_ok=True)
        self._lowerdir.mkdir(parents=True, exist_ok=True)
        self._workdir.mkdir(parents=True, exist_ok=True)
        self._mountpoint.mkdir(parents=True, exist_ok=True)


class BasePackagesLayers(Layers):
    def __init__(self, root: Path, base: Path):
        super().__init__(
            upperdir=root / "base_packages",
            lowerdir=base,
            workdir=root / "base_packages_work",
            mountpoint=root / "base_packages_overlay",
        )


class Overlay:
    def __init__(self, layers: Layers):
        self._layers = layers
        self._layers.mkdirs()
        self._pid = os.getpid()

    def __enter__(self):
        self._layers.mount()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # workaround for pychroot 0.10.4 process leak
        if os.getpid() != self._pid:
            sys.exit()

        self._layers.unmount()
        return False

    def refresh_package_list(self) -> None:
        # with contextlib.suppress(SystemExit), pychroot.Chroot(self._layers.mountpoint):
        #    packages.Repository.refresh_build_packages()
        chroot_run(self._layers.mountpoint, packages.Repository.refresh_build_packages)

    def install_packages(self, package_list: Optional[List[str]]) -> List[str]:
        if not package_list:
            return []

        # with contextlib.suppress(SystemExit), pychroot.Chroot(self._layers.mountpoint):
        #     # FIXME: rename to install_packages
        #     packages.Repository.install_build_packages(package_list)
        chroot_run(self._layers.mountpoint, packages.Repository.install_build_packages, package_list)
