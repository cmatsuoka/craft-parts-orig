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
    "v2": {"nil": v2.NilPlugin, "dump": v2.DumpPlugin, "make": v2.MakePlugin}
}


def get_plugin(name: str, *, version: str) -> PluginType:
    """Obtain a plugin class given the name and plugin API version."""

    if version not in _PLUGINS:
        raise errors.InvalidPluginAPIVersion(version)

    if name not in _PLUGINS[version]:
        raise errors.InvalidPlugin(name)

    return _PLUGINS[version][name]


def register(plugins: Dict[str, PluginType], *, version: str = "v2") -> None:
    """Register part handler plugins.

    :param plugins: a dictionary where the keys are plugin names and
        values are plugin classes. Valid plugins must extend the base
        class defined for each plugin API version.
    :param version: the plugin API version. Defaults to "v2".
    """

    if version not in _PLUGINS:
        raise errors.InvalidPluginAPIVersion(version)

    _PLUGINS[version].update(plugins)
