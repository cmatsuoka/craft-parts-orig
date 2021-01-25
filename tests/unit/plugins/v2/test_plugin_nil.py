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

import pytest

from craft_parts import errors
from craft_parts.plugins.options import PluginOptions
from craft_parts.plugins.v2 import NilPlugin


def test_plugin_nil():
    schema = NilPlugin.get_schema()
    options = PluginOptions(properties={}, schema=schema)
    p = NilPlugin(part_name="foo", options=options)
    assert p.get_build_snaps() == set()
    assert p.get_build_packages() == set()
    assert p.get_build_environment() == dict()
    assert p.get_build_commands() == []


def test_schema():
    schema = NilPlugin.get_schema()
    assert schema["additionalProperties"] is False

    with pytest.raises(errors.SchemaValidation) as ei:
        PluginOptions(properties={"invalid": True}, schema=schema)
    assert (
        ei.value.get_brief()
        == "Schema validation error: Additional properties are not allowed "
        "('invalid' was unexpected)"
    )
