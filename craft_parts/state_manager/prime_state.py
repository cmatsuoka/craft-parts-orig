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

from typing import Any, Dict, Optional, Set

from .part_state import PartState


class PrimeState(PartState):
    """Hold context information for the prime step."""

    dependency_paths: Optional[Set[str]] = set()
    primed_stage_packages: Optional[Set[str]] = set()

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "PrimeState":
        return cls(**data)

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
