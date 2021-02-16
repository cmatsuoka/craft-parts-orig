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
import subprocess
import sys
import tempfile
import textwrap

import pytest

from craft_parts import errors
from craft_parts.infos import ProjectInfo
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
        lib = None
        for x in elf_file.needed.values():
            if x.name.startswith("libc.so"):
                lib = x
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


class TestMissingLibraries:
    def test_get_libraries_missing_libs(self, fake_elf):
        elf_file = fake_elf["fake_elf-with-missing-libs"]
        libs = elf_file.load_dependencies(
            root_path=fake_elf.root_path,
            core_base_path=fake_elf.core_base_path,
            arch_triplet=ProjectInfo().arch_triplet,
            content_dirs=[],
        )

        assert libs == set([fake_elf.root_libraries["foo.so.1"], "missing.so.2"])


@pytest.fixture
def mock_path_exists(mocker):
    mocker.patch("os.path.exists", return_value=True)


@pytest.mark.usefixtures("mock_path_exists")
class TestGetLibraries:
    def test_get_libraries(self, fake_elf):
        elf_file = fake_elf["fake_elf-2.23"]
        libs = elf_file.load_dependencies(
            root_path=fake_elf.root_path,
            core_base_path=fake_elf.core_base_path,
            arch_triplet=ProjectInfo().arch_triplet,
            content_dirs=[],
        )

        assert libs == set([fake_elf.root_libraries["foo.so.1"], "/usr/lib/bar.so.2"])

    def test_get_libraries_with_soname_cache(self, fake_elf):
        elf_file = fake_elf["fake_elf-2.23"]

        arch = ("ELFCLASS64", "ELFDATA2LSB", "EM_X86_64")
        soname_cache = elf_utils.SonameCache()
        soname_cache[arch, "bar.so.2"] = "/lib/bar.so.2"

        libs = elf_file.load_dependencies(
            root_path=fake_elf.root_path,
            core_base_path=fake_elf.core_base_path,
            arch_triplet=ProjectInfo().arch_triplet,
            content_dirs=[],
            soname_cache=soname_cache,
        )

        # With no cache this would have returned '/usr/lib/bar.so.2'
        assert libs == set([fake_elf.root_libraries["foo.so.1"], "/lib/bar.so.2"])

    def test_primed_libraries_are_preferred(self, fake_elf):
        elf_file = fake_elf["fake_elf-2.23"]
        libs = elf_file.load_dependencies(
            root_path=fake_elf.root_path,
            core_base_path=fake_elf.core_base_path,
            arch_triplet=ProjectInfo().arch_triplet,
            content_dirs=[],
        )

        assert libs == frozenset(
            [fake_elf.root_libraries["foo.so.1"], "/usr/lib/bar.so.2"]
        )

    def test_non_elf_primed_sonames_matches_are_ignored(self, fake_elf):
        primed_foo = os.path.join(fake_elf.root_path, "foo.so.1")
        with open(primed_foo, "wb") as f:
            # A bz2 header
            f.write(b"\x42\x5a\x68")

        elf_file = fake_elf["fake_elf-2.23"]
        libs = elf_file.load_dependencies(
            root_path=fake_elf.root_path,
            core_base_path=fake_elf.core_base_path,
            arch_triplet=ProjectInfo().arch_triplet,
            content_dirs=[],
        )

        assert libs == frozenset(["/lib/foo.so.1", "/usr/lib/bar.so.2"])

    def test_get_libraries_excludes_slash_snap(self, fake_elf):
        elf_file = fake_elf["fake_elf-with-core-libs"]
        libs = elf_file.load_dependencies(
            root_path=fake_elf.root_path,
            core_base_path=fake_elf.core_base_path,
            arch_triplet=ProjectInfo().arch_triplet,
            content_dirs=[],
        )

        assert libs == set([fake_elf.root_libraries["foo.so.1"], "/usr/lib/bar.so.2"])

    def test_existing_host_library_searched_for(self, fake_elf, mocker):
        elf_file = fake_elf["fake_elf-with-host-libraries"]

        class MooLibrary(elf_utils.Library):
            """A Library implementation that always returns valid for moo."""

            def _is_valid_elf(self, resolved_path: str) -> bool:
                #  This path is defined in ldd for fake_elf-with-host-libraries.
                if resolved_path == "/usr/lib/moo.so.2":
                    return True

                return super()._is_valid_elf(resolved_path)

        mocker.patch("craft_parts.utils.elf_utils.Library", side_effect=MooLibrary)

        libs = elf_file.load_dependencies(
            root_path=fake_elf.root_path,
            core_base_path=fake_elf.core_base_path,
            arch_triplet=ProjectInfo().arch_triplet,
            content_dirs=[],
        )

        assert libs == {fake_elf.root_libraries["moo.so.2"]}


