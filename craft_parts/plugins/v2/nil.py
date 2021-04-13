# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2020 Canonical Ltd
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

"""The nil plugin.

Using this, parts can be defined purely by utilizing properties that are
automatically included, e.g. stage-packages.
"""

from typing import Any, Dict, List, Set

from ..plugin_v2 import PluginV2, PluginV2Properties


class NilPluginProperties(PluginV2Properties):
    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        return cls()


class NilPlugin(PluginV2):
    """The nil plugin, useful for parts with no source."""

    properties_class = NilPluginProperties

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        }

    def get_build_snaps(self) -> Set[str]:
        return set()

    def get_build_packages(self) -> Set[str]:
        return set()

    def get_build_environment(self) -> Dict[str, str]:
        return dict()

    def get_build_commands(self) -> List[str]:
        return list()
