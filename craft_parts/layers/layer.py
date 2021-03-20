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

logger = logging.getLogger(__name__)


class LayerState(GlobalState):

    yaml_tag = "!LayerState"

    def __init__(self, *, base_packages: Set[str] = None):
        if not base_packages:
            base_packages = set()

        self.base_packages = base_packages


class _Layers(abc.ABC):
    def __init__(
        self,
        *,
        layer_dirs: List[Path],
    ):
        logger.debug("layer_dirs: %s", layer_dirs)

        if len(layer_dirs) < 2:
            raise ValueError("at least two layers are required in a layer stack")

        self._upper_dir = layer_dirs[0]
        self._lower_dirs = layer_dirs[1:]
        self._work_dir = self._upper_dir.parent / (self._upper_dir.name + "_work")
        self._mountpoint = self._upper_dir.parent / (self._upper_dir.name + "_overlay")

        self._overlayfs = OverlayFS(
            upper_dir=self._upper_dir,
            lower_dirs=self._lower_dirs,
            work_dir=self._work_dir,
            mountpoint=self._mountpoint,
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
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._mountpoint.mkdir(parents=True, exist_ok=True)

        for ldir in self._lower_dirs:
            ldir.mkdir(parents=True, exist_ok=True)

    def clean(self):
        if os.path.ismount(self._mountpoint):
            raise errors.CleanLayerError(f"{self._mountpoint} is mounted")

        for directory in [self._upper_dir, self._work_dir]:
            if directory:
                with contextlib.suppress(FileNotFoundError):
                    shutil.rmtree(directory)

        self.mkdirs()


class BasePackageLayerStack:
    def __init__(self, root: Path, base: Path):
        self._state_file = root / "state" / "base_packages"

        layer_dirs = [
            root / "base_packages",
            root / "base_pkglist",
            base,
        ]

        self._base_package_layers = _Layers(layer_dirs=layer_dirs)
        self._base_pkglist_layers = _Layers(layer_dirs=layer_dirs[1:])
        self._combined_package_layers = _Layers(layer_dirs=layer_dirs[0:2])

    @property
    def base_package_layers(self) -> _Layers:
        return self._base_package_layers

    @property
    def base_pkglist_layers(self) -> _Layers:
        return self._base_pkglist_layers

    @property
    def combined_package_layers(self) -> _Layers:
        return self._combined_package_layers

    def has_state(self) -> bool:
        return self._state_file.is_file()

    def load_state(self) -> Optional[LayerState]:
        state_data, _ = load_global_state(self._state_file)
        return cast(LayerState, state_data)

    def write_state(self, *, base_packages: List[str]) -> None:
        # TODO: add something to identify the base layer?
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        state = LayerState(base_packages=set(base_packages))
        state.write(self._state_file)

    def clean_state(self) -> None:
        self._state_file.unlink(missing_ok=True)


class Overlay:
    def __init__(self, layers: _Layers):
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

        result = chroot.run(
            self._layers.mountpoint,
            packages.Repository.install_build_packages,
            package_list,
        )

        if result and isinstance(result, list):
            installed_packages = result

        return installed_packages

    def export_overlay(self, dest: Path) -> None:
        if not os.path.ismount(self._layers.mountpoint):
            raise errors.ExportOverlayError(f"{self._layers.mountpoint} is not mounted")

        shutil.copytree(self._layers.mountpoint, dest)
