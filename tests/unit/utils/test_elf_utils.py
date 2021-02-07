# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016-2021 Canonical Ltd
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

import os
import sys
import tempfile
import textwrap

from craft_parts.utils import elf_utils

# pylint: disable=missing-class-docstring


class TestLdLibraryPathParser:
    def test_extract_ld_library_paths(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, mode="w")

        tmp.write(
            textwrap.dedent(
                """\
                # This is a comment
                /foo/bar
                /colon:/separated,/comma\t/tab /space # This is another comment
                /baz"""
            )
        )
        tmp.close()

        assert elf_utils._extract_ld_library_paths(tmp.name) == [
            "/foo/bar",
            "/colon",
            "/separated",
            "/comma",
            "/tab",
            "/space",
            "/baz",
        ]

        os.remove(tmp.name)


class TestElfFileSmoketest:
    def test_bin_echo(self):
        # Try parsing a file without the pyelftools logic mocked out
        elf_file = elf_utils.ElfFile(path=sys.executable)

        assert elf_file.path == sys.executable

        # The arch attribute will be a tuple of three strings
        assert isinstance(elf_file.arch, tuple)
        assert len(elf_file.arch) == 3
        assert elf_file.arch[0].startswith("ELFCLASS")
        assert elf_file.arch[1].startswith("ELFDATA")
        assert elf_file.arch[2].startswith("EM_")

        # We expect Python to be a dynamic linked executable with an
        # ELF interpreter.
        assert isinstance(elf_file.interp, str)
        assert elf_file.interp != ""

        # Python is not a shared library, so has no soname or defined versions
        assert elf_file.soname == ""
        assert elf_file.versions == set()

        # We expect that Python will be linked to libc
        for lib in elf_file.needed.values():
            if lib.name.startswith("libc.so"):
                break
        else:
            assert False, "Expected to find libc in needed library list"

        assert isinstance(lib.name, str)
        for version in lib.versions:
            assert isinstance(version, str), f"expected {version!r} to be a string"

        # GCC adds a build ID to executables
        assert elf_file.build_id != ""

        # If the Python interpreter is distro packaged, it probably
        # doesn't have debug info, but we don't know for sure.
        # Instead just check that it is a boolean.
        assert isinstance(elf_file.has_debug_info, bool)

        # Ensure type is detered as executable.
        assert elf_file.elf_type == "ET_EXEC"


class TestInvalidElf:
    def test_invalid_elf_file(self, tmpdir):
        invalid_elf = os.path.join(tmpdir, "invalid-elf")
        open(invalid_elf, "wb").write(b"\x7fELF\x00")

        elf_files = elf_utils.get_elf_files(tmpdir, ["invalid-elf"])
        assert elf_files == set()


# FIXME: add the rest of ELF tests