@pytest.mark.usefixtures("mock_path_exists", "fake_elf")
class TestLibrary:
    def test_is_valid_elf_ignores_corrupt_files(self, tmpdir, mocker):
        soname = "libssl.so.1.0.0"
        soname_path = os.path.join(tmpdir, soname)
        library = elf_utils.Library(
            soname=soname,
            soname_path=soname_path,
            search_paths=[tmpdir],
            core_base_path="/snap/core/current",
            arch=("ELFCLASS64", "ELFDATA2LSB", "EM_X86_64"),
            soname_cache=elf_utils.SonameCache(),
        )

        assert library._is_valid_elf(soname_path)

        mocker.patch(
            "craft_parts.utils.elf_utils.ElfFile",
            side_effect=errors.CorruptedElfFile(
                path=soname_path, message="oops, something wrong happened"
            ),
        )

        assert library._is_valid_elf(soname_path) is False


class TestGetElfFiles:
    def test_get_elf_files(self, fake_elf):
        elf_files = elf_utils.get_elf_files(fake_elf.root_path, ["fake_elf-2.23"])

        assert len(elf_files) == 1

        elf_file = set(elf_files).pop()
        assert elf_file.interp == "/lib64/ld-linux-x86-64.so.2"

    def test_skip_object_files(self, fake_elf):
        open(os.path.join(fake_elf.root_path, "object_file.o"), "w").close()

        elf_files = elf_utils.get_elf_files(fake_elf.root_path, ["object_file.o"])
        assert elf_files == set()

    def test_no_find_dependencies_statically_linked(self, fake_elf):
        elf_files = elf_utils.get_elf_files(fake_elf.root_path, ["fake_elf-static"])
        assert elf_files == set()

    def test_elf_with_execstack(self, fake_elf):
        elf_files = elf_utils.get_elf_files(
            fake_elf.root_path, ["fake_elf-with-execstack"]
        )
        elf_file = set(elf_files).pop()
        assert elf_file.execstack_set

    def test_elf_without_execstack(self, fake_elf):
        elf_files = elf_utils.get_elf_files(fake_elf.root_path, ["fake_elf-2.23"])
        elf_file = set(elf_files).pop()
        assert elf_file.execstack_set is False

    def test_non_elf_files(self, fake_elf):
        with open(os.path.join(fake_elf.root_path, "non-elf"), "wb") as f:
            # A bz2 header
            f.write(b"\x42\x5a\x68")

        elf_files = elf_utils.get_elf_files(fake_elf.root_path, ["non-elf"])
        assert elf_files == set()

    def test_symlinks(self, fake_elf):
        symlinked_path = os.path.join(fake_elf.root_path, "symlinked")
        os.symlink("/bin/dash", symlinked_path)

        elf_files = elf_utils.get_elf_files(fake_elf.root_path, ["symlinked"])

        assert elf_files == set()

    def test_device_files(self):
        elf_files = elf_utils.get_elf_files("/dev", ["null"])
        assert elf_files == set()

    def test_fifo(self, fake_elf):
        fifo_path = os.path.join(fake_elf.root_path, "fifo")
        os.mkfifo(fifo_path)

        elf_files = elf_utils.get_elf_files(fake_elf.root_path, ["fifo"])
        assert elf_files == set()


class TestGetRequiredGLIBC:
    def test_get_required_glibc(self, fake_elf):
        elf_file = fake_elf["fake_elf-2.23"]
        assert elf_file.get_required_glibc() == "2.23"

    def test_linker_version_greater_than_required_glibc(self, fake_elf):
        elf_file = fake_elf["fake_elf-2.23"]
        assert elf_file.is_linker_compatible(linker_version="2.26")

    def test_linker_version_equals_required_glibc(self, fake_elf):
        elf_file = fake_elf["fake_elf-2.23"]
        assert elf_file.is_linker_compatible(linker_version="2.23")

    def test_linker_version_less_than_required_glibc(self, fake_elf):
        elf_file = fake_elf["fake_elf-2.23"]
        assert elf_file.is_linker_compatible(linker_version="1.2") is False


class TestElfFileAttrs:
    def test_executable(self, fake_elf):
        elf_file = fake_elf["fake_elf-2.23"]

        assert elf_file.interp == "/lib64/ld-linux-x86-64.so.2"
        assert elf_file.soname == ""
        assert sorted(elf_file.needed.keys()) == ["libc.so.6"]

        glibc = elf_file.needed["libc.so.6"]
        assert glibc.name == "libc.so.6"
        assert glibc.versions == {"GLIBC_2.2.5", "GLIBC_2.23"}

    def test_shared_object(self, fake_elf):
        # fake_elf-shared-object has no GLIBC dependency, but two symbols
        # nonetheless
        elf_file = fake_elf["fake_elf-shared-object"]

        assert elf_file.interp == ""
        assert elf_file.soname == "libfake_elf.so.0"
        assert sorted(elf_file.needed.keys()) == ["libssl.so.1.0.0"]

        openssl = elf_file.needed["libssl.so.1.0.0"]
        assert openssl.name == "libssl.so.1.0.0"
        assert openssl.versions == {"OPENSSL_1.0.0"}

    def test_libssl(self, fake_elf):
        # libssl.so.1.0.0 defines some symbol versions it provides
        elf_file = fake_elf["libssl.so.1.0.0"]

        assert elf_file.interp == ""
        assert elf_file.soname == "libssl.so.1.0.0"
        assert elf_file.versions == {"libssl.so.1.0.0", "OPENSSL_1.0.0"}


