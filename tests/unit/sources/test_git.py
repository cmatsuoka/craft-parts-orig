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
import subprocess
from typing import List
from unittest import mock

import pytest

from craft_parts.sources import errors, sources


def _call(cmd: List[str]) -> None:
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _call_with_output(cmd: List[str]) -> str:
    return subprocess.check_output(cmd).decode("utf-8").strip()


def _fake_git_command_error(*args, **kwargs):
    raise subprocess.CalledProcessError(44, ["git"], output=b"git: some error")


@pytest.fixture
def mock_get_source_details(mocker) -> None:
    mocker.patch("craft_parts.sources.git.Git._get_source_details", return_value="")


@pytest.fixture
def fake_check_output(mocker):
    return mocker.patch("subprocess.check_output")


@pytest.fixture
def fake_run(mocker):
    return mocker.patch("subprocess.check_call")


# pylint: disable=attribute-defined-outside-init
# pylint: disable=missing-class-docstring
# pylint: disable=too-many-public-methods


# LP: #1733584
@pytest.mark.usefixtures("mock_get_source_details")
class TestGit:
    def test_pull(self, fake_run):
        git = sources.Git("git://my-source", "source_dir")
        git.pull()

        fake_run.assert_called_once_with(
            ["git", "clone", "--recursive", "git://my-source", "source_dir"]
        )

    def test_add(self, fake_check_output):
        url = "git://my-source"
        source_dir = "source_dir"

        git = sources.Git(url, source_dir)
        git.add("file")
        fake_check_output.assert_called_once_with(
            ["git", "-C", "source_dir", "add", "file"]
        )

    def test_add_error(self, fake_check_output):
        fake_check_output.side_effect = _fake_git_command_error
        url = "git://my-source"
        source_dir = "source_dir"

        git = sources.Git(url, source_dir)

        with pytest.raises(errors.GitCommandError) as raised:
            git.add("file")
        assert str(raised.value) == (
            "Git command 'git -C source_dir add file' failed with code 44: "
            "git: some error"
        )

    def test_add_abs_path(self, fake_check_output):
        url = "git://my-source"
        source_dir = "source_dir"

        git = sources.Git(url, source_dir)
        git.add(os.path.join(source_dir, "file"))
        fake_check_output.assert_called_once_with(
            ["git", "-C", "source_dir", "add", "file"]
        )

    def test_commit(self, fake_check_output):
        url = "git://my-source"
        source_dir = "source_dir"

        git = sources.Git(url, source_dir)
        git.commit(message="message", author="author")

        fake_check_output.assert_called_once_with(
            [
                "git",
                "-C",
                "source_dir",
                "commit",
                "--no-gpg-sign",
                "--message",
                "message",
                "--author",
                "author",
            ]
        )

    def test_commit_error(self, fake_check_output):
        fake_check_output.side_effect = _fake_git_command_error
        url = "git://my-source"
        source_dir = "source_dir"

        git = sources.Git(url, source_dir)

        with pytest.raises(errors.GitCommandError) as raised:
            git.commit(message="message", author="author")
        assert str(raised.value) == (
            "Git command 'git -C source_dir commit --no-gpg-sign --message message "
            "--author author' failed with code 44: git: some error"
        )

    def test_init(self, fake_check_output):
        url = "git://my-source"
        source_dir = "source_dir"

        git = sources.Git(url, source_dir)
        git.init()
        fake_check_output.assert_called_once_with(["git", "-C", "source_dir", "init"])

    def test_init_error(self, fake_check_output):
        fake_check_output.side_effect = _fake_git_command_error
        url = "git://my-source"
        source_dir = "source_dir"

        git = sources.Git(url, source_dir)

        with pytest.raises(errors.GitCommandError) as raised:
            git.init()
        assert str(raised.value) == (
            "Git command 'git -C source_dir init' failed with code 44: git: some error"
        )

    def test_push(self, fake_check_output):
        url = "git://my-source"
        refspec = "HEAD:master"
        source_dir = "source_dir"

        git = sources.Git(url, source_dir)
        git.push(url, refspec)
        fake_check_output.assert_called_once_with(
            ["git", "-C", "source_dir", "push", url, refspec]
        )

    def test_push_force(self, fake_check_output):
        url = "git://my-source"
        refspec = "HEAD:master"
        source_dir = "source_dir"

        git = sources.Git(url, source_dir)
        git.push(url, refspec, force=True)
        fake_check_output.assert_called_once_with(
            ["git", "-C", "source_dir", "push", url, refspec, "--force"]
        )

    def test_push_error(self, fake_check_output):
        fake_check_output.side_effect = _fake_git_command_error
        url = "git://my-source"
        refspec = "HEAD:master"
        source_dir = "source_dir"

        git = sources.Git(url, source_dir)

        with pytest.raises(errors.GitCommandError) as raised:
            git.push(url, refspec)
        assert str(raised.value) == (
            "Git command 'git -C source_dir push git://my-source HEAD:master' failed "
            "with code 44: git: some error"
        )

    def test_pull_with_depth(self, fake_run):
        git = sources.Git("git://my-source", "source_dir", source_depth=2)

        git.pull()

        fake_run.assert_called_once_with(
            [
                "git",
                "clone",
                "--recursive",
                "--depth",
                "2",
                "git://my-source",
                "source_dir",
            ]
        )

    def test_pull_branch(self, fake_run):
        git = sources.Git("git://my-source", "source_dir", source_branch="my-branch")
        git.pull()

        fake_run.assert_called_once_with(
            [
                "git",
                "clone",
                "--recursive",
                "--branch",
                "my-branch",
                "git://my-source",
                "source_dir",
            ]
        )

    def test_pull_tag(self, fake_run):
        git = sources.Git("git://my-source", "source_dir", source_tag="tag")
        git.pull()

        fake_run.assert_called_once_with(
            [
                "git",
                "clone",
                "--recursive",
                "--branch",
                "tag",
                "git://my-source",
                "source_dir",
            ]
        )

    def test_pull_commit(self, fake_run):
        git = sources.Git(
            "git://my-source",
            "source_dir",
            source_commit="2514f9533ec9b45d07883e10a561b248497a8e3c",
        )
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    ["git", "clone", "--recursive", "git://my-source", "source_dir"]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "origin",
                        "2514f9533ec9b45d07883e10a561b248497a8e3c",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "checkout",
                        "2514f9533ec9b45d07883e10a561b248497a8e3c",
                    ]
                ),
            ]
        )

    def test_pull_existing(self, mocker, fake_run):
        mocker.patch("os.path.exists", return_value=True)

        git = sources.Git("git://my-source", "source_dir")
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(
                    ["git", "-C", "source_dir", "reset", "--hard", "origin/master"]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                    ]
                ),
            ]
        )

    def test_pull_existing_with_tag(self, mocker, fake_run):
        mocker.patch("os.path.exists", return_value=True)

        git = sources.Git("git://my-source", "source_dir", source_tag="tag")
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(
                    ["git", "-C", "source_dir", "reset", "--hard", "refs/tags/tag"]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                    ]
                ),
            ]
        )

    def test_pull_existing_with_commit(self, mocker, fake_run):
        mocker.patch("os.path.exists", return_value=True)

        git = sources.Git(
            "git://my-source",
            "source_dir",
            source_commit="2514f9533ec9b45d07883e10a561b248497a8e3c",
        )
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "reset",
                        "--hard",
                        "2514f9533ec9b45d07883e10a561b248497a8e3c",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                    ]
                ),
            ]
        )

    def test_pull_existing_with_branch(self, mocker, fake_run):
        mocker.patch("os.path.exists", return_value=True)

        git = sources.Git("git://my-source", "source_dir", source_branch="my-branch")
        git.pull()

        fake_run.assert_has_calls(
            [
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "fetch",
                        "--prune",
                        "--recurse-submodules=yes",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "reset",
                        "--hard",
                        "refs/heads/my-branch",
                    ]
                ),
                mock.call(
                    [
                        "git",
                        "-C",
                        "source_dir",
                        "submodule",
                        "update",
                        "--recursive",
                        "--force",
                    ]
                ),
            ]
        )

    def test_init_with_source_branch_and_tag_raises_exception(self):
        with pytest.raises(sources.errors.IncompatibleSourceOptions) as raised:
            sources.Git(
                "git://mysource",
                "source_dir",
                source_tag="tag",
                source_branch="branch",
            )
        assert str(raised.value) == (
            "Failed to pull source: cannot specify both 'source-branch' and "
            "'source-tag' for a git source.\n"
        )

    def test_init_with_source_branch_and_commit_raises_exception(self):
        with pytest.raises(sources.errors.IncompatibleSourceOptions) as raised:
            sources.Git(
                "git://mysource",
                "source_dir",
                source_commit="2514f9533ec9b45d07883e10a561b248497a8e3c",
                source_branch="branch",
            )
        assert str(raised.value) == (
            "Failed to pull source: cannot specify both 'source-branch' and "
            "'source-commit' for a git source.\n"
        )

    def test_init_with_source_tag_and_commit_raises_exception(self):
        with pytest.raises(sources.errors.IncompatibleSourceOptions) as raised:
            sources.Git(
                "git://mysource",
                "source_dir",
                source_commit="2514f9533ec9b45d07883e10a561b248497a8e3c",
                source_tag="tag",
            )
        assert str(raised.value) == (
            "Failed to pull source: cannot specify both 'source-commit' and "
            "'source-tag' for a git source.\n"
        )

    def test_source_checksum_raises_exception(self):
        with pytest.raises(sources.errors.InvalidSourceOption) as raised:
            sources.Git(
                "git://mysource",
                "source_dir",
                source_checksum="md5/d9210476aac5f367b14e513bdefdee08",
            )
        assert str(raised.value) == (
            "Failed to pull source: 'source-checksum' cannot be used with a git source."
        )

    def test_has_source_handler_entry(self):
        assert sources._source_handler["git"] is sources.Git

    def test_pull_failure(self, fake_run):
        fake_run.side_effect = subprocess.CalledProcessError(1, [])

        git = sources.Git("git://my-source", "source_dir")
        with pytest.raises(sources.errors.PullError) as raised:
            git.pull()
        assert str(raised.value) == (
            "Failed to pull source: command 'git clone --recursive git://my-source "
            "source_dir' exited with code 1."
        )


