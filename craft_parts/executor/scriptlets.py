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

"""Helpers to run scriptlets."""

import json
import logging
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

from craft_parts import errors
from craft_parts.utils import file_utils

logger = logging.getLogger(__name__)


def run(*, scriptlet_name: str, scriptlet: str, workdir: Path, env: str = "") -> None:
    """Run a scriptlet."""

    with tempfile.TemporaryDirectory() as tempdir:
        call_fifo = file_utils.NonBlockingRWFifo(os.path.join(tempdir, "function_call"))
        feedback_fifo = file_utils.NonBlockingRWFifo(
            os.path.join(tempdir, "call_feedback")
        )

        # snapcraftctl only works consistently if it's using the exact same
        # interpreter as that used by snapcraft itself, thus the definition
        # of SNAPCRAFT_INTERPRETER.
        script = textwrap.dedent(
            """\
            set -e
            export PARTBUILDERCTL_CALL_FIFO={call_fifo}
            export PARTBUILDERCTL_FEEDBACK_FIFO={feedback_fifo}
            export PARTBUIDLER_INTERPRETER={interpreter}
            {env}

            {env}

            {scriptlet}"""
        ).format(
            interpreter=sys.executable,
            call_fifo=call_fifo.path,
            feedback_fifo=feedback_fifo.path,
            scriptlet=scriptlet,
            env=env,
        )

        with tempfile.TemporaryFile(mode="w+") as script_file:
            print(script, file=script_file)
            script_file.flush()
            script_file.seek(0)
            process = subprocess.Popen(["/bin/sh"], stdin=script_file, cwd=workdir)

        status = None
        try:
            while status is None:
                function_call = call_fifo.read()
                if function_call:
                    # Handle the function and let caller know that function
                    # call has been handled (must contain at least a
                    # newline, anything beyond is considered an error by
                    # snapcraftctl)
                    _handle_builtin_function(scriptlet_name, function_call.strip())
                    feedback_fifo.write("\n")

                status = process.poll()

                # Don't loop TOO busily
                time.sleep(0.1)
        except Exception as error:
            feedback_fifo.write(f"{error!s}\n")
            raise error
        finally:
            call_fifo.close()
            feedback_fifo.close()

        if process.returncode != 0:
            raise errors.ScriptletRunError(scriptlet_name=scriptlet_name, code=status)


def _handle_builtin_function(scriptlet_name, function_call) -> None:
    try:
        function_json = json.loads(function_call)
    except json.decoder.JSONDecodeError as err:
        raise errors.InternalError(
            "{!r} scriptlet called a function with invalid json: "
            "{}".format(scriptlet_name, function_call)
        ) from err

    for attr in ["function", "args"]:
        if attr not in function_json:
            raise errors.InternalError(
                f"{scriptlet_name} scriptlet missing attribute {attr!r}"
            )

    # function_name = function_json["function"]
    # function_args = function_json["args"]

    # TODO: handle built-in functions
    # try:
    #     function = self._builtin_functions[function_name]
    # except KeyError as e:
    #     raise errors.InternalError(
    #         "{!r} scriptlet called an undefined builtin function: "
    #         "{}".format(scriptlet_name, function_name)
    #     ) from e

    # function(**function_args)
