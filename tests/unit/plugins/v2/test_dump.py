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
from craft_parts.plugins.options import PluginOptions
from craft_parts.plugins.v2 import DumpPlugin
from craft_parts.step_info import StepInfo

_SCHEMA_DIR = Path(__file__).parents[4] / "craft_parts" / "data" / "schema"


# pylint: disable=attribute-defined-outside-init


class TestPluginDump:
    """Dump plugin tests."""

    def setup_class(self):
        validator = schemas.Validator(_SCHEMA_DIR / "parts.json")
        self._schema = validator.merge_schema(DumpPlugin.get_schema())

    def setup_method(self):
        options = PluginOptions(
            properties={"source": "of all evil"}, schema=self._schema
        )
        step_info = StepInfo()
        step_info.part_install_dir = Path("install/dir")
        self._plugin = DumpPlugin(part_name="foo", options=options, step_info=step_info)

    def test_schema(self):
        schema = DumpPlugin.get_schema()
        assert schema["$schema"] == "http://json-schema.org/draft-04/schema#"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert schema["properties"] == {}

        with pytest.raises(errors.SchemaValidation) as ei:
            PluginOptions(properties={}, schema=self._schema)
        assert (
            ei.value.get_brief()
            == "Schema validation error: 'source' is a required property"
        )

        with pytest.raises(errors.SchemaValidation) as ei:
            PluginOptions(properties={"invalid": True}, schema=schema)
        assert (
            ei.value.get_brief()
            == "Schema validation error: Additional properties are not allowed "
            "('invalid' was unexpected)"
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
