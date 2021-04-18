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

import copy
from typing import TYPE_CHECKING, Dict, Type

from craft_parts import errors

from .autotools_plugin import AutotoolsPlugin
from .base import Plugin
from .dump_plugin import DumpPlugin
from .make_plugin import MakePlugin
from .nil_plugin import NilPlugin
from .properties import PluginProperties

if TYPE_CHECKING:
    from craft_parts.infos import PartInfo
    from craft_parts.parts import Part


PluginType = Type[Plugin]


# Plugin registry by plugin API version
_BUILTIN_PLUGINS: Dict[str, PluginType] = {
    "autotools": AutotoolsPlugin,
    "dump": DumpPlugin,
    "make": MakePlugin,
    "nil": NilPlugin,
}

_PLUGINS = copy.deepcopy(_BUILTIN_PLUGINS)


def get_plugin(
    *,
    part: "Part",
    part_info: "PartInfo",
    properties: PluginProperties,  # = None,
) -> Plugin:
    """Obtain a plugin instance for the specified part."""

    plugin_name = part.plugin if part.plugin else part.name
    plugin_class = get_plugin_class(plugin_name)
    # plugin_schema = validator.merge_schema(plugin_class.get_schema())
    # options = PluginOptions(properties=part.properties, schema=plugin_schema)

    return plugin_class(options=properties, part_info=part_info)


def get_plugin_class(name: str) -> PluginType:
    """Obtain a plugin class given the name and plugin API version."""

    if name not in _PLUGINS:
        raise errors.InvalidPlugin(name)

    return _PLUGINS[name]


def register(plugins: Dict[str, PluginType]) -> None:
    """Register part handler plugins.

    :param plugins: a dictionary where the keys are plugin names and
        values are plugin classes. Valid plugins must extend the base
        class defined for each plugin API version.
    :param version: the plugin API version. Defaults to "v2".
    """

    _PLUGINS.update(plugins)


def unregister_all() -> None:
    """Unregister all user-registered plugins."""
    global _PLUGINS  # pylint: disable=global-statement
    _PLUGINS = copy.deepcopy(_BUILTIN_PLUGINS)
