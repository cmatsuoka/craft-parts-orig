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

import json
from typing import Any, Dict

import jsonschema  # type: ignore

from craft_parts import errors


class Validator:
    """Parts schema validator."""

    def __init__(self, schema: str):
        self._load_schema(schema)

    @property
    def schema(self):
        """Return all schema properties."""

        return self._schema["properties"].copy()

    @property
    def part_schema(self):
        """Return part-specific schema properties."""

        sub = self.schema["parts"]["patternProperties"]
        properties = sub["^(?!plugins$)[a-z0-9][a-z0-9+-]*$"]["properties"]
        return properties

    @property
    def definitions_schema(self):
        """Return sub-schema that describes definitions used within schema."""

        return self._schema["definitions"].copy()

    def _load_schema(self, schema: str):
        try:
            with open(schema) as schema_file:
                self._schema = json.load(schema_file)
        except FileNotFoundError:
            raise errors.SchemaValidation(
                "schema validation file is missing from installation path"
            )

    def validate(self, data: Dict[str, Any]) -> None:
        format_check = jsonschema.FormatChecker()
        try:
            jsonschema.validate(data, self._schema, format_checker=format_check)
        except jsonschema.ValidationError as err:
            raise errors.SchemaValidation.from_validation_error(err)
