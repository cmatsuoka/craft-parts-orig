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

from collections import namedtuple

import pytest

from craft_parts import errors, sources

HandlerTC = namedtuple("HandlerTC", ["uri", "handler"])


@pytest.mark.parametrize("tc", [HandlerTC(".", sources.Local)])
def test_get_source_handler(tc):
    h = sources.get_source_handler(tc.uri)
    assert h == tc.handler


def test_get_source_handler_with_invalid_type():
    with pytest.raises(errors.InvalidSourceType) as ei:
        sources.get_source_handler(".", source_type="invalid")
    assert ei.value.get_brief() == "Source '.' type is not recognized."