@pytest.mark.usefixtures("new_dir")
class GitBaseTestCase:
    def rm_dir(self, dir_name):
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

    def clean_dir(self, dir_name):
        self.rm_dir(dir_name)
        os.mkdir(dir_name)

    def clone_repo(self, repo, tree):
        self.clean_dir(tree)
        _call(["git", "clone", repo, tree])
        os.chdir(tree)
        _call(["git", "config", "--local", "user.name", '"Example Dev"'])
        _call(["git", "config", "--local", "user.email", "dev@example.com"])

    def add_file(self, filename, body, message):
        with open(filename, "w") as fp:
            fp.write(body)

        _call(["git", "add", filename])
        _call(["git", "commit", "-am", message])

    def check_file_contents(self, path, expected):
        body = None
        with open(path) as fp:
            body = fp.read()
        assert body == expected


@pytest.mark.usefixtures("new_dir")
class TestGitConflicts(GitBaseTestCase):
    """Test that git pull errors don't kill the parser"""

    def test_git_conflicts(self):
        repo = os.path.abspath("conflict-test.git")
        working_tree = os.path.abspath("git-conflict-test")
        conflicting_tree = "{}-conflict".format(working_tree)
        git = sources.Git(repo, working_tree, silent=True)

        self.clean_dir(repo)
        self.clean_dir(working_tree)
        self.clean_dir(conflicting_tree)

        os.chdir(repo)
        _call(["git", "init", "--bare"])

        self.clone_repo(repo, working_tree)

        # check out the original repo
        self.clone_repo(repo, conflicting_tree)

        # add a file to the repo
        os.chdir(working_tree)
        self.add_file("fake", "fake 1", "fake 1")
        _call(["git", "push", repo])

        git.pull()

        os.chdir(conflicting_tree)
        self.add_file("fake", "fake 2", "fake 2")
        _call(["git", "push", "-f", repo])

        os.chdir(working_tree)
        git.pull()

        body = None
        with open(os.path.join(working_tree, "fake")) as fp:
            body = fp.read()

        assert body == "fake 2"

    def test_git_submodules(self):
        """Test that updates to submodules are pulled"""
        repo = os.path.abspath("submodules.git")
        sub_repo = os.path.abspath("subrepo")
        working_tree = os.path.abspath("git-submodules")
        working_tree_two = "{}-two".format(working_tree)
        sub_working_tree = os.path.abspath("git-submodules-sub")
        git = sources.Git(repo, working_tree, silent=True)

        self.clean_dir(repo)
        self.clean_dir(sub_repo)
        self.clean_dir(working_tree)
        self.clean_dir(working_tree_two)
        self.clean_dir(sub_working_tree)

        os.chdir(sub_repo)
        _call(["git", "init", "--bare"])

        self.clone_repo(sub_repo, sub_working_tree)
        self.add_file("sub-file", "sub-file", "sub-file")
        _call(["git", "push", sub_repo])

        os.chdir(repo)
        _call(["git", "init", "--bare"])

        self.clone_repo(repo, working_tree)
        _call(["git", "submodule", "add", sub_repo])
        _call(["git", "commit", "-am", "added submodule"])
        _call(["git", "push", repo])

        git.pull()

        self.check_file_contents(
            os.path.join(working_tree, "subrepo", "sub-file"), "sub-file"
        )

        # add a file to the repo
        os.chdir(sub_working_tree)
        self.add_file("fake", "fake 1", "fake 1")
        _call(["git", "push", sub_repo])

        os.chdir(working_tree)
        git.pull()

        # this shouldn't cause any change
        self.check_file_contents(
            os.path.join(working_tree, "subrepo", "sub-file"), "sub-file"
        )
        assert os.path.exists(os.path.join(working_tree, "subrepo", "fake")) is False

        # update the submodule
        self.clone_repo(repo, working_tree_two)
        _call(["git", "submodule", "update", "--init", "--recursive", "--remote"])
        _call(["git", "add", "subrepo"])
        _call(["git", "commit", "-am", "updated submodule"])
        _call(["git", "push"])

        os.chdir(working_tree)
        git.pull()

        # new file should be there now
        self.check_file_contents(
            os.path.join(working_tree, "subrepo", "sub-file"), "sub-file"
        )
        self.check_file_contents(
            os.path.join(working_tree, "subrepo", "fake"), "fake 1"
        )


