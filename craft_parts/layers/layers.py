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

"""Define a set of layers to be used by an overlay filesystem."""

import abc
import contextlib
import logging
import os
import shutil
from pathlib import Path
from typing import List

from craft_parts import errors

from .overlayfs import OverlayFS

logger = logging.getLogger(__name__)


class Layers(abc.ABC):
    """The set of layers used by an overlay filesystem."""

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
        """Where the overlay filesystem is mounted."""
        return self._mountpoint

    @property
    def upper_dir(self) -> Path:
        """Where the upper dir of this layer set is located."""
        return self._upper_dir

    def mount(self) -> None:
        """Mount this layer set as an overlay filesystem."""
        self._overlayfs.mount()

    def unmount(self) -> None:
        """Unmount the overlay filesystem."""
        self._overlayfs.unmount()

    def mkdirs(self) -> None:
        """Create the directories for the layers in this layer set."""
        self._upper_dir.mkdir(parents=True, exist_ok=True)
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._mountpoint.mkdir(parents=True, exist_ok=True)

        for ldir in self._lower_dirs:
            ldir.mkdir(parents=True, exist_ok=True)

    def clean(self):
        """Remove all the files from the layers in this layer set."""
        if os.path.ismount(self._mountpoint):
            raise errors.CleanLayerError(f"{self._mountpoint} is mounted")

        for directory in [self._upper_dir, self._work_dir]:
            if directory:
                with contextlib.suppress(FileNotFoundError):
                    shutil.rmtree(directory)

        self.mkdirs()
