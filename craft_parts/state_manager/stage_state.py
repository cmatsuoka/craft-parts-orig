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

"""State definitions for the stage step."""

from typing import Any, Dict

from .part_state import PartState


class StageState(PartState):
    yaml_tag = "!StageState"

    def __init__(
        self,
        *,
        files,
        directories,
        part_properties=None,
    ):
        super().__init__(
            part_properties=part_properties, files=files, directories=directories
        )

    def properties_of_interest(self, part_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the properties concerning this step from part_properties.

        The only property of interest to the stage step is the `stage` keyword
        used to filter out files with a white or blacklist.
        """

        return {
            "filesets": part_properties.get("filesets", {}) or {},
            "override-stage": part_properties.get("override-stage"),
            "stage": part_properties.get("stage", ["*"]) or ["*"],
        }

    def project_options_of_interest(
        self, project_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract the options concerning this step from the project.

        The stage step doesn't care about any project options.
        """

        return {}
