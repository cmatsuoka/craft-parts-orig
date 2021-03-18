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

from pathlib import Path

import pytest

from craft_parts import errors, schemas
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins import plugins

_SCHEMA_DIR = Path(__file__).parents[3] / "craft_parts" / "data" / "schema"


@pytest.fixture
def validator() -> schemas.Validator:
    return schemas.Validator(_SCHEMA_DIR / "parts.json")


class TestGetPlugin:
    """Check plugin instantiation given the part and API version.

    The plugin is ordinarily selected using the `plugin` property defined
    in the part. If it's not defined, use the part name as a fallback.
    """

    def test_get_plugin_happy(self, validator):
        part = Part("foo", {"plugin": "nil"})
        project_info = ProjectInfo()
        part_info = PartInfo(project_info=project_info, part=part)

        plugin = plugins.get_plugin(
            part=part,
            plugin_version="v2",
            validator=validator,
            part_info=part_info,
        )

        assert isinstance(plugin, plugins.v2.NilPlugin)

    def test_get_plugin_fallback(self, validator):
        part = Part("nil", {})
        project_info = ProjectInfo()
        part_info = PartInfo(project_info=project_info, part=part)

        plugin = plugins.get_plugin(
            part=part,
            plugin_version="v2",
            validator=validator,
            part_info=part_info,
        )

        assert isinstance(plugin, plugins.v2.NilPlugin)

    def test_get_plugin_invalid(self, validator):
        part = Part("foo", {"plugin": "invalid"})
        project_info = ProjectInfo()
        part_info = PartInfo(project_info=project_info, part=part)

        with pytest.raises(errors.InvalidPlugin) as raised:
            plugins.get_plugin(
                part=part,
                plugin_version="v2",
                validator=validator,
                part_info=part_info,
            )

        assert str(raised.value) == "A plugin named 'invalid' is not registered."

    def test_get_plugin_undefined(self, validator):
        part = Part("foo", {})
        project_info = ProjectInfo()
        part_info = PartInfo(project_info=project_info, part=part)

        with pytest.raises(errors.UndefinedPlugin) as raised:
            plugins.get_plugin(
                part=part,
                plugin_version="v2",
                validator=validator,
                part_info=part_info,
            )

        assert str(raised.value) == "Plugin not defined for part 'foo'."