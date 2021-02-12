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

from __future__ import annotations

import copy
import logging
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from craft_parts import errors, utils
from craft_parts.parts import Part
from craft_parts.steps import Step

logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class StepInfo:
    """All the information needed by part handlers."""

    def __init__(
        self,
        *,
        application_name: str = utils.package_name(),
        target_arch: str = "",
        parallel_build_count: int = 1,
        local_plugins_dir: Optional[Union[Path, str]] = None,
        **custom_args,  # custom passthrough args
    ):
        self._application_name = application_name
        self._set_machine(target_arch)

        self._parallel_build_count = parallel_build_count

        if not local_plugins_dir:
            self._local_plugins_dir = None
        elif isinstance(local_plugins_dir, Path):
            self._local_plugins_dir = local_plugins_dir
        else:
            self._local_plugins_dir = Path(local_plugins_dir)

        # Attributes set before step execution
        self.step: Optional[Step] = None
        self.part_src_dir = Path()
        self.part_src_work_dir = Path()
        self.part_build_dir = Path()
        self.part_build_work_dir = Path()
        self.part_install_dir = Path()
        self.part_state_dir = Path()
        self.stage_dir = Path()
        self.prime_dir = Path()
        self._custom_args: List[str] = []

        for key, value in custom_args.items():
            self._custom_args.append(key)
            setattr(self, key, value)

    @property
    def application_name(self) -> str:
        """The name of the application using craft-parts."""
        return self._application_name

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
    def local_plugins_dir(self) -> Optional[Path]:
        """The location of local plugins in the filesystem."""
        return self._local_plugins_dir

    @property
    def deb_arch(self) -> str:
        """The architecture used for deb packages."""
        return self.__machine_info["deb"]

    def for_part(self, part: Part) -> StepInfo:
        """Return a copy of this object adding part-specific fields.

        :param part: the part containing the information to add.
        """

        info = copy.deepcopy(self)
        info.part_src_dir = part.part_src_dir
        info.part_src_work_dir = part.part_src_work_dir
        info.part_build_dir = part.part_build_dir
        info.part_build_work_dir = part.part_build_work_dir
        info.part_install_dir = part.part_install_dir
        info.part_state_dir = part.part_state_dir
        info.stage_dir = part.stage_dir
        info.prime_dir = part.prime_dir

        return info

    def for_step(self, step: Step) -> StepInfo:
        """Return a copy of this object adding step-specific fields.

        :param step: the step information to add.
        """

        info = copy.deepcopy(self)
        info.step = step

        return info

    def _set_machine(self, target_arch):
        self.__platform_arch = _get_platform_architecture()
        if not target_arch:
            target_arch = self.__platform_arch
            logger.info("Setting target machine to %s", target_arch)

        machine = _ARCH_TRANSLATIONS.get(target_arch, None)
        if not machine:
            raise errors.InvalidArchitecture(target_arch)

        self.__target_machine = target_arch
        self.__machine_info = machine


def options_from_step_info(step_info: StepInfo) -> Dict[str, Any]:
    """Obtain project-wide options from the given step info."""

    options = {
        "application_name": step_info.application_name,
        "arch_triplet": step_info.arch_triplet,
        "deb_arch": step_info.deb_arch,
    }

    return options


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
