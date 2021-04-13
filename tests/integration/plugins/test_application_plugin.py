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

import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Set

import pytest
import yaml

import craft_parts
from craft_parts import Action, ActionType, Step, errors, plugins


@dataclass(frozen=True)
class ApplicationPluginProperties(plugins.PluginV2Properties):
    stuff: List[str]

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        return cls(stuff=data.pop("stuff", []))


class ApplicationPlugin(plugins.PluginV2):
    """Our application plugin."""

    properties_class = ApplicationPluginProperties

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "stuff": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {"type": "string"},
                    "default": [],
                },
            },
            "required": ["source", "stuff"],
        }

    def get_build_snaps(self) -> Set[str]:
        return {"build_snap"}

    def get_build_packages(self) -> Set[str]:
        return {"build_package"}

    def get_build_environment(self) -> Dict[str, str]:
        return {"CRAFT_PARTS_CUSTOM_TEST": "application plugin"}

    def get_build_commands(self) -> List[str]:
        return ["echo hello ${CRAFT_PARTS_CUSTOM_TEST}"]


def setup_function():
    plugins.unregister_all()


@pytest.mark.usefixtures("new_dir")
def test_application_plugin_happy(capfd, mocker):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: test
            source: .
            stuff:
            - first
            - second
            - third
        """
    )

    # register our application plugin
    plugins.register({"test": ApplicationPlugin})

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(parts, application_name="test_application_plugin")

    # plugins act on the build step
    actions = lf.plan(Step.BUILD)
    assert actions == [
        Action("foo", Step.PULL, action_type=ActionType.RUN),
        Action("foo", Step.BUILD, action_type=ActionType.RUN),
    ]

    mock_install_build_packages = mocker.patch(
        "craft_parts.packages.Repository.install_build_packages"
    )

    mock_install_build_snaps = mocker.patch("craft_parts.packages.snaps.install_snaps")

    with lf.action_executor() as exe:
        exe.execute(actions[1])

    out, _ = capfd.readouterr()
    assert out == "hello application plugin\n"

    mock_install_build_packages.assert_called_once_with(["build_package"])
    mock_install_build_snaps.assert_called_once_with({"build_snap"})


@pytest.mark.skip("schema validation not implemented")
def test_application_plugin_miss_stuff():
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: test
            source: .
        """
    )

    # register our application plugin
    plugins.register({"test": ApplicationPlugin})

    parts = yaml.safe_load(_parts_yaml)

    with pytest.raises(errors.SchemaValidationError) as raised:
        craft_parts.LifecycleManager(parts, application_name="test_application_plugin")
    assert (
        str(raised.value) == "Schema validation error: 'stuff' is a required property"
    )


@pytest.mark.skip("schema validation not implemented")
def test_application_plugin_schema_error():
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: test
            source: .
            stuff: "some stuff"
        """
    )

    # register our application plugin
    plugins.register({"test": ApplicationPlugin})

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(parts, application_name="test_application_plugin")

    with pytest.raises(errors.SchemaValidationError) as raised:
        lf.plan(Step.BUILD)
    assert str(raised.value) == (
        "Schema validation error: The 'stuff' property does not match the required "
        "schema: 'some stuff' is not of type 'array'"
    )


def test_application_plugin_not_registered():
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: test
            source: .
        """
    )

    # don't register our application plugin
    parts = yaml.safe_load(_parts_yaml)

    with pytest.raises(errors.InvalidPlugin) as raised:
        craft_parts.LifecycleManager(parts, application_name="test_application_plugin")

    assert str(raised.value) == "A plugin named 'test' is not registered."
