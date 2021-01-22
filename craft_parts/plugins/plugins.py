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

"""Definitions and helpers to handle plugins."""

from typing import Dict, Type, Union

from craft_parts import errors

from . import v2
from .plugin_v2 import PluginV2

Plugin = Union[PluginV2]
PluginType = Type[Plugin]


# Plugin registry by plugin API version
_PLUGINS: Dict[str, Dict[str, PluginType]] = {
    "v2": {"nil": v2.NilPlugin, "dump": v2.DumpPlugin}
}


def get_plugin(name: str, *, version: str) -> PluginType:
    """Obtain a plugin class given the name and plugin API version."""

    if version not in _PLUGINS:
        raise errors.UnknownPluginVersion(version)

    if name not in _PLUGINS[version]:
        raise errors.UnknownPlugin(name)

    return _PLUGINS[version][name]


def register_plugin(plugins: Dict[str, PluginType], *, version: str) -> None:
    """Register part handler plugins."""

    if version not in _PLUGINS:
        raise errors.UnknownPluginVersion(version)

    _PLUGINS[version].update(plugins)
