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

import os
import shutil

from craft_parts.utils import elf_utils
from tests import TESTS_DIR


class FakeElf:
    """Provides different types of fake ELF files."""

    def __init__(self, *, root_path, mocker, patchelf_version="0.10"):
        self.root_path = root_path
        self.core_base_path = root_path / "base"
        self._patchelf_version = patchelf_version

        binaries_path = TESTS_DIR / "bin" / "elf"
        new_binaries_path = root_path

        # Copy strip
        for f in ["strip", "execstack"]:
            shutil.copy(binaries_path / f, new_binaries_path / f)
            (new_binaries_path / f).chmod(0o755)

        # Some values in ldd need to be set with core_path
        with open(binaries_path / "ldd") as rf:
            with open(new_binaries_path / "ldd", "w") as wf:
                for line in rf.readlines():
                    wf.write(line.replace("{CORE_PATH}", str(self.core_base_path)))
        (new_binaries_path / "ldd").chmod(0o755)

        # Some values in ldd need to be set with core_path
        self.patchelf_path = new_binaries_path / "patchelf"
        with open(binaries_path / "patchelf") as rf:
            with open(self.patchelf_path, "w") as wf:
                for line in rf.readlines():
                    wf.write(line.replace("{VERSION}", self._patchelf_version))
        (new_binaries_path / "patchelf").chmod(0o755)

        mocker.patch.object(
            elf_utils.ElfFile,
            "_extract_attributes",
            new_callable=lambda: _fake_elffile_extract_attributes,
        )

        self._elf_files = {
            "fake_elf-2.26": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-2.26")
            ),
            "fake_elf-2.23": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-2.23")
            ),
            "fake_elf-1.1": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-1.1")
            ),
            "fake_elf-static": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-static")
            ),
            "fake_elf-shared-object": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-shared-object")
            ),
            "fake_elf-with-host-libraries": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-with-host-libraries")
            ),
            "fake_elf-bad-ldd": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-bad-ldd")
            ),
            "fake_elf-bad-patchelf": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-bad-patchelf")
            ),
            "fake_elf-with-core-libs": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-with-core-libs")
            ),
            "fake_elf-with-missing-libs": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-with-missing-libs")
            ),
            "fake_elf-with-execstack": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-with-execstack")
            ),
            "fake_elf-with-bad-execstack": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "fake_elf-with-bad-execstack")
            ),
            "libc.so.6": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "libc.so.6")
            ),
            "libssl.so.1.0.0": elf_utils.ElfFile(
                path=os.path.join(self.root_path, "libssl.so.1.0.0")
            ),
        }

        for elf_file in self._elf_files.values():
            with open(elf_file.path, "wb") as f:
                f.write(b"\x7fELF")
                if elf_file.path.endswith("fake_elf-bad-patchelf"):
                    f.write(b"nointerpreter")

        self.root_libraries = {
            "foo.so.1": os.path.join(self.root_path, "foo.so.1"),
            "moo.so.2": os.path.join(self.root_path, "non-standard", "moo.so.2"),
        }

        barsnap_elf = os.path.join(self.core_base_path, "barsnap.so.2")
        elf_list = [*self.root_libraries.values(), barsnap_elf]

        for root_library in elf_list:
            os.makedirs(os.path.dirname(root_library), exist_ok=True)
            with open(root_library, "wb") as f:
                f.write(b"\x7fELF")

    def __getitem__(self, item):
        return self._elf_files[item]


# pylint: disable=too-many-statements


def _fake_elffile_extract_attributes(self):
    name = os.path.basename(self.path)

    self.arch = ("ELFCLASS64", "ELFDATA2LSB", "EM_X86_64")
    self.build_id = "build-id-{}".format(name)

    if name in [
        "fake_elf-2.26",
        "fake_elf-bad-ldd",
        "fake_elf-with-core-libs",
        "fake_elf-with-missing-libs",
        "fake_elf-bad-patchelf",
        "fake_elf-with-host-libraries",
    ]:
        glibc = elf_utils.NeededLibrary(name="libc.so.6")
        glibc.add_version("GLIBC_2.2.5")
        glibc.add_version("GLIBC_2.26")

        self.interp = "/lib64/ld-linux-x86-64.so.2"
        self.soname = ""
        self.versions = set()
        self.needed = {glibc.name: glibc}
        self.execstack_set = False
        self.is_dynamic = True
        self.has_debug_info = False

    elif name == "fake_elf-2.23":
        glibc = elf_utils.NeededLibrary(name="libc.so.6")
        glibc.add_version("GLIBC_2.2.5")
        glibc.add_version("GLIBC_2.23")

        self.interp = "/lib64/ld-linux-x86-64.so.2"
        self.soname = ""
        self.versions = set()
        self.needed = {glibc.name: glibc}
        self.execstack_set = False
        self.is_dynamic = True
        self.has_debug_info = False

    elif name == "fake_elf-1.1":
        glibc = elf_utils.NeededLibrary(name="libc.so.6")
        glibc.add_version("GLIBC_1.1")
        glibc.add_version("GLIBC_0.1")

        self.interp = "/lib64/ld-linux-x86-64.so.2"
        self.soname = ""
        self.versions = set()
        self.needed = {glibc.name: glibc}
        self.execstack_set = False
        self.is_dynamic = True
        self.has_debug_info = False

    elif name == "fake_elf-static":
        self.interp = "/lib64/ld-linux-x86-64.so.2"
        self.soname = ""
        self.versions = set()
        self.needed = dict()
        self.execstack_set = False
        self.is_dynamic = False
        self.has_debug_info = False

    elif name == "fake_elf-shared-object":
        openssl = elf_utils.NeededLibrary(name="libssl.so.1.0.0")
        openssl.add_version("OPENSSL_1.0.0")

        self.interp = ""
        self.soname = "libfake_elf.so.0"
        self.versions = set()
        self.needed = {openssl.name: openssl}
        self.execstack_set = False
        self.is_dynamic = True
        self.has_debug_info = False

    elif name == "fake_elf-with-execstack":
        glibc = elf_utils.NeededLibrary(name="libc.so.6")
        glibc.add_version("GLIBC_2.23")

        self.interp = "/lib64/ld-linux-x86-64.so.2"
        self.soname = ""
        self.versions = set()
        self.needed = {glibc.name: glibc}
        self.execstack_set = True
        self.is_dynamic = True
        self.has_debug_info = False

    elif name == "fake_elf-with-bad-execstack":
        glibc = elf_utils.NeededLibrary(name="libc.so.6")
        glibc.add_version("GLIBC_2.23")

        self.interp = "/lib64/ld-linux-x86-64.so.2"
        self.soname = ""
        self.versions = set()
        self.needed = {glibc.name: glibc}
        self.execstack_set = True
        self.is_dynamic = True
        self.has_debug_info = False

    elif name == "libc.so.6":
        self.interp = ""
        self.soname = "libc.so.6"
        self.versions = {"libc.so.6", "GLIBC_2.2.5", "GLIBC_2.23", "GLIBC_2.26"}
        self.needed = {}
        self.execstack_set = False
        self.is_dynamic = True
        self.has_debug_info = False

    elif name == "libssl.so.1.0.0":
        self.interp = ""
        self.soname = "libssl.so.1.0.0"
        self.versions = {"libssl.so.1.0.0", "OPENSSL_1.0.0"}
        self.needed = {}
        self.execstack_set = False
        self.is_dynamic = True
        self.has_debug_info = False

    else:
        self.interp = ""
        self.soname = ""
        self.versions = set()
        self.needed = {}
        self.execstack_set = False
        self.is_dynamic = True
        self.has_debug_info = False
