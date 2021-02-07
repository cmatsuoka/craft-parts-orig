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

import contextlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from craft_parts.parts import Part
from craft_parts.steps import Step
from craft_parts.utils import file_utils, yaml_utils


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


class PartState(_State):
    """The context used to run a step for a given part."""

    def __init__(
        self,
        *,
        part_properties=None,
        project=None,
        data: Dict[str, Any] = None,
        files: Set[str] = None,
        directories: Set[str] = None
    ):
        if data:
            super().__init__(data)
            return

        super().__init__()

        self._files = files
        self._directories = directories
        self.timestamp: datetime = datetime.now()

        if not part_properties:
            part_properties = {}

        # TODO: handle this in a better way
        if part_properties:
            self.properties = self.properties_of_interest(part_properties)

        if project:
            self.project_options = self.project_options_of_interest(project)

    @property
    def files(self) -> Set[str]:
        return self._files if self._files else set()

    @property
    def directories(self) -> Set[str]:
        return self._directories if self._directories else set()

    def properties_of_interest(self, part_properties):
        """Extract the properties concerning this step from the options.

        Note that these options come from the YAML for a given part.
        """

        raise NotImplementedError

    def project_options_of_interest(self, project):
        """Extract the options concerning this step from the project."""

        raise NotImplementedError

    def diff_properties_of_interest(self, other_properties):
        """Return set of properties that differ."""

        return _get_differing_keys(
            self.properties, self.properties_of_interest(other_properties)
        )

    def diff_project_options_of_interest(self, other_project_options):
        """Return set of project options that differ."""

        return _get_differing_keys(
            self.project_options,
            self.project_options_of_interest(other_project_options),
        )

    def write(self, filepath: Path) -> None:
        """Write this state to disk."""

        os.makedirs(filepath.parent, exist_ok=True)
        with open(filepath, "w") as f:
            data = yaml_utils.dump(self.__dict__)
            if data:
                f.write(data)


def _get_differing_keys(dict1, dict2):
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


def load_state(part: Part, step: Step) -> Optional[PartState]:
    """Retrieve the persistent state for the given part and step."""

    state_data = {}
    filename = os.path.join(part.part_state_dir, step.name.lower())
    if not os.path.isfile(filename):
        return None

    with open(filename, "r") as state_file:
        data = yaml_utils.load(state_file)
        if data:
            state_data.update(data)

    state_data["timestamp"] = file_utils.timestamp(filename)
    return PartState(data=state_data)


def load_part_states(step: Step, part_list: List[Part]) -> Dict[str, PartState]:
    """Return a dictionary of the state of the given step for all parts."""

    states: Dict[str, PartState] = {}
    for part in part_list:
        state = load_state(part, step)
        if state:
            states[part.name] = state
    return states


def is_clean(part: Part, step: Step) -> bool:
    """Verify whether the persistent state for the given part and step is clean."""

    filename = os.path.join(part.part_state_dir, step.name.lower())
    return not os.path.isfile(filename)


def remove(part: Part, step: Step):
    """Remove the persistent state file for the given part and step."""
    with contextlib.suppress(FileNotFoundError):
        os.remove(part.part_state_dir / step.name.lower())
