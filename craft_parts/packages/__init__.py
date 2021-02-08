# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2017 Canonical Ltd
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

"""Operations with platform specific package repositories."""

from . import errors  # noqa: F401
from . import snaps  # noqa: F401
from . import _platform

# pylint: disable=import-outside-toplevel

# Imported for backwards compatibility with plugins
# if _platform._is_deb_based():
#     from ._deb import Ubuntu  # noqa


def _get_repository_for_platform():
    if _platform._is_deb_based():
        from ._deb import Ubuntu

        return Ubuntu

    from ._base import DummyRepository

    return DummyRepository


Repository = _get_repository_for_platform()
