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

import textwrap
from pathlib import Path

import pytest

from craft_parts.schemas import Validator

_pull_state_foo = textwrap.dedent(
    """\
    !PullState
    assets:
      stage-packages:
      - fake-package-foo=1
    """
)

_pull_state_bar = textwrap.dedent(
    """\
    !PullState
    assets:
      stage-packages:
      - fake-package-bar=2
    """
)


@pytest.fixture
def fake_validator(mocker) -> Validator:
    mocker.patch("craft_parts.schemas.Validator._load_schema")
    mocker.patch("craft_parts.schemas.Validator.merge_schema", return_value=dict())
    mocker.patch("craft_parts.schemas.Validator.schema", return_value=dict())
    mocker.patch("craft_parts.schemas.Validator.validate", return_value=True)
    return Validator("")


@pytest.fixture
def fake_state(new_dir):
    # build current state
    Path(new_dir / "parts/foo/state").mkdir(parents=True)
    Path(new_dir / "parts/bar/state").mkdir(parents=True)
    Path(new_dir / "parts/foo/state/pull").write_text(_pull_state_foo)
    Path(new_dir / "parts/bar/state/pull").write_text(_pull_state_bar)
