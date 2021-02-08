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
from craft_parts.plugins.v2 import AutotoolsPlugin
from craft_parts.step_info import StepInfo

_SCHEMA_DIR = Path(__file__).parents[4] / "craft_parts" / "data" / "schema"


# pylint: disable=attribute-defined-outside-init
# pylint: disable=line-too-long


class TestPluginAutotools:
    """Autotools plugin tests."""

    def setup_class(self):
        validator = schemas.Validator(_SCHEMA_DIR / "parts.json")
        self._schema = validator.merge_schema(AutotoolsPlugin.get_schema())

    def setup_method(self):
        options = PluginOptions(properties={}, schema=self._schema)
        step_info = StepInfo()
        step_info.part_install_dir = Path("install/dir")
        step_info._parallel_build_count = 42
        self._plugin = AutotoolsPlugin(
            part_name="foo", options=options, step_info=step_info
        )

    def test_schema(self):
        schema = AutotoolsPlugin.get_schema()
        assert schema["$schema"] == "http://json-schema.org/draft-04/schema#"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert schema["properties"] == {
            "autotools-configure-parameters": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string"},
                "default": [],
            }
        }

        with pytest.raises(errors.SchemaValidationError) as raised:
            PluginOptions(properties={"invalid": True}, schema=schema)
        assert (
            str(raised.value) == "Schema validation error: Additional properties "
            "are not allowed ('invalid' was unexpected)"
        )

    def test_get_build_packages(self):
        assert self._plugin.get_build_packages() == {
            "autoconf",
            "automake",
            "autopoint",
            "gcc",
            "libtool",
        }
        assert self._plugin.get_build_snaps() == set()

    def test_get_build_environment(self):
        assert self._plugin.get_build_environment() == dict()

    def test_get_build_commands(self):
        assert self._plugin.get_build_commands() == [
            "[ ! -f ./configure ] && [ -f ./autogen.sh ] && env NOCONFIGURE=1 ./autogen.sh",
            "[ ! -f ./configure ] && [ -f ./bootstrap ] && env NOCONFIGURE=1 ./bootstrap",
            "[ ! -f ./configure ] && autoreconf --install",
            "./configure",
            "make -j42",
            'make install DESTDIR="install/dir"',
        ]

    def test_get_build_commands_with_configure_parameters(self):
        options = PluginOptions(
            properties={
                "autotools-configure-parameters": ["--with-foo=true", "--prefix=/foo"]
            },
            schema=self._schema,
        )
        step_info = StepInfo()
        step_info.part_install_dir = Path("/tmp")
        step_info._parallel_build_count = 8
        plugin = AutotoolsPlugin(part_name="foo", options=options, step_info=step_info)

        assert plugin.get_build_commands() == [
            "[ ! -f ./configure ] && [ -f ./autogen.sh ] && env NOCONFIGURE=1 ./autogen.sh",
            "[ ! -f ./configure ] && [ -f ./bootstrap ] && env NOCONFIGURE=1 ./bootstrap",
            "[ ! -f ./configure ] && autoreconf --install",
            "./configure --with-foo=true --prefix=/foo",
            "make -j8",
            'make install DESTDIR="/tmp"',
        ]
