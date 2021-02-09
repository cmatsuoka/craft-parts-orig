# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2019-2021 Canonical Ltd
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

from craft_parts.utils import yaml_utils

contents = textwrap.dedent(
    """\
    foo: bar
    foobar:
    - zzz
    - aaa
    """
)


def test_load_yaml_data():
    data = yaml_utils.load(contents)
    assert data == {"foo": "bar", "foobar": ["zzz", "aaa"]}


def test_dump_yaml_data():
    data = {"foo": "bar", "foobar": ["zzz", "aaa"]}
    assert yaml_utils.dump(data) == contents
