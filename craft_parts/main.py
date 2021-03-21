# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2021 Canonical Ltd
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

"""Part crafting command line tool.

This is the main entry point for the craft_parts package, invoked
when running `python -mcraft_parts`. It provides basic functionality
to process a parts specification and display the planned sequence
of actions (using `--plan-only`) or execute them,
"""

import argparse
import logging
import sys

import yaml

import craft_parts
import craft_parts.errors
from craft_parts import ActionType, Step


def main():
    """The main entry point."""

    options = _parse_arguments()

    if options.version:
        print(f"craft-parts {craft_parts.__version__}")
        sys.exit()

    logging.basicConfig(level=logging.INFO)

    try:
        _process_parts(options)
    except OSError as err:
        print(f"Error: {err.strerror}.", file=sys.stderr)
        sys.exit(1)
    except craft_parts.errors.SchemaValidationError:
        print("Error: invalid parts specification.", file=sys.stderr)
        sys.exit(2)
    except craft_parts.errors.CraftPartsError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(3)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(4)


def _process_parts(options: argparse.Namespace) -> None:
    with open(options.file) as f:
        part_data = yaml.safe_load(f)

    lf = craft_parts.LifecycleManager(
        part_data, application_name="craft-parts", work_dir=options.work_dir
    )

    command = options.command if options.command else "prime"
    if command == "clean":
        _do_clean(lf, options)
        sys.exit()

    _do_step(lf, options)


def _do_step(lf: craft_parts.LifecycleManager, options: argparse.Namespace) -> None:
    target_step = _parse_step(options.command) if options.command else Step.PRIME
    part_names = vars(options).get("parts", [])

    if options.update:
        lf.update()

    actions = lf.plan(target_step, part_names)

    if options.plan_only:
        printed = False
        for action in actions:
            if options.show_skipped or action.type != ActionType.SKIP:
                print(_action_message(action))
                printed = True
        if not printed:
            print("No actions to execute.")
        sys.exit()

    with lf.action_executor() as ctx:
        for action in actions:
            if options.show_skipped or action.type != ActionType.SKIP:
                print(f"Execute: {_action_message(action)}")
                ctx.execute(action)


def _do_clean(lf: craft_parts.LifecycleManager, options: argparse.Namespace) -> None:
    if options.plan_only:
        raise ValueError("Clean operations cannot be planned.")

    if not options.parts:
        print("Clean all parts.")

    lf.clean(None, options.parts)


def _action_message(a: craft_parts.Action) -> str:
    msg = {
        Step.PULL: {
            ActionType.RUN: "Pull",
            ActionType.RERUN: "Repull",
            ActionType.SKIP: "Skip pull",
            ActionType.UPDATE: "Update sources for",
        },
        Step.BUILD: {
            ActionType.RUN: "Build",
            ActionType.RERUN: "Rebuild",
            ActionType.SKIP: "Skip build",
            ActionType.UPDATE: "Update build for",
        },
        Step.STAGE: {
            ActionType.RUN: "Stage",
            ActionType.RERUN: "Restage",
            ActionType.SKIP: "Skip stage",
        },
        Step.PRIME: {
            ActionType.RUN: "Prime",
            ActionType.RERUN: "Re-prime",
            ActionType.SKIP: "Skip prime",
        },
    }

    if a.reason:
        return f"{msg[a.step][a.type]} {a.part_name} ({a.reason})"

    return f"{msg[a.step][a.type]} {a.part_name}"


def _parse_step(name: str) -> Step:
    step_map = {
        "pull": Step.PULL,
        "build": Step.BUILD,
        "stage": Step.STAGE,
        "prime": Step.PRIME,
    }

    return step_map.get(name, Step.PRIME)


def _parse_arguments() -> argparse.Namespace:
    prog = "python -m craft_parts"
    description = (
        "A command line interface for the craft_parts module to build "
        "parts-based projects."
    )

    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "-f",
        "--file",
        metavar="filename",
        default="parts.yaml",
        help="The parts specification file (default: parts.yaml)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Refresh the stage packages list before procceeding",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Show planned actions to be executed and exit",
    )
    parser.add_argument(
        "--show-skipped",
        action="store_true",
        help="Also display skipped actions",
    )
    parser.add_argument(
        "--work-dir",
        metavar="dirname",
        default=".",
        help="Use the specified work directory (default: current)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Display the craft-parts version and exit",
    )

    subparsers = parser.add_subparsers(dest="command")

    pull_parser = subparsers.add_parser("pull", help="Pull the specified parts")
    pull_parser.add_argument("parts", nargs="*", help="The list of parts to pull")

    build_parser = subparsers.add_parser("build", help="Build the specified parts")
    build_parser.add_argument("parts", nargs="*", help="The list of parts to build")

    stage_parser = subparsers.add_parser("stage", help="Stage the specified parts")
    stage_parser.add_argument("parts", nargs="*", help="The list of parts to stage")

    prime_parser = subparsers.add_parser("prime", help="Prime the specified parts")
    prime_parser.add_argument("parts", nargs="*", help="The list of parts to prime")

    clean_parser = subparsers.add_parser(
        "clean", help="Clean the specified steps and parts"
    )
    clean_parser.add_argument(
        "parts", nargs="*", help="The list of parts whose this step should be cleaned"
    )

    return parser.parse_args()
