# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016-2017 Canonical Ltd
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

"""State definitions for the prime state."""

from typing import Any, Dict

from .part_state import PartState


class PrimeState(PartState):
    """Hold context information for the prime step."""

    yaml_tag = "!PrimeState"

    def __init__(
        self,
        *,
        files,
        directories,
        dependency_paths=None,
        part_properties: Dict[str, Any] = None,
        project_options: Dict[str, Any] = None,
        primed_stage_packages=None,
    ):
        super().__init__(
            part_properties=part_properties,
            project_options=project_options,
            files=files,
            directories=directories,
        )

        self.dependency_paths = set()
        self.primed_stage_packages = primed_stage_packages
        if self.primed_stage_packages is None:
            self.primed_stage_packages = set()

        if dependency_paths:
            self.dependency_paths = dependency_paths

    def properties_of_interest(self, part_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the properties concerning this step from part_properties.

        The properties of interest to the prime step are the `prime` keyword
        used to filter out files with an allow or deny, and the override-prime
        scriptlet (if defined).
        """

        return {
            "override-prime": part_properties.get("override-prime"),
            "prime": part_properties.get("prime", ["*"]) or ["*"],
        }

    def project_options_of_interest(
        self, project_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract the options concerning this step from the project.

        The prime step doesn't care about any project options.
        """

        return {}
