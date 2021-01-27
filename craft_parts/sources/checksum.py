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

"""Helpers to compute and verify file checksums."""

from typing import Tuple

from craft_parts import errors
from craft_parts.utils import file_utils


def split_checksum(source_checksum: str) -> Tuple:
    """Splits source_checksum into algorithm and hash.
    :raises ValueError: if source_checksum is not of the form algorithm/hash.
    :returns: a tuple consisting of the algorithm and the hash.
    """
    try:
        algorithm, digest = source_checksum.split("/", 1)
    except ValueError as err:
        raise ValueError(f"invalid checksum format: {source_checksum!r}") from err

    return (algorithm, digest)


def verify_checksum(source_checksum: str, checkfile: str) -> Tuple:
    """Verifies that checkfile corresponds to the given source_checksum.
    :param str source_checksum: algorithm/hash expected for checkfile.
    :param str checkfile: the file to calculate the sum for with the
                          algorithm defined in source_checksum.
    :raises ValueError: if source_checksum is not of the form algorithm/hash.
    :raises DigestDoesNotMatchError: if checkfile does not match the expected
                                     hash calculated with the algorithm defined
                                     in source_checksum.
    :returns: a tuple consisting of the algorithm and the hash.
    """
    algorithm, digest = split_checksum(source_checksum)

    calculated_digest = file_utils.calculate_hash(checkfile, algorithm=algorithm)
    if digest != calculated_digest:
        raise errors.ChecksumMismatch(digest, calculated_digest)

    return (algorithm, digest)
