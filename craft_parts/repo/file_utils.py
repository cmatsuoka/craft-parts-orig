# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016-2019 Canonical Ltd
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

"""File utilities and helpers."""

# FIXME: change the name of this package to avoid confusion with utils.file_utils

import logging
import os
from typing import Pattern

logger = logging.getLogger(__name__)


def replace_in_file(
    directory: str, file_pattern: Pattern, search_pattern: Pattern, replacement: str
) -> None:
    """Searches and replaces patterns that match a file pattern.

    :param str directory: The directory to look for files.
    :param str file_pattern: The file pattern to match inside directory.
    :param search_pattern: A re.compile'd pattern to search for within
                           matching files.
    :param str replacement: The string to replace the matching search_pattern
                            with.
    """

    for root, _, files in os.walk(directory):
        for file_name in files:
            if file_pattern.match(file_name):
                file_path = os.path.join(root, file_name)
                # Don't bother trying to rewrite a symlink. It's either invalid
                # or the linked file will be rewritten on its own.
                if not os.path.islink(file_path):
                    search_and_replace_contents(file_path, search_pattern, replacement)


def search_and_replace_contents(
    file_path: str, search_pattern: Pattern, replacement: str
) -> None:
    """Search file and replace any occurrence of pattern with replacement.

    :param str file_path: Path of file to be searched.
    :param re.RegexObject search_pattern: Pattern for which to search.
    :param str replacement: The string to replace pattern.
    """
    try:
        with open(file_path, "r+") as fil:
            try:
                original = fil.read()
            except UnicodeDecodeError:
                # This was probably a binary file. Skip it.
                return

            replaced = search_pattern.sub(replacement, original)
            if replaced != original:
                fil.seek(0)
                fil.truncate()
                fil.write(replaced)
    except PermissionError as err:
        logger.warning("Unable to open %s for writing: %s", file_path, err)
