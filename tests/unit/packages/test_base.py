# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2017-2021 Canonical Ltd
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

from craft_parts.packages._base import get_pkg_name_parts


class TestPkgNameParts:
    """Check the extraction of package name parts."""

    def test_get_pkg_name_parts_name_only(self):
        name, version = get_pkg_name_parts("hello")
        assert name == "hello"
        assert version is None

    def test_get_pkg_name_parts_all(self):
        name, version = get_pkg_name_parts("hello:i386=2.10-1")
        assert name == "hello:i386"
        assert version == "2.10-1"

    def test_get_pkg_name_parts_no_arch(self):
        name, version = get_pkg_name_parts("hello=2.10-1")
        assert name == "hello"
        assert version == "2.10-1"
