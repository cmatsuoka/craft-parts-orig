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

"""State definitions for the pull step."""

from typing import Any, Dict

from .part_state import PartState


class PullState(PartState):
    """Hold context information for the pull step."""

    assets: Dict[str, Any] = {}

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "PullState":
        return cls(**data)

    def properties_of_interest(self, part_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Return relevant properties concerning this step."""

        relevant_properties = [
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
            "stage-packages",
        ]

        properties: Dict[str, Any] = {}
        for name in relevant_properties:
            properties[name] = part_properties.get(name)

        return properties

    def project_options_of_interest(
        self, project_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract the options concerning this step from the project.

        The pull step only cares about the target architecture.
        """

        return {"target_arch": project_options.get("target_arch")}
