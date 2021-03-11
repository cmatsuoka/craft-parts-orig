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
from typing import Dict, Type, Union

from craft_parts import errors
from craft_parts.infos import PartInfo
from craft_parts.parts import Part
from craft_parts.schemas import Validator

from . import v2
from .options import PluginOptions
from .plugin_v2 import PluginV2

Plugin = Union[PluginV2]
PluginType = Type[Plugin]


# Plugin registry by plugin API version
_BUILTIN_PLUGINS: Dict[str, Dict[str, PluginType]] = {
    "v2": {
        "autotools": v2.AutotoolsPlugin,
        "dump": v2.DumpPlugin,
        "make": v2.MakePlugin,
        "nil": v2.NilPlugin,
    }
}

_PLUGINS = copy.deepcopy(_BUILTIN_PLUGINS)


def get_plugin(
    *, part: Part, plugin_version: str, validator: Validator, part_info: PartInfo
) -> Plugin:
    """Obtain a plugin instance for the specified part."""

    plugin_class = _get_plugin_class(part=part, version=plugin_version)
    plugin_schema = validator.merge_schema(plugin_class.get_schema())
    options = PluginOptions(properties=part.properties, schema=plugin_schema)

    return plugin_class(options=options, part_info=part_info)


def _get_plugin_class(*, part: Part, version: str) -> PluginType:
    """Obtain a plugin class given the name and plugin API version."""

    plugin_name = part.plugin if part.plugin else part.name
    if version not in _PLUGINS:
        raise errors.InvalidPluginAPIVersion(version)

    if plugin_name not in _PLUGINS[version]:
        if not part.plugin:
            raise errors.UndefinedPlugin(part.name)

        raise errors.InvalidPlugin(part.plugin)

    return _PLUGINS[version][plugin_name]


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


def unregister_all() -> None:
    """Unregister all user-registered plugins."""
    global _PLUGINS  # pylint: disable=global-statement
    _PLUGINS = copy.deepcopy(_BUILTIN_PLUGINS)
