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
import os.path
import subprocess
import sys
from pathlib import Path
from typing import Callable, Union

from craft_parts.utils import os_utils

logger = logging.getLogger(__name__)


_BINDS = ["/sys", "/proc", "/etc/resolv.conf", "/dev"]


def chroot_run(root: Union[str, Path], func: Callable, *args, **kwargs) -> None:
    _prepare_root(root)
    try:
        pid = os.fork()
        if pid == 0:
             logger.debug(f"[{os.getpid()}] chroot to {root!r}")
             os.chroot(root)
             os.chdir("/")
             func(*args, **kwargs)
             sys.exit()
        os.waitpid(pid, 0)
    finally:
        _clean_root(root)


def _prepare_root(root: str) -> None:
    for entry in _BINDS:
        mountpoint = os.path.join(root, os.path.relpath(entry, "/"))
        print("===1", entry, mountpoint)
        _create_mountpoint(entry, mountpoint)
        print("===2", entry, mountpoint)
        os_utils.mount(entry, mountpoint, "--bind")
        print("===3", entry, mountpoint)

    os_utils.mount(
        "tmpfs", os.path.join(root, "dev/shm"), "-ttmpfs", "-orw,nosuid,nodev"
    )


def _clean_root(root: str) -> None:
    with contextlib.suppress(subprocess.CalledProcessError):
        os_utils.umount(os.path.join(root, "dev/shm"))

    for entry in reversed(_BINDS):
        with contextlib.suppress(subprocess.CalledProcessError):
            mountpoint = os.path.join(root, os.path.relpath(entry, "/"))
            os_utils.umount(mountpoint)
            _clean_mountpoint(entry, mountpoint)


def _create_mountpoint(entry: str, mountpoint: str) -> None:
    if not os.path.isdir(entry):
        if os.path.islink(mountpoint):
            os.unlink(mountpoint)
        os.makedirs(os.path.dirname(mountpoint), exist_ok=True)
        open(mountpoint, "a").close()
    else:
        os.makedirs(mountpoint, exist_ok=True)


def _clean_mountpoint(entry: str, mountpoint: str) -> None:
    if not os.path.exists(mountpoint):
        return

    if not os.path.isdir(entry):
        os.unlink(mountpoint)
