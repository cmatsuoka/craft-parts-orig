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
import stat

import pytest

from craft_parts import filesets
from craft_parts.executor import runner
from craft_parts.filesets import Fileset


@pytest.mark.usefixtures("new_dir")
class TestFileMigration:
    def test_migrate_files_already_exists(self):
        os.makedirs("install")
        os.makedirs("stage")

        # Place the already-staged file
        with open("stage/foo", "w") as f:
            f.write("staged")

        # Place the to-be-staged file with the same name
        with open("install/foo", "w") as f:
            f.write("installed")

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        runner._migrate_files(files=files, dirs=dirs, srcdir="install", destdir="stage")

        # Verify that the staged file is the one that was staged last
        with open("stage/foo", "r") as f:
            assert (
                f.read() == "installed"
            ), "Expected staging to allow overwriting of already-staged files"

    def test_migrate_files_supports_no_follow_symlinks(self):
        os.makedirs("install")
        os.makedirs("stage")

        with open(os.path.join("install", "foo"), "w") as f:
            f.write("installed")

        os.symlink("foo", os.path.join("install", "bar"))

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        runner._migrate_files(
            files=files,
            dirs=dirs,
            srcdir="install",
            destdir="stage",
            follow_symlinks=False,
        )

        # Verify that the symlink was preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'bar' to still be a symlink."

        assert (
            os.readlink(os.path.join("stage", "bar")) == "foo"
        ), "Expected migrated 'bar' to point to 'foo'"

    def test_migrate_files_preserves_symlink_file(self):
        os.makedirs("install")
        os.makedirs("stage")

        with open(os.path.join("install", "foo"), "w") as f:
            f.write("installed")

        os.symlink("foo", os.path.join("install", "bar"))

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        runner._migrate_files(files=files, dirs=dirs, srcdir="install", destdir="stage")

        # Verify that the symlinks were preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'sym-a' to be a symlink."

    def test_migrate_files_no_follow_symlinks(self):
        os.makedirs("install/usr/bin")
        os.makedirs("stage")

        with open(os.path.join("install", "usr", "bin", "foo"), "w") as f:
            f.write("installed")

        os.symlink("usr/bin", os.path.join("install", "bin"))

        files, dirs = filesets.migratable_filesets(Fileset(["-usr"]), "install")
        runner._migrate_files(files=files, dirs=dirs, srcdir="install", destdir="stage")

        # Verify that the symlinks were preserved
        assert files == {"bin"}
        assert dirs == set()

        assert os.path.islink(
            os.path.join("stage", "bin")
        ), "Expected migrated 'bin' to be a symlink."

    def test_migrate_files_preserves_symlink_nested_file(self):
        os.makedirs(os.path.join("install", "a"))
        os.makedirs("stage")

        with open(os.path.join("install", "a", "foo"), "w") as f:
            f.write("installed")

        os.symlink(os.path.join("a", "foo"), os.path.join("install", "bar"))
        os.symlink(os.path.join("foo"), os.path.join("install", "a", "bar"))

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        runner._migrate_files(files=files, dirs=dirs, srcdir="install", destdir="stage")

        # Verify that the symlinks were preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'sym-a' to be a symlink."

        assert os.path.islink(
            os.path.join("stage", "a", "bar")
        ), "Expected migrated 'a/bar' to be a symlink."

    def test_migrate_files_preserves_symlink_empty_dir(self):
        os.makedirs(os.path.join("install", "foo"))
        os.makedirs("stage")

        os.symlink("foo", os.path.join("install", "bar"))

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        runner._migrate_files(files=files, dirs=dirs, srcdir="install", destdir="stage")

        # Verify that the symlinks were preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'bar' to be a symlink."

    def test_migrate_files_preserves_symlink_nonempty_dir(self):
        os.makedirs(os.path.join("install", "foo"))
        os.makedirs("stage")

        os.symlink("foo", os.path.join("install", "bar"))

        with open(os.path.join("install", "foo", "xfile"), "w") as f:
            f.write("installed")

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        runner._migrate_files(files=files, dirs=dirs, srcdir="install", destdir="stage")

        # Verify that the symlinks were preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'bar' to be a symlink."

    def test_migrate_files_preserves_symlink_nested_dir(self):
        os.makedirs(os.path.join("install", "a", "b"))
        os.makedirs("stage")

        os.symlink(os.path.join("a", "b"), os.path.join("install", "bar"))
        os.symlink(os.path.join("b"), os.path.join("install", "a", "bar"))

        with open(os.path.join("install", "a", "b", "xfile"), "w") as f:
            f.write("installed")

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        runner._migrate_files(files=files, dirs=dirs, srcdir="install", destdir="stage")

        # Verify that the symlinks were preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'bar' to be a symlink."

        assert os.path.islink(
            os.path.join("stage", "a", "bar")
        ), "Expected migrated 'a/bar' to be a symlink."

    def test_migrate_files_supports_follow_symlinks(self):
        os.makedirs("install")
        os.makedirs("stage")

        with open(os.path.join("install", "foo"), "w") as f:
            f.write("installed")

        os.symlink("foo", os.path.join("install", "bar"))

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        runner._migrate_files(
            files=files,
            dirs=dirs,
            srcdir="install",
            destdir="stage",
            follow_symlinks=True,
        )

        # Verify that the symlink was preserved
        assert (
            os.path.islink(os.path.join("stage", "bar")) is False
        ), "Expected migrated 'bar' to no longer be a symlink."

        with open(os.path.join("stage", "bar"), "r") as f:
            assert (
                f.read() == "installed"
            ), "Expected migrated 'bar' to be a copy of 'foo'"

    def test_migrate_files_preserves_file_mode(self):
        os.makedirs("install")
        os.makedirs("stage")

        foo = os.path.join("install", "foo")

        with open(foo, "w") as f:
            f.write("installed")

        mode = os.stat(foo).st_mode

        new_mode = 0o777
        os.chmod(foo, new_mode)
        assert mode != new_mode

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        runner._migrate_files(
            files=files,
            dirs=dirs,
            srcdir="install",
            destdir="stage",
            follow_symlinks=True,
        )

        assert new_mode == stat.S_IMODE(os.stat(os.path.join("stage", "foo")).st_mode)

    # TODO: add test_migrate_files_preserves_file_mode_chown_permissions

    def test_migrate_files_preserves_directory_mode(self):
        os.makedirs("install/foo")
        os.makedirs("stage")

        foo = os.path.join("install", "foo", "bar")

        with open(foo, "w") as f:
            f.write("installed")

        mode = os.stat(foo).st_mode

        new_mode = 0o777
        assert mode != new_mode
        os.chmod(os.path.dirname(foo), new_mode)
        os.chmod(foo, new_mode)

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        runner._migrate_files(
            files=files,
            dirs=dirs,
            srcdir="install",
            destdir="stage",
            follow_symlinks=True,
        )

        assert new_mode == stat.S_IMODE(os.stat(os.path.join("stage", "foo")).st_mode)
        assert new_mode == stat.S_IMODE(
            os.stat(os.path.join("stage", "foo", "bar")).st_mode
        )
