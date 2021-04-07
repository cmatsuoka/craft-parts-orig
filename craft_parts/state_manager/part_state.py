# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016-2021 Canonical Ltd
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

"""The part state for a given step."""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Set

from pydantic import Field
from pydantic_yaml import YamlModel  # type: ignore

from craft_parts.utils import yaml_utils


class _State(yaml_utils.YAMLObject):
    def __init__(self, yaml_data: Dict[str, Any] = None):
        if yaml_data:
            self.__dict__.update(yaml_data)

    def __repr__(self):
        items = sorted(self.__dict__.items())
        strings = (": ".join((key, repr(value))) for key, value in items)
        representation = ", ".join(strings)

        return "{}({})".format(self.__class__.__name__, representation)

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__

        return False

    def write(self, filepath: Path) -> None:
        """Write this state to disk."""

        os.makedirs(filepath.parent, exist_ok=True)
        with open(filepath, "w") as f:
            data = yaml_utils.dump(self)
            if data:
                f.write(data)


class GlobalState(_State):
    pass


class PartState(YamlModel, ABC):
    """The context used to run a step for a given part.

    The part state contains environmental and project-specific configuration
    data collected at step run time. If those properties are different in a
    new lifecycle execution the step will run again.
    """

    part_properties: Dict[str, Any] = Field({}, alias="properties")
    project_options: Dict[str, Any] = {}
    files: Set[str] = set()
    directories: Set[str] = set()

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True
        extra = "forbid"
        allow_mutation = False
        alias_generator = lambda s: s.replace("_", "-")  # noqa: E731
        allow_population_by_field_name = True

    @abstractmethod
    def properties_of_interest(self, part_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Return relevant properties concerning this step."""

    @abstractmethod
    def project_options_of_interest(
        self, project_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return relevant options concerning this step."""

    def diff_properties_of_interest(self, other_properties: Dict[str, Any]) -> Set[str]:
        """Return set of properties that differ."""

        return _get_differing_keys(
            self.properties_of_interest(self.part_properties),
            self.properties_of_interest(other_properties),
        )

    def diff_project_options_of_interest(
        self, other_project_options: Dict[str, Any]
    ) -> Set[str]:
        """Return set of project options that differ."""
        return _get_differing_keys(
            self.project_options_of_interest(self.project_options),
            self.project_options_of_interest(other_project_options),
        )

    def marshal(self) -> Dict[str, Any]:
        """Create a dictionary containing the part state data.

        :return: The newly created dictionary.

        """
        return self.dict(by_alias=True)

    def write(self, filepath: Path) -> None:
        """Write this state to disk."""

        os.makedirs(filepath.parent, exist_ok=True)
        yaml_data = self.yaml(by_alias=True)
        with open(filepath, "w") as f:
            f.write(yaml_data)


def _get_differing_keys(dict1, dict2) -> Set[str]:
    differing_keys = set()
    for key, dict1_value in dict1.items():
        dict2_value = dict2.get(key)
        if dict1_value != dict2_value:
            differing_keys.add(key)

    for key, dict2_value in dict2.items():
        dict1_value = dict1.get(key)
        if dict1_value != dict2_value:
            differing_keys.add(key)

    return differing_keys
