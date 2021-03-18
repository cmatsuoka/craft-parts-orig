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
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Union

from craft_parts.utils import os_utils

logger = logging.getLogger(__name__)


_BINDS = ["/sys", "/proc", "/dev"]


def run(root: Union[str, Path], func: Callable, *args, **kwargs) -> None:
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


def created_files() -> List[str]:
    return ["/etc/resolv.conf"]


def _install_file(name: str, root: str):
    dest_name = os.path.join(root, os.path.relpath(name, "/"))
    if os.path.islink(dest_name):
        os.unlink(dest_name)
    shutil.copyfile(name, dest_name)


def _prepare_root(root: str) -> None:
    for entry in _BINDS:
        mountpoint = os.path.join(root, os.path.relpath(entry, "/"))
        os.makedirs(mountpoint, exist_ok=True)
        os_utils.mount(entry, mountpoint, "--bind")

    _install_file("/etc/resolv.conf", root=root)

    os_utils.mount(
        "tmpfs", os.path.join(root, "dev/shm"), "-ttmpfs", "-orw,nosuid,nodev"
    )


def _clean_root(root: str) -> None:
    with contextlib.suppress(subprocess.CalledProcessError):
        os_utils.umount(os.path.join(root, "dev/shm"))

    os.unlink(os.path.join(root, "etc/resolv.conf"))

    for entry in reversed(_BINDS):
        with contextlib.suppress(subprocess.CalledProcessError):
            mountpoint = os.path.join(root, os.path.relpath(entry, "/"))
            os_utils.umount(mountpoint)
