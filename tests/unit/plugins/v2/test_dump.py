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

from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.v2 import DumpPlugin

# pylint: disable=attribute-defined-outside-init


class TestPluginDump:
    """Dump plugin tests."""

    def setup_method(self):
        options = DumpPlugin.get_properties_class().unmarshal({"source": "of all evil"})

        project_info = ProjectInfo()

        part = Part("foo", {})
        part_info = PartInfo(project_info=project_info, part=part)
        part_info._part_install_dir = Path("install/dir")

        self._plugin = DumpPlugin(options=options, part_info=part_info)

    @pytest.mark.skip("schema validation not implemented")
    def test_schema(self):
        schema = DumpPlugin.get_schema()
        assert schema["$schema"] == "http://json-schema.org/draft-04/schema#"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert schema["properties"] == {}

        with pytest.raises(errors.SchemaValidationError) as raised:
            DumpPlugin.get_properties_class().unmarshal({})
        assert (
            str(raised.value) == "Schema validation error: 'source' "
            "is a required property"
        )

        with pytest.raises(errors.SchemaValidationError) as raised:
            DumpPlugin.get_properties_class().unmarshal({"invalid": True})
        assert (
            str(raised.value) == "Schema validation error: Additional properties "
            "are not allowed ('invalid' was unexpected)"
        )

    def test_get_build_packages(self):
        assert self._plugin.get_build_packages() == set()
        assert self._plugin.get_build_snaps() == set()

    def test_get_build_environment(self):
        assert self._plugin.get_build_environment() == dict()

    def test_get_build_commands(self):
        assert self._plugin.get_build_commands() == [
            'cp --archive --link --no-dereference . "install/dir"'
        ]
