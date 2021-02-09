# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2021 Canonical Ltd
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

"""Common 'source' options.

Unless the part plugin overrides this behaviour, a part can use these
'source' keys in its definition. They tell snapcraft where to pull source
code for that part, and how to unpack it if necessary.

  - source: url-or-path

    A URL or path to some source tree to build. It can be local
    ('./src/foo') or remote ('https://foo.org/...'), and can refer to a
    directory tree or a tarball or a revision control repository
    ('git:...').

  - source-type: git, bzr, hg, svn, tar, deb, rpm, or zip

    In some cases the source string is not enough to identify the version
    control system or compression algorithm. The source-type key can tell
    snapcraft exactly how to treat that content.

  - source-checksum: <algorithm>/<digest>

    Snapcraft will use the digest specified to verify the integrity of the
    source. The source-type needs to be a file (tar, zip, deb or rpm) and
    the algorithm either md5, sha1, sha224, sha256, sha384, sha512, sha3_256,
    sha3_384 or sha3_512.

  - source-depth: <integer>

    By default clones or branches with full history, specifying a depth
    will truncate the history to the specified number of commits.

  - source-branch: <branch-name>

    Snapcraft will checkout a specific branch from the source tree. This
    only works on multi-branch repositories from git and hg (mercurial).

  - source-commit: <commit>

    Snapcraft will checkout the specific commit from the source tree revision
    control system.

  - source-tag: <tag>

    Snapcraft will checkout the specific tag from the source tree revision
    control system.

  - source-subdir: path

    When building, Snapcraft will set the working directory to be this
    subdirectory within the source.

Note that plugins might well define their own semantics for the 'source'
keywords, because they handle specific build systems, and many languages
have their own built-in packaging systems (think CPAN, PyPI, NPM). In those
cases you want to refer to the help text for the specific plugin.

  snapcraft help <plugin>

"""
import logging
import os
import os.path
import re
import sys
from typing import Any, Dict, Type, Union

from . import errors

if sys.platform == "linux":
    # from .bazaar import Bazaar  # noqa: F401
    # from .git import Git  # noqa: F401
    from .local import Local  # noqa: F401

    # from .mercurial import Mercurial  # noqa: F401
    # from .script import Script  # noqa: F401
    # from .subversion import Subversion  # noqa: F401
    from .tar import Tar  # noqa: F401

    # from .zip import Zip  # noqa: F401
    # from .7z import SevenZip  # noqa: F401
    # from .deb import Deb  # noqa: F401
    # from .rpm import Rpm  # noqa: F401
    # from .snap import Snap  # noqa: F401

    SourceHandler = Union[Local, Tar]
    SourceHandlerType = Type[SourceHandler]

    _source_handler: Dict[str, SourceHandlerType] = {
        # "bzr": Bazaar,
        # "git": Git,
        # "hg": Mercurial,
        # "mercurial": Mercurial,
        # "subversion": Subversion,
        # "svn": Subversion,
        "tar": Tar,
        # "zip": Zip,
        # "7z": SevenZip,
        "local": Local,
        # "deb": Deb,
        # "rpm": Rpm,
        # "snap": Snap,
        "": Local,
    }

else:
    # from .git import Git  # noqa
    from .local import Local  # noqa

    # from .tar import Tar  # noqa

    SourceHandlerType = Type[Union[Local]]

    _source_handler: Dict[str, SourceHandlerType] = {
        # "git": Git,
        "local": Local,
        "tar": Tar,
        "": Local,
    }


logging.getLogger("urllib3").setLevel(logging.CRITICAL)


__SOURCE_DEFAULTS = {
    "source": None,
    "source-commit": None,
    "source-checksum": None,
    "source-depth": None,
    "source-tag": None,
    "source-type": None,
    "source-branch": None,
    "source-subdir": None,
}


def get_source_defaults() -> Dict[str, Any]:
    """Obtain the default values for source properties."""
    return __SOURCE_DEFAULTS.copy()


def get_source_handler(source, *, source_type: str = "") -> SourceHandlerType:
    """Return the appropriate handler for the given source.

    :param source: the source specification.
    :param source_type: The source type to use. If not specified, the
        type will be inferred from the source specification.
    """

    if not source_type:
        source_type = get_source_type_from_uri(source)

    if source_type not in _source_handler:
        raise errors.InvalidSourceType(source)

    return _source_handler.get(source_type, Local)


_tar_type_regex = re.compile(r".*\.((tar(\.(xz|gz|bz2))?)|tgz)$")


def get_source_type_from_uri(
    source: str, ignore_errors: bool = False
) -> str:  # noqa: C901
    for extension in ["zip", "deb", "rpm", "7z", "snap"]:
        if source.endswith(".{}".format(extension)):
            return extension
    source_type = ""
    if source.startswith("bzr:") or source.startswith("lp:"):
        source_type = "bzr"
    elif (
        source.startswith("git:")
        or source.startswith("git@")
        or source.endswith(".git")
    ):
        source_type = "git"
    elif source.startswith("svn:"):
        source_type = "subversion"
    elif _tar_type_regex.match(source):
        source_type = "tar"
    elif os.path.isdir(source):
        source_type = "local"
    elif not ignore_errors:
        raise errors.InvalidSourceType(source)

    return source_type
