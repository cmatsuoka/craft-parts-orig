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

import sys
import textwrap
from pathlib import Path

import pytest

import craft_parts
import craft_parts.__main__ as main

parts_yaml = textwrap.dedent(
    """
    parts:
      foo:
        plugin: nil
      bar:
        after: [foo]
        plugin: nil
"""
)


@pytest.fixture(autouse=True)
def setup_new_dir(new_dir):  # pylint: disable=unused-argument
    pass


def test_main_no_args(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert out == (
        "Execute: Pull foo\n"
        "Execute: Pull bar\n"
        "Execute: Build foo\n"
        "Execute: Stage foo (required to build 'bar')\n"
        "Execute: Build bar\n"
        "Execute: Stage bar\n"
        "Execute: Prime foo\n"
        "Execute: Prime bar\n"
    )
    assert Path("parts").is_dir()
    assert Path("parts/foo").is_dir()
    assert Path("parts/bar").is_dir()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()


def test_main_version(mocker, capfd):
    mocker.patch.object(sys, "argv", ["cmd", "--version"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == f"craft-parts {craft_parts.__version__}\n"


def test_main_plan_only(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "pull", "--plan-only"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "Pull foo\nPull bar\n"
    assert Path("parts").is_dir() is False


def test_main_plan_only_skip(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd", "pull"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "Execute: Pull foo\nExecute: Pull bar\n"

    # run it again on the existing state
    mocker.patch.object(sys, "argv", ["cmd", "pull", "--plan-only"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "No actions to execute.\n"


def test_main_plan_only_show_skip(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd", "pull"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "Execute: Pull foo\nExecute: Pull bar\n"

    # run it again on the existing state
    mocker.patch.object(sys, "argv", ["cmd", "pull", "--plan-only", "--show-skip"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "Skip pull foo (already ran)\nSkip pull bar (already ran)\n"


@pytest.mark.parametrize(
    "step,executed",
    [
        ("pull", ["Pull"]),
        ("build", ["Pull", "Build"]),
        ("stage", ["Pull", "Build", "Stage"]),
        ("prime", ["Pull", "Build", "Stage", "Prime"]),
    ],
)
def test_main_specify_part(mocker, capfd, step, executed):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", step, "foo"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "".join([f"Execute: {x} foo\n" for x in executed])


@pytest.mark.parametrize(
    "step,planned",
    [
        ("pull", ["Pull"]),
        ("build", ["Pull", "Build"]),
        ("stage", ["Pull", "Build", "Stage"]),
        ("prime", ["Pull", "Build", "Stage", "Prime"]),
    ],
)
def test_main_specify_part_plan_only(mocker, capfd, step, planned):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", step, "foo", "--plan-only"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "".join([f"{x} foo\n" for x in planned])

    assert Path("parts").is_dir() is False


def test_main_specify_multiple_parts(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "pull", "foo", "bar", "--plan-only"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "Pull foo\nPull bar\n"
    assert Path("parts").is_dir() is False


@pytest.mark.parametrize("step", ["pull", "build", "stage", "prime"])
def test_main_invalid_part(mocker, capfd, step):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", step, "invalid"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 1

    out, err = capfd.readouterr()
    assert err == "Error: A part named 'invalid' is not defined in the parts list.\n"
    assert out == ""


@pytest.mark.parametrize("step", ["pull", "build", "stage", "prime"])
def test_main_invalid_part_plan_only(mocker, capfd, step):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", step, "invalid", "--plan-only"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 1

    out, err = capfd.readouterr()
    assert err == "Error: A part named 'invalid' is not defined in the parts list.\n"
    assert out == ""
    assert Path("parts").is_dir() is False


def test_main_invalid_multiple_parts_plan_only(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "pull", "foo", "invalid", "--plan-only"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 1

    out, err = capfd.readouterr()
    assert err == "Error: A part named 'invalid' is not defined in the parts list.\n"
    assert out == ""
    assert Path("parts").is_dir() is False


def test_main_clean(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert Path("parts").is_dir()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()

    # clean the existing work dirs
    mocker.patch.object(sys, "argv", ["cmd", "clean"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "Clean all parts.\n"
    assert Path("parts").is_dir() is False
    assert Path("stage").is_dir() is False
    assert Path("prime").is_dir() is False

    # clean the again should not fail
    mocker.patch.object(sys, "argv", ["cmd", "clean"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None
    assert err == ""
    assert out == "Clean all parts.\n"


def test_main_clean_part(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert Path("parts").is_dir()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()

    # clean the existing work dirs
    mocker.patch.object(sys, "argv", ["cmd", "clean", "foo"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == ""
    assert Path("parts/foo/state/pull").is_file() is False
    assert Path("parts/foo/state/build").is_file() is False
    assert Path("parts/foo/state/state").is_file() is False
    assert Path("parts/foo/state/prime").is_file() is False
    assert Path("parts/bar/state/pull").is_file()
    assert Path("parts/bar/state/build").is_file()
    assert Path("parts/bar/state/stage").is_file()
    assert Path("parts/bar/state/prime").is_file()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()

    # clean the again should not fail
    mocker.patch.object(sys, "argv", ["cmd", "clean", "foo"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None
    assert err == ""
    assert out == ""


def test_main_clean_multiple_part(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert Path("parts").is_dir()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()

    # clean the existing work dirs
    mocker.patch.object(sys, "argv", ["cmd", "clean", "foo", "bar"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == ""
    assert Path("parts/foo/state/pull").is_file() is False
    assert Path("parts/foo/state/build").is_file() is False
    assert Path("parts/foo/state/state").is_file() is False
    assert Path("parts/foo/state/prime").is_file() is False
    assert Path("parts/bar/state/pull").is_file() is False
    assert Path("parts/bar/state/build").is_file() is False
    assert Path("parts/bar/state/stage").is_file() is False
    assert Path("parts/bar/state/prime").is_file() is False


def test_main_clean_invalid_part(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd", "clean", "invalid"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 1

    out, err = capfd.readouterr()
    assert err == "Error: A part named 'invalid' is not defined in the parts list.\n"
    assert out == ""


def test_main_clean_invalid_multiple_part(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd", "clean", "foo", "invalid"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 1

    out, err = capfd.readouterr()
    assert err == "Error: A part named 'invalid' is not defined in the parts list.\n"
    assert out == ""
