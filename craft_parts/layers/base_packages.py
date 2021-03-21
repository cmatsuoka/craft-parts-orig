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
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Set, cast

from craft_parts import errors, packages
from craft_parts.state_manager import GlobalState, load_global_state

from . import chroot
from .layers import Layers

logger = logging.getLogger(__name__)


class BasePackagesLayerState(GlobalState):
    """Context data for the base package layer."""

    yaml_tag = "!BasePackageLayerState"

    def __init__(self, *, base_packages: Set[str] = None):
        if not base_packages:
            base_packages = set()

        self.base_packages = base_packages


class BasePackagesLayerStack:
    """The filesystem layers used to modify the base image with base package."""

    def __init__(self, root: Path, base: Path):
        self._state_file = root / "state" / "base_packages"

        layer_dirs = [
            root / "base_packages",
            root / "base_pkglist",
            base,
        ]

        self._base_packages_layers = Layers(layer_dirs=layer_dirs)
        self._base_pkglist_layers = Layers(layer_dirs=layer_dirs[1:])
        self._combined_package_layers = Layers(layer_dirs=layer_dirs[0:2])

    @property
    def package_layers(self) -> Layers:
        return self._base_packages_layers

    @property
    def pkglist_layers(self) -> Layers:
        return self._base_pkglist_layers

    @property
    def combined_layers(self) -> Layers:
        return self._combined_package_layers

    def has_state(self) -> bool:
        return self._state_file.is_file()

    def load_state(self) -> Optional[BasePackagesLayerState]:
        state_data, _ = load_global_state(self._state_file)
        return cast(BasePackagesLayerState, state_data)

    def write_state(self, *, base_packages: List[str]) -> None:
        # TODO: add something to identify the base layer?
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        state = BasePackagesLayerState(base_packages=set(base_packages))
        state.write(self._state_file)

    def clean_state(self) -> None:
        self._state_file.unlink(missing_ok=True)


class BasePackagesOverlay:
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
