# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2020 Canonical Ltd
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

"""Handle part files organization.

Installed part files can be reorganized according to a mapping specified
under the `organize` entry in a part definition. In the key/value pair,
the key represents the path of a file inside the part and the value
represents how the file is going to be staged.
"""

import contextlib
import os
import shutil
from glob import iglob
from pathlib import Path
from typing import Dict

from craft_parts import errors
from craft_parts.utils import file_utils


def organize_files(
    *, part_name: str, mapping: Dict[str, str], base_dir: Path, overwrite: bool
):
    """Rearrange files for part staging.

    :param fileset: A fileset containing the `organize` file mapping.
    :param base_dir: Where the installed files are located.
    :param overwrite: Whether existing files should be overwritten.
    """

    for key in sorted(mapping, key=lambda x: ["*" in x, x]):
        src = str(base_dir / key)
        # Remove the leading slash so the path actually joins
        dst = str(base_dir / mapping[key].lstrip("/"))

        sources = iglob(src, recursive=True)

        # Keep track of the number of glob expansions so we can properly error if more
        # than one tries to organize to the same file
        src_count = 0
        for src in sources:
            src_count += 1

            if os.path.isdir(src) and "*" not in key:
                file_utils.link_or_copy_tree(src, dst)
                # TODO create alternate organization location to avoid
                # deletions.
                shutil.rmtree(src)
                continue

            if os.path.isfile(dst):
                if overwrite and src_count <= 1:
                    with contextlib.suppress(FileNotFoundError):
                        os.remove(dst)
                elif src_count > 1:
                    raise errors.FileOrganizeError(
                        part_name,
                        "multiple files to be organized into {!r}. If this is supposed "
                        "to be a directory, end it with a forward slash.".format(
                            os.path.relpath(dst, base_dir)
                        ),
                    )
                else:
                    raise errors.FileOrganizeError(
                        part_name,
                        "trying to organize file {key!r} to {dst!r}, but {dst!r} "
                        "already exists".format(
                            key=key, dst=os.path.relpath(dst, base_dir)
                        ),
                    )

            if os.path.isdir(dst) and overwrite:
                real_dst = os.path.join(dst, os.path.basename(src))
                if os.path.isdir(real_dst):
                    shutil.rmtree(real_dst)
                else:
                    with contextlib.suppress(FileNotFoundError):
                        os.remove(real_dst)

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
