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

"""Common helpers that can be used the sequencer or the executor."""

import logging
from typing import Any, Dict, List, Set

from craft_parts import packages, plugins, sources
from craft_parts.parts import Part
from craft_parts.plugins import Plugin
from craft_parts.utils import os_utils

logger = logging.getLogger(__name__)


def get_build_packages(*, part: Part, repository, plugin: Plugin) -> List[str]:
    """Obtain the list of build packages from part, source, and plugin."""

    all_packages: List[str] = []

    build_packages = part.build_packages
    if build_packages:
        logger.debug("part build packages: %s", build_packages)
        all_packages.extend(build_packages)

    source = part.source
    if source:
        source_type = sources.get_source_type_from_uri(source)
        source_build_packages = repository.get_packages_for_source_type(source_type)
        if source_build_packages:
            logger.debug("source build packages: %s", source_build_packages)
            all_packages.extend(source_build_packages)

    if isinstance(plugin, plugins.PluginV2):
        plugin_build_packages = plugin.get_build_packages()
        if plugin_build_packages:
            logger.debug("plugin build packages: %s", plugin_build_packages)
            all_packages.extend(plugin_build_packages)

    return all_packages


def get_machine_manifest() -> Dict[str, Any]:
    """Obtain information about the system OS and runtime environment."""

    return {
        "uname": os_utils.get_system_info(),
        "installed-packages": sorted(packages.Repository.get_installed_packages()),
        "installed-snaps": sorted(packages.snaps.get_installed_snaps()),
    }


def stage_packages_from_parts(part_list: List[Part]) -> List[str]:
    """Obtain the list of stage packages from all parts."""

    stage_packages: Set[str] = set()
    for part in part_list:
        part_stage_packages = part.stage_packages
        if part_stage_packages:
            stage_packages.update(part_stage_packages)

    return list(stage_packages)


def build_packages_from_parts(part_list: List[Part]) -> List[str]:
    """Obtain the list of build packages from all parts."""

    build_packages: Set[str] = set()
    for part in part_list:
        part_build_packages = part.build_packages
        if part_build_packages:
            build_packages.update(part_build_packages)

    return list(build_packages)
