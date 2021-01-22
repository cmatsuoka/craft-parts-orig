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

"""Built-in step execution handlers."""

import logging
import subprocess

from craft_parts import errors, plugins
from craft_parts.parts import Part
from craft_parts.plugins import Plugin

logger = logging.getLogger(__name__)


def pull(*, part: Part) -> None:
    """Execute the built-in pull step handler."""


def build(*, part: Part, plugin: Plugin, env: str) -> None:
    """Execute the built-in build step handler."""

    if not isinstance(plugin, plugins.PluginV2):
        raise errors.InternalError("Plugin version not supported.")

    _do_v2_build(part=part, plugin=plugin, env=env)


def stage(*, part: Part) -> None:
    """Execute the built-in stage step handler."""


def prime(*, part: Part) -> None:
    """Execute the built-in prime step handler."""


def _do_v2_build(*, part: Part, plugin: Plugin, env: str) -> None:
    # Save script to execute.
    build_script_path = part.part_run_dir / "build.sh"

    # Plugin commands.
    plugin_build_commands = plugin.get_build_commands()

    with build_script_path.open("w") as run_file:
        print(env, file=run_file)
        print("set -x", file=run_file)

        for build_command in plugin_build_commands:
            print(build_command, file=run_file)

        run_file.flush()

    source_subdir = part.data.get("source-subdir", "")
    build_work_dir = part.part_build_dir / source_subdir

    try:
        subprocess.run([build_script_path], check=True, cwd=build_work_dir)
    except subprocess.CalledProcessError as process_error:
        raise errors.PluginBuildError(part_name=part.name) from process_error