class TestGitDetails(GitBaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):  # pylint: disable=unused-argument
        def _add_and_commit_file(filename, content=None, message=None):
            if not content:
                content = filename

            if not message:
                message = filename

            with open(filename, "w") as fp:
                fp.write(content)

            _call(["git", "add", filename])
            _call(["git", "commit", "-am", message])

        self.working_tree = "git-test"
        self.source_dir = "git-checkout"
        self.clean_dir(self.working_tree)
        os.chdir(self.working_tree)
        _call(["git", "init"])
        _call(["git", "config", "user.name", '"Example Dev"'])
        _call(["git", "config", "user.email", "dev@example.com"])
        _add_and_commit_file("testing")
        self.expected_commit = _call_with_output(["git", "rev-parse", "HEAD"])

        _add_and_commit_file("testing-2")
        _call(["git", "tag", "test-tag"])
        self.expected_tag = "test-tag"

        _add_and_commit_file("testing-3")
        self.expected_branch = "test-branch"
        _call(["git", "branch", self.expected_branch])

        os.chdir("..")

        self.git = sources.Git(
            self.working_tree,
            self.source_dir,
            silent=True,
            source_commit=self.expected_commit,
        )
        self.git.pull()

        self.source_details = self.git._get_source_details()

    def test_git_details_commit(self):
        assert self.source_details["source-commit"] == self.expected_commit

    def test_git_details_branch(self):
        shutil.rmtree(self.source_dir)
        self.git = sources.Git(
            self.working_tree,
            self.source_dir,
            silent=True,
            source_branch=self.expected_branch,
        )
        self.git.pull()

        self.source_details = self.git._get_source_details()
        assert self.source_details["source-branch"] == self.expected_branch

    def test_git_details_tag(self):
        self.git = sources.Git(
            self.working_tree, self.source_dir, silent=True, source_tag="test-tag"
        )
        self.git.pull()

        self.source_details = self.git._get_source_details()
        assert self.source_details["source-tag"] == self.expected_tag