class TestSonameCache:
    def setup_method(self):
        self.arch = ("ELFCLASS64", "ELFDATA2LSB", "EM_X86_64")  # pylint: disable=W0201
        self.soname_cache = elf_utils.SonameCache()  # pylint: disable=W0201

    def test_add_and_retrieve_soname_path(self):
        self.soname_cache[self.arch, "soname.so"] = "/fake/path/soname.so"
        assert self.soname_cache[self.arch, "soname.so"] == "/fake/path/soname.so"

    def test_add_and_verify_soname_path(self):
        self.soname_cache[self.arch, "soname.so"] = "/fake/path/soname.so"
        assert (self.arch, "soname.so") in self.soname_cache

    def test_reset_except_root(self):
        self.soname_cache[self.arch, "soname.so"] = "/fake/path/soname.so"
        self.soname_cache[self.arch, "soname2.so"] = "/keep/me/soname2.so"
        self.soname_cache[self.arch, "notfound.so"] = None

        assert (self.arch, "soname.so") in self.soname_cache
        assert (self.arch, "soname2.so") in self.soname_cache
        assert (self.arch, "notfound.so") in self.soname_cache

        self.soname_cache.reset_except_root("/keep/me")

        assert (self.arch, "soname.so") not in self.soname_cache
        assert (self.arch, "notfound.so") not in self.soname_cache
        assert (self.arch, "soname2.so") in self.soname_cache


@pytest.mark.parametrize(
    "key,partial_message",
    [
        # invalid string key
        ("soname.so", "The key for"),
        # invalid first argument tuple
        ((("ELFCLASS64", "ELFDATA2LSB"), "soname.so"), "The first element"),
        # invalid second argument type
        ((("ELFCLASS64", "ELFDATA2LSB", "EM_X86_64"), 1), "The second element"),
    ],
)
class TestSonameCacheErrors:
    def test_error(self, key, partial_message):
        soname_cache = elf_utils.SonameCache()
        with pytest.raises(EnvironmentError) as error:
            soname_cache.__setitem__(key, "/soname.so")
            assert str(error).startswith(partial_message)


@pytest.mark.parametrize(
    "ldd_output,expected",
    [
        # ubuntu 20.04 basic
        (
            """
\tlinux-vdso.so.1 (0x00007ffcae3e6000)
\tlibc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f33eebeb000)
\t/lib64/ld-linux-x86-64.so.2 (0x00007f33eedf2000)
""",
            {"libc.so.6": "/lib/x86_64-linux-gnu/libc.so.6"},
        ),
        # ubuntu 18.04 lspci w/o libpci
        (
            """
\tlinux-vdso.so.1 (0x00007fffeddd1000)
\tlibpci.so.3 => not found
\tlibkmod.so.2 => /lib/x86_64-linux-gnu/libkmod.so.2 (0x00007fe500619000)
\tlibc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007fe500228000)
\t/lib64/ld-linux-x86-64.so.2 (0x00007fe500a44000)
""",
            {
                "libc.so.6": "/lib/x86_64-linux-gnu/libc.so.6",
                "libkmod.so.2": "/lib/x86_64-linux-gnu/libkmod.so.2",
                "libpci.so.3": "libpci.so.3",
            },
        ),
        # ubuntu 16.04 basic
        (
            """
\tlinux-vdso.so.1 =>  (0x00007ffd71d64000)
\tlibc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007fda33a16000)
\t/lib64/ld-linux-x86-64.so.2 (0x00007fda33de0000)
""",
            {"libc.so.6": "/lib/x86_64-linux-gnu/libc.so.6"},
        ),
        # ubuntu 16.04 lspci w/o libpci
        (
            """
\tlinux-vdso.so.1 =>  (0x00007fff305b3000)
\tlibpci.so.3 => not found
\tlibkmod.so.2 => /lib/x86_64-linux-gnu/libkmod.so.2 (0x00007faef225c000)
\tlibc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007faef1e92000)
\t/lib64/ld-linux-x86-64.so.2 (0x00007faef2473000)
""",
            {
                "libc.so.6": "/lib/x86_64-linux-gnu/libc.so.6",
                "libkmod.so.2": "/lib/x86_64-linux-gnu/libkmod.so.2",
                "libpci.so.3": "libpci.so.3",
            },
        ),
    ],
)
class TestLddParsing:
    def test_scenario(self, ldd_output, expected, monkeypatch):
        def fake_abspath(path):
            return path

        monkeypatch.setattr(os.path, "exists", lambda f: True)
        monkeypatch.setattr(os.path, "abspath", fake_abspath)
        monkeypatch.setattr(
            subprocess, "check_output", lambda *args, **kwargs: ldd_output.encode()
        )

        libraries = elf_utils.ldd(path="/bin/foo", ld_library_paths=[])

        assert libraries == expected
