# -*- Mode:Python; indent-tabs-buildnil; tab-width:4 -*-
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

"""State definitions for the pull step."""

from typing import Any, Dict, List

from .part_state import PartState


class PullState(PartState):
    """Hold context information for the pull step."""

    yaml_tag = "!PullState"

    def __init__(
        self,
        *,
        part_properties: Dict[str, Any] = None,
        project_options: Dict[str, Any] = None,
        stage_packages: List[str] = None,
        stage_snaps: List[str] = None,
        source_details=None,
    ):
        assets = {
            "stage-packages": stage_packages,
            "stage-snaps": stage_snaps,
            "source-details": source_details,
        }

        super().__init__(
            part_properties=part_properties,
            project_options=project_options,
            assets=assets,
        )

    def properties_of_interest(self, part_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the properties concerning this step from part_properties."""

        schema_properties = [
            "override-pull",
            "parse-info",
            "plugin",
            "source",
            "source-commit",
            "source-depth",
            "source-tag",
            "source-type",
            "source-branch",
            "source-subdir",
        ]

        properties: Dict[str, Any] = {}
        for name in schema_properties:
            properties[name] = part_properties.get(name)

        return properties

    def project_options_of_interest(
        self, project_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract the options concerning this step from the project.

        The pull step only cares about the target architecture.
        """

        return {"target_arch": project_options.get("target_arch")}
