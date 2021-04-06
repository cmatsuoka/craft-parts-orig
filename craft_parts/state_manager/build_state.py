# -*- Mode:Python; indent-tabs-buildnil; tab-width:4 -*-
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

"""State definitions for the build step."""

from typing import Any, Dict, Optional

from .part_state import PartState


class BuildState(PartState):
    """Hold context information for the build step."""

    #    assets = {
    #        "build-snaps": build_snaps,
    #        "build-packages": build_packages,
    #    }

    assets: Optional[Dict[str, Any]] = {}
    machine_assets: Optional[Dict[str, Any]] = {}

    # machine_assets: Optional[Dict[str, Any]] = None

    #    if machine_assets:
    #        assets.update(machine_assets)

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "BuildState":
        return cls(**data)

    def properties_of_interest(self, part_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the properties concerning this step from part_properties."""

        relevant_properties = [
            "after",
            "build-attributes",
            "build-packages",
            "disable-parallel",
            "organize",
            "override-build",
        ]

        properties: Dict[str, Any] = {}
        for name in relevant_properties:
            properties[name] = part_properties.get(name)

        return properties

    def project_options_of_interest(
        self, project_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract the options concerning this step from the project.

        The build step only cares about the target architecture.
        """

        return {"target_arch": project_options.get("target_arch")}
