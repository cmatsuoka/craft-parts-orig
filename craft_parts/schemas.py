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

"""Schema validation helpers and definitions."""

import json
from pathlib import Path
from typing import Any, Dict, Union

import jsonschema  # type: ignore

from craft_parts import errors


class Validator:
    """Parts schema validator."""

    def __init__(self, filename: Union[str, Path]):
        self._load_schema(filename)

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

    def _load_schema(self, filename: Union[str, Path]):
        try:
            with open(filename) as schema_file:
                self._schema = json.load(schema_file)
        except FileNotFoundError as err:
            raise errors.SchemaValidation(
                "schema validation file is missing from installation path"
            ) from err

    def validate(self, data: Dict[str, Any]) -> None:
        """Validate the given data against the validator's schema.

        :param data: the structured data to validate against the schema.
        """

        validate_schema(data=data, schema=self._schema)

    def merge_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Update the supplied schema with data from the validator schema.

        :param schema: the schema to update.

        :return: the updated schema.
        """

        schema = schema.copy()

        if "properties" not in schema:
            schema["properties"] = {}

        if "definitions" not in schema:
            schema["definitions"] = {}

        # The part schema takes precedence over the plugin's schema.
        schema["properties"].update(self.part_schema)
        schema["definitions"].update(self.definitions_schema)

        return schema


def validate_schema(*, data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Validate properties according to the given schema.

    :param data: the structured data to validate against the schema.
    :param schema: the validation schema.
    """

    format_check = jsonschema.FormatChecker()
    try:
        jsonschema.validate(data, schema, format_checker=format_check)
    except jsonschema.ValidationError as err:
        raise errors.SchemaValidation.from_validation_error(err)
