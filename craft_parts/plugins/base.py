# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2020 Canonical Ltd
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

"""Plugins V2 definitions."""

import abc
from typing import TYPE_CHECKING, Any, Dict, List, Set, Type

from .properties import PluginProperties

if TYPE_CHECKING:
    from craft_parts.infos import PartInfo


class Plugin(abc.ABC):
    """The base class for plugins conforming to the plugin API version 2.

    :cvar properties_class: The plugin properties class.

    :param part_name: the name of the part this plugin is instantiated to.
    :param options: an object representing part defined properties.
    """

    properties_class: Type[PluginProperties]

    def __init__(self, *, options: PluginProperties, part_info: "PartInfo") -> None:
        self._name = part_info.part_name
        self._options = options
        self._part_info = part_info

    @classmethod
    @abc.abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Return a jsonschema compatible dictionary for the plugin properties."""

    @abc.abstractmethod
    def get_build_snaps(self) -> Set[str]:
        """
        Return a set of required snaps to install in the build environment.
        """

    @abc.abstractmethod
    def get_build_packages(self) -> Set[str]:
        """
        Return a set of required packages to install in the build environment.
        """

    @abc.abstractmethod
    def get_build_environment(self) -> Dict[str, str]:
        """
        Return a dictionary with the environment to use in the build step.
        This method is called by the PluginHandler during the "build" step.
        """

    @property
    def out_of_source_build(self):
        """Set to True if the plugin performs out-of-source-tree builds.

        In practice, this controls whether the PluginHandler code will
        copy the source code to the build directory before invoking
        the plugin's build commands.
        """
        return False

    @abc.abstractmethod
    def get_build_commands(self) -> List[str]:
        """
        Return a list of commands to run during the build step.

        This method is called by the PluginHandler during the "build" step.
        These commands are run in a single shell instance. This means
        that commands run before do affect the commands that follow.

        snapcraftctl can be used in the script to call out to snapcraft
        specific functionality.
        """
