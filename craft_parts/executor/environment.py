# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2020-2021 Canonical Ltd
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

"""Helpers to handle part environment setting."""

import logging
from typing import Dict

from craft_parts.parts import Part
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step
from craft_parts.utils import formatting_utils, os_utils

logger = logging.getLogger(__name__)


def get_part_environment(
    part: Part, step: Step, *, step_info: StepInfo
) -> Dict[str, str]:
    """Return the built-in part environment."""

    part_environment: Dict[str, str] = dict()
    paths = [part.part_install_dir, part.stage_dir]

    bin_paths = list()
    for path in paths:
        bin_paths.extend(os_utils.get_bin_paths(root=path, existing_only=True))

    if bin_paths:
        bin_paths.append("$PATH")
        part_environment["PATH"] = formatting_utils.combine_paths(
            paths=bin_paths, prepend="", separator=":"
        )

    include_paths = list()
    for path in paths:
        include_paths.extend(
            os_utils.get_include_paths(root=path, arch_triplet=step_info.arch_triplet)
        )

    if include_paths:
        for envvar in ["CPPFLAGS", "CFLAGS", "CXXFLAGS"]:
            part_environment[envvar] = formatting_utils.combine_paths(
                paths=include_paths, prepend="-isystem", separator=" "
            )

    library_paths = list()
    for path in paths:
        library_paths.extend(
            os_utils.get_library_paths(root=path, arch_triplet=step_info.arch_triplet)
        )

    if library_paths:
        part_environment["LDFLAGS"] = formatting_utils.combine_paths(
            paths=library_paths, prepend="-L", separator=" "
        )

    pkg_config_paths = list()
    for path in paths:
        pkg_config_paths.extend(
            os_utils.get_pkg_config_paths(
                root=path, arch_triplet=step_info.arch_triplet
            )
        )

    if pkg_config_paths:
        part_environment["PKG_CONFIG_PATH"] = formatting_utils.combine_paths(
            pkg_config_paths, prepend="", separator=":"
        )

    return part_environment
