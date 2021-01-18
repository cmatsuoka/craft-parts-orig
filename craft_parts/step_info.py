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

"""Definitions for the step information used by part handlers."""

import logging
import os
import platform

from craft_parts import errors

logger = logging.getLogger(__name__)


class StepInfo:
    """All the information needed by part handlers."""

    def __init__(
        self,
        *,
        work_dir: str,
        target_arch: str,
        platform_id: str,
        platform_version_id: str,
        parallel_build_count: int,
        local_plugins_dir: str,
        **custom_args,  # custom passthrough args
    ):
        self._set_machine(target_arch)

        self._parallel_build_count = parallel_build_count
        self._local_plugins_dir = local_plugins_dir

        self.part = ""  # part name to be filled by the part handler
        self.step = ""  # step name to be filled by the part handler

        if not work_dir:
            work_dir = os.getcwd()

        self.work_dir = work_dir
        self.parts_dir = os.path.join(work_dir, "parts")
        self.stage_dir = os.path.join(work_dir, "stage")
        self.prime_dir = os.path.join(work_dir, "prime")

        for key, value in custom_args.items():
            setattr(self, key, value)

    @property
    def arch_triplet(self) -> str:
        """The machine-vendor-os platform triplet definition."""

        return self.__machine_info["triplet"]

    @property
    def is_cross_compiling(self) -> bool:
        """Whether the target and host architectures are different."""

        return self.__target_machine != self.__platform_arch

    @property
    def parallel_build_count(self) -> int:
        """The maximum allowable number of concurrent build jobs."""

        return self._parallel_build_count

    @property
    def local_plugins_dir(self) -> str:
        """The location of local plugins in the filesystem."""

        return self._local_plugins_dir

    @property
    def deb_arch(self) -> str:
        """The architecture used for deb packages."""

        return self.__machine_info["deb"]

    def _set_machine(self, target_arch):
        self.__platform_arch = _get_platform_architecture()
        if not target_arch:
            self.__target_machine = self.__platform_arch
        else:
            self.__target_machine = _find_machine(target_arch)
            logger.info("Setting target machine to %s", target_arch)
        self.__machine_info = _ARCH_TRANSLATIONS[self.__target_machine]


def _find_machine(target_arch):
    machine = _ARCH_TRANSLATIONS.get(target_arch, None)
    if not machine:
        raise errors.InvalidArchitecture(target_arch)
    return machine


def _get_platform_architecture() -> str:
    # TODO: handle Windows architectures
    return platform.machine()


_ARCH_TRANSLATIONS = {
    "aarch64": {
        "kernel": "arm64",
        "deb": "arm64",
        "uts_machine": "aarch64",
        "cross-compiler-prefix": "aarch64-linux-gnu-",
        "cross-build-packages": ["gcc-aarch64-linux-gnu", "libc6-dev-arm64-cross"],
        "triplet": "aarch64-linux-gnu",
        "core-dynamic-linker": "lib/ld-linux-aarch64.so.1",
    },
    "armv7l": {
        "kernel": "arm",
        "deb": "armhf",
        "uts_machine": "arm",
        "cross-compiler-prefix": "arm-linux-gnueabihf-",
        "cross-build-packages": ["gcc-arm-linux-gnueabihf", "libc6-dev-armhf-cross"],
        "triplet": "arm-linux-gnueabihf",
        "core-dynamic-linker": "lib/ld-linux-armhf.so.3",
    },
    "i686": {
        "kernel": "x86",
        "deb": "i386",
        "uts_machine": "i686",
        "triplet": "i386-linux-gnu",
    },
    "ppc": {
        "kernel": "powerpc",
        "deb": "powerpc",
        "uts_machine": "powerpc",
        "cross-compiler-prefix": "powerpc-linux-gnu-",
        "cross-build-packages": ["gcc-powerpc-linux-gnu", "libc6-dev-powerpc-cross"],
        "triplet": "powerpc-linux-gnu",
    },
    "ppc64le": {
        "kernel": "powerpc",
        "deb": "ppc64el",
        "uts_machine": "ppc64el",
        "cross-compiler-prefix": "powerpc64le-linux-gnu-",
        "cross-build-packages": [
            "gcc-powerpc64le-linux-gnu",
            "libc6-dev-ppc64el-cross",
        ],
        "triplet": "powerpc64le-linux-gnu",
        "core-dynamic-linker": "lib64/ld64.so.2",
    },
    "riscv64": {
        "kernel": "riscv64",
        "deb": "riscv64",
        "uts_machine": "riscv64",
        "cross-compiler-prefix": "riscv64-linux-gnu-",
        "cross-build-packages": ["gcc-riscv64-linux-gnu", "libc6-dev-riscv64-cross"],
        "triplet": "riscv64-linux-gnu",
        "core-dynamic-linker": "lib/ld-linux-riscv64-lp64d.so.1",
    },
    "s390x": {
        "kernel": "s390",
        "deb": "s390x",
        "uts_machine": "s390x",
        "cross-compiler-prefix": "s390x-linux-gnu-",
        "cross-build-packages": ["gcc-s390x-linux-gnu", "libc6-dev-s390x-cross"],
        "triplet": "s390x-linux-gnu",
        "core-dynamic-linker": "lib/ld64.so.1",
    },
    "x86_64": {
        "kernel": "x86",
        "deb": "amd64",
        "uts_machine": "x86_64",
        "triplet": "x86_64-linux-gnu",
        "core-dynamic-linker": "lib64/ld-linux-x86-64.so.2",
    },
}
