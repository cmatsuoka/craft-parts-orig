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

import pychroot  # type: ignore

from craft_parts import packages

from .overlays import OverlayFS

logger = logging.getLogger(__name__)


class BaseLayer:
    def __init__(self, *, upperdir, lowerdir, workdir, mountpoint):
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

    def flatten(self, destdir: Path) -> None:
        pass


class StagePackagesLayer(BaseLayer):
    def __init__(self, root: Path, base: Path):
        super().__init__(
            upperdir=root / "stage_packages",
            lowerdir=base,
            workdir=root / "stage_packages_work",
            mountpoint=root / "stage_packages_overlay",
        )


class StageLayer(BaseLayer):
    def __init__(self, root: Path):
        super().__init__(
            upperdir=root / "stage",
            lowerdir=root / "stage_packages",
            workdir=root / "stage_work",
            mountpoint=root / "stage_overlay",
        )


class PrimeLayer(BaseLayer):
    def __init__(self, root: Path):
        super().__init__(
            upperdir=root / "prime",
            lowerdir=root / "stage_packages",
            workdir=root / "prime_work",
            mountpoint=root / "prime_overlay",
        )


class Layer:
    def __init__(self, layer: BaseLayer):
        self._layer = layer
        self._layer.mkdirs()
        self._pid = os.getpid()

    def __enter__(self):
        self._layer.mount()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if os.getpid() != self._pid:
            sys.exit()
        self._layer.unmount()
        return False

    def install_packages(self, *, package_list: Optional[List[str]]) -> None:
        if not package_list:
            return []

        with contextlib.suppress(SystemExit), pychroot.Chroot(self._layer.mountpoint):
            # FIXME: do at start, rename because it's not only for build packages
            packages.Repository.refresh_build_packages()
            packages.Repository.install_build_packages(package_list)
