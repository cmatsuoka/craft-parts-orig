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

import abc
import contextlib
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Set, cast

from craft_parts import errors, packages
from craft_parts.state_manager import GlobalState, load_global_state

from . import chroot
from .overlays import OverlayFS

# import pychroot  # type: ignore


logger = logging.getLogger(__name__)


class LayerState(GlobalState):

    yaml_tag = "!LayerState"

    def __init__(self, *, base_packages: Set[str] = None):
        if not base_packages:
            base_packages = set()

        self.base_packages = base_packages


class Layers(abc.ABC):
    def __init__(
        self,
        *,
        state_dir: Path,
        upper_dir: Path,
        lower_dir: Path,
        work_dir: Path,
        mountpoint: Path,
        state_file: str,
    ):
        self._state_dir = state_dir
        self._upper_dir = upper_dir
        self._lower_dir = lower_dir
        self._work_dir = work_dir
        self._mountpoint = mountpoint
        self._state_file = state_file

        self._overlayfs = OverlayFS(
            upper_dir=upper_dir,
            lower_dir=lower_dir,
            work_dir=work_dir,
            mountpoint=mountpoint,
        )

    @property
    def mountpoint(self) -> Path:
        return self._mountpoint

    @property
    def upper_dir(self) -> Path:
        return self._upper_dir

    def mount(self) -> None:
        self._overlayfs.mount()

    def unmount(self) -> None:
        self._overlayfs.unmount()

    def mkdirs(self) -> None:
        self._upper_dir.mkdir(parents=True, exist_ok=True)
        self._lower_dir.mkdir(parents=True, exist_ok=True)
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._mountpoint.mkdir(parents=True, exist_ok=True)

    def clean(self):
        if os.path.ismount(self._mountpoint):
            raise errors.LayerCleanError(f"{self._mountpoint} is mounted")

        for directory in [self._upper_dir, self._work_dir, self._state_dir]:
            with contextlib.suppress(FileNotFoundError):
                shutil.rmtree(directory)

        self.mkdirs()

    def extract_to(self, dest: Path) -> None:
        shutil.copytree(self.upper_dir, dest)

    def load_state(self) -> Optional[LayerState]:
        state_data, _ = load_global_state(self._state_dir / self._state_file)
        return cast(LayerState, state_data)


class BasePackagesLayers(Layers):
    def __init__(self, root: Path, base: Path):
        super().__init__(
            state_dir=root / "state",
            upper_dir=root / "base_packages",
            lower_dir=base,
            work_dir=root / "base_packages_work",
            mountpoint=root / "base_packages_overlay",
            state_file="base_packages",
        )

    def write_state(self, *, base_packages: List[str]) -> None:
        state = LayerState(base_packages=set(base_packages))
        state.write(self._state_dir / self._state_file)


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

        for entry in chroot.created_files():
            relative = os.path.relpath(entry, "/")
            with contextlib.suppress(FileNotFoundError):
                os.unlink(os.path.join(self._layers.upper_dir, relative))

        return False

    def refresh_package_list(self) -> None:
        # with contextlib.suppress(SystemExit), pychroot.Chroot(self._layers.mountpoint):
        #    packages.Repository.refresh_build_packages()
        chroot.run(self._layers.mountpoint, packages.Repository.refresh_build_packages)

    def resolve_dependencies(self, package_list: List[str]) -> List[str]:
        if not package_list:
            return []

        installed_packages: List[str] = []  # FIXME

        installed_packages = chroot.run(
            self._layers.mountpoint,
            packages.Repository.install_build_packages,
            package_list,
            list_only=True,
        )

        return installed_packages

    def install_packages(self, package_list: List[str]) -> List[str]:
        if not package_list:
            return []

        installed_packages: List[str] = []

        # with contextlib.suppress(SystemExit), pychroot.Chroot(self._layers.mountpoint):
        #     # FIXME: rename to install_packages
        #     packages.Repository.install_build_packages(package_list)
        result = chroot.run(
            self._layers.mountpoint,
            packages.Repository.install_build_packages,
            package_list,
        )

        if result and isinstance(result, list):
            installed_packages = result

        return installed_packages