class TestGitGenerateVersion:
    @pytest.mark.parametrize(
        "return_value,expected",
        [
            ("2.28", "2.28"),  # only_tag
            ("2.28-28-gabcdef1", "2.28+git28.abcdef1"),  # tag+commits
            ("2.28-29-gabcdef1-dirty", "2.28+git29.abcdef1-dirty"),  # tag+dirty
        ],
    )
    def test_version(self, mocker, return_value, expected):
        mocker.patch("subprocess.check_output", return_value=return_value.encode())
        assert sources.Git.generate_version() == expected


class TestGitGenerateVersionNoTag:
    def test_version(self, mocker, fake_check_output):
        popen_mock = mocker.patch("subprocess.Popen")

        fake_check_output.side_effect = subprocess.CalledProcessError(1, [])
        proc_mock = mock.Mock()
        proc_mock.returncode = 0
        proc_mock.communicate.return_value = (b"abcdef1", b"")
        popen_mock.return_value = proc_mock

        expected = "0+git.abcdef1"
        assert sources.Git.generate_version() == expected


class TestGitGenerateVersionNoGit:
    def test_version(self, mocker, fake_check_output):
        popen_mock = mocker.patch("subprocess.Popen")

        fake_check_output.side_effect = subprocess.CalledProcessError(1, [])
        proc_mock = mock.Mock()
        proc_mock.returncode = 2
        proc_mock.communicate.return_value = (b"", b"No .git")
        popen_mock.return_value = proc_mock

        with pytest.raises(sources.errors.VCSError):
            sources.Git.generate_version()
