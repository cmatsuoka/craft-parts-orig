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

"""Definitions and helpers for plugin options."""

from typing import Any, Dict

from craft_parts import schemas


# pylint: disable=too-few-public-methods
class PluginOptions:
    """Parameters to be passed to the plugin instance.

    :param properties: a dictionary containing option names and values. Options
        must conform to the plugin schema.
    :param schema: the plugin schema.
    """

    def __init__(self, *, properties: Dict[str, Any], schema: Dict[str, Any]):
        schema_properties = schema.get("properties", {})
        schemas.validate_schema(data=properties, schema=schema)

        for key in schema_properties:
            attr_name = key.replace("-", "_")
            default_value = schema_properties[key].get("default")
            attr_value = properties.get(key, default_value)
            setattr(self, attr_name, attr_value)
