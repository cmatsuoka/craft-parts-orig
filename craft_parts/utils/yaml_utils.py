# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2018-2021 Canonical Ltd
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

"""YAML file handling utilities."""

import collections
from typing import Any, TextIO

import yaml

try:
    # The C-based loaders/dumpers aren't available everywhere, but they're much faster.
    # Use them if possible. If not, we could fallback to the normal loader/dumper.
    # from .yaml_utils_c import SafeDumper, SafeLoader

    import yaml.constructor
    from yaml import CSafeDumper, CSafeLoader  # type: ignore

    class SafeLoader(CSafeLoader):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.add_constructor(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _dict_constructor
            )

    class SafeDumper(CSafeDumper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.add_representer(str, _str_presenter)
            self.add_representer(collections.OrderedDict, _dict_representer)

    def _dict_constructor(loader, node):
        # Necessary in order to make yaml merge tags work
        loader.flatten_mapping(node)
        value = loader.construct_pairs(node)

        try:
            return collections.OrderedDict(value)
        except TypeError:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found unhashable key",
                node.start_mark,
            )

    def _dict_representer(dumper, data):
        return dumper.represent_dict(data.items())

    def _str_presenter(dumper, data):
        if len(data.splitlines()) > 1:  # check for multiline string
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)


except ImportError:
    from yaml import SafeDumper, SafeLoader  # type: ignore


def load(stream: TextIO) -> Any:
    """Safely load YAML in ordered manner."""
    return yaml.load(stream, Loader=SafeLoader)


class YAMLObject(yaml.YAMLObject):
    yaml_loader = SafeLoader
    yaml_dumper = SafeDumper
