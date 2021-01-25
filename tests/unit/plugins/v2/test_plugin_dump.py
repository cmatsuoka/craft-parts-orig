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

from pathlib import Path

import pytest

from craft_parts import errors, schemas
from craft_parts.plugins.options import PluginOptions
from craft_parts.plugins.v2 import DumpPlugin

_SCHEMA_DIR = Path(__file__).parents[4] / "craft_parts" / "data" / "schema"


class TestPluginDump:
    """Dump plugin tests."""

    def setup_class(self):
        validator = schemas.Validator(_SCHEMA_DIR / "parts.json")

        # pylint: disable=attribute-defined-outside-init
        self._schema = validator.merge_schema(DumpPlugin.get_schema())

    def test_plugin_nil(self):
        options = PluginOptions(
            properties={"source": "of all evil"}, schema=self._schema
        )
        p = DumpPlugin(part_name="foo", options=options)
        assert p.get_build_snaps() == set()
        assert p.get_build_packages() == set()
        assert p.get_build_environment() == dict()

    def test_schema(self):
        schema = DumpPlugin.get_schema()
        assert schema["additionalProperties"] is False

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
