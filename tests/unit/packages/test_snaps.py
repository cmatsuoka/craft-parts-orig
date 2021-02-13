# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2017-2021 Canonical Ltd
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
from unittest.mock import call

import pytest

from craft_parts.packages import errors, snaps

# pylint: disable=missing-class-docstring


class TestSnapPackageCurrentChannel:
    def assert_channels(self, *, snap, installed_snaps, expected, fake_snapd):
        fake_snapd.snaps_result = installed_snaps
        snap_pkg = snaps.SnapPackage(snap)
        assert snap_pkg.get_current_channel() == expected

    def test_risk(self, fake_snapd):
        self.assert_channels(
            snap="fake-snap-stable/stable",
            installed_snaps=[{"name": "fake-snap-stable", "channel": "stable"}],
            expected="latest/stable",
            fake_snapd=fake_snapd,
        )

    def test_track_risk(self, fake_snapd):
        self.assert_channels(
            snap="fake-snap-stable/latest/stable",
            installed_snaps=[{"name": "fake-snap-stable", "channel": "stable"}],
            expected="latest/stable",
            fake_snapd=fake_snapd,
        )

    def test_track_risk_branch(self, fake_snapd):
        self.assert_channels(
            snap="fake-snap-branch/candidate/branch",
            installed_snaps=[
                {"name": "fake-snap-branch", "channel": "candidate/branch"}
            ],
            expected="latest/candidate/branch",
            fake_snapd=fake_snapd,
        )


class TestPackageIsInstalled:
    def assert_installed(self, snap, installed_snaps, expected, fake_snapd):
        fake_snapd.snaps_result = installed_snaps
        snap_pkg = snaps.SnapPackage(snap)
        assert snap_pkg.installed is expected
        assert snaps.SnapPackage.is_snap_installed(snap) is expected

    def test_default(self, fake_snapd):
        self.assert_installed(
            snap="fake-snap-stable",
            installed_snaps=[{"name": "fake-snap-stable", "channel": "stable"}],
            expected=True,
            fake_snapd=fake_snapd,
        )

    def test_track_risk(self, fake_snapd):
        self.assert_installed(
            snap="fake-snap-stable/latest/stable",
            installed_snaps=[{"name": "fake-snap-stable", "channel": "stable"}],
            expected=True,
            fake_snapd=fake_snapd,
        )

    def test_default_not_installed(self, fake_snapd):
        self.assert_installed(
            snap="missing-snap",
            installed_snaps=[],
            expected=False,
            fake_snapd=fake_snapd,
        )

    def test_track_risk_not_installed(self, fake_snapd):
        self.assert_installed(
            snap="missing-snap/latest/stable",
            installed_snaps=[],
            expected=False,
            fake_snapd=fake_snapd,
        )


class TestPackageIsInStore:
    def assert_in_store(self, snap, find_result, expected, fake_snapd):
        fake_snapd.find_result = find_result
        snap_pkg = snaps.SnapPackage(snap)
        assert snap_pkg.in_store is expected

    def test_default(self, fake_snapd):
        self.assert_in_store(
            snap="fake-snap",
            find_result=[{"fake-snap": "dummy"}],
            expected=True,
            fake_snapd=fake_snapd,
        )

    def test_track_risk(self, fake_snapd):
        self.assert_in_store(
            snap="fake-snap/latest/stable",
            find_result=[{"fake-snap": "dummy"}],
            expected=True,
            fake_snapd=fake_snapd,
        )

    def test_default_not_in_store(self, fake_snapd):
        self.assert_in_store(
            snap="missing-snap", find_result=[], expected=False, fake_snapd=fake_snapd
        )

    def test_track_risk_not_in_store(self, fake_snapd):
        self.assert_in_store(
            snap="missing-snap/latest/stable",
            find_result=[],
            expected=False,
            fake_snapd=fake_snapd,
        )


class TestSnapPackageIsClassic:
    def assert_classic(self, snap, find_result, expected, fake_snapd):
        fake_snapd.find_result = find_result
        snap_pkg = snaps.SnapPackage(snap)
        assert snap_pkg.is_classic() is expected

    def test_classic(self, fake_snapd):
        self.assert_classic(
            snap="fake-snap/classic/stable",
            find_result=[
                {
                    "fake-snap": {
                        "channels": {"classic/stable": {"confinement": "classic"}}
                    }
                }
            ],
            expected=True,
            fake_snapd=fake_snapd,
        )

    def test_strict(self, fake_snapd):
        self.assert_classic(
            snap="fake-snap/strict/stable",
            find_result=[
                {
                    "fake-snap": {
                        "channels": {"strict/stable": {"confinement": "strict"}}
                    }
                }
            ],
            expected=False,
            fake_snapd=fake_snapd,
        )

    def test_devmode(self, fake_snapd):
        self.assert_classic(
            snap="fake-snap/devmode/stable",
            find_result=[
                {
                    "fake-snap": {
                        "channels": {"devmode/stable": {"confinement": "devmode"}}
                    }
                }
            ],
            expected=False,
            fake_snapd=fake_snapd,
        )


class TestSnapPackageIsValid:
    def assert_valid(self, snap, find_result, expected, fake_snapd):
        fake_snapd.find_result = find_result
        snap_pkg = snaps.SnapPackage(snap)
        assert snap_pkg.is_valid() is expected
        assert snaps.SnapPackage.is_valid_snap(snap) is expected

    def test_default(self, fake_snapd):
        self.assert_valid(
            snap="fake-snap",
            find_result=[
                {
                    "fake-snap": {
                        "channels": {"latest/stable": {"confinement": "strict"}}
                    }
                }
            ],
            expected=True,
            fake_snapd=fake_snapd,
        )

    def test_track_risk(self, fake_snapd):
        self.assert_valid(
            snap="fake-snap/strict/stable",
            find_result=[
                {
                    "fake-snap": {
                        "channels": {"strict/stable": {"confinement": "strict"}}
                    }
                }
            ],
            expected=True,
            fake_snapd=fake_snapd,
        )

    def test_invalid_track(self, fake_snapd):
        self.assert_valid(
            snap="fake-snap/non-existent/edge",
            find_result=[
                {
                    "fake-snap": {
                        "channels": {"strict/stable": {"confinement": "strict"}}
                    }
                }
            ],
            expected=False,
            fake_snapd=fake_snapd,
        )

    def test_missing_snap(self, fake_snapd):
        self.assert_valid(
            snap="missing-snap", find_result=[], expected=False, fake_snapd=fake_snapd
        )


@pytest.mark.usefixtures("new_dir")
class TestSnapPackageLifecycle:
    def test_install_classic(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"classic/stable": {"confinement": "classic"}}}}
        ]

        snap_pkg = snaps.SnapPackage("fake-snap/classic/stable")
        snap_pkg.install()
        assert fake_snap_command.calls == [
            ["snap", "whoami"],
            [
                "sudo",
                "snap",
                "install",
                "fake-snap",
                "--channel",
                "classic/stable",
                "--classic",
            ],
        ]

    def test_install_non_classic(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"strict/stable": {"confinement": "strict"}}}}
        ]

        snap_pkg = snaps.SnapPackage("fake-snap/strict/stable")
        snap_pkg.install()
        assert fake_snap_command.calls == [
            ["snap", "whoami"],
            [
                "sudo",
                "snap",
                "install",
                "fake-snap",
                "--channel",
                "strict/stable",
            ],
        ]

    def test_download_from_host(self, fake_snapd, mocker):
        fake_get_assertion = mocker.patch(
            "craft_parts.packages.snaps.get_assertion", return_value=b"foo-assert"
        )

        fake_snapd.snaps_result = [
            {
                "id": "fake-snap-id",
                "name": "fake-snap",
                "channel": "stable",
                "revision": "10",
            }
        ]

        snap_pkg = snaps.SnapPackage("fake-snap/strict/stable")
        snap_pkg.local_download(
            snap_path="fake-snap.snap", assertion_path="fake-snap.assert"
        )

        assert os.path.isfile("fake-snap.snap")
        with open("fake-snap.assert", "r") as f:
            assert f.read() == "foo-assert\nfoo-assert\nfoo-assert\n"

        # pylint: disable=line-too-long
        assert fake_get_assertion.mock_calls == [
            call(
                [
                    "account-key",
                    "public-key-sha3-384=BWDEoaqyr25nF5SNCvEv2v7QnM9QsfCc0PBMYD_i2NGSQ32EF2d4D0hqUel3m8ul",
                ]
            ),
            call(["snap-declaration", "snap-name=fake-snap"]),
            call(["snap-revision", "snap-revision=10", "snap-id=fake-snap-id"]),
        ]

    def test_download_from_host_dangerous(self, fake_snapd, mocker):
        fake_get_assertion = mocker.patch(
            "craft_parts.packages.snaps.get_assertion", return_value=b"foo-assert"
        )
        fake_snapd.snaps_result = [
            {
                "id": "fake-snap-id",
                "name": "fake-snap",
                "channel": "stable",
                "revision": "x1",
            }
        ]

        snap_pkg = snaps.SnapPackage("fake-snap/strict/stable")
        snap_pkg.local_download(
            snap_path="fake-snap.snap", assertion_path="fake-snap.assert"
        )

        assert os.path.isfile("fake-snap.snap")
        with open("fake-snap.assert", "r") as f:
            assert f.read() == ""
        fake_get_assertion.assert_not_called()

    def test_install_logged_in(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"strict/stable": {"confinement": "strict"}}}}
        ]

        fake_snap_command.login("user@email.com")
        snap_pkg = snaps.SnapPackage("fake-snap/strict/stable")
        snap_pkg.install()
        assert fake_snap_command.calls == [
            ["snap", "whoami"],
            ["snap", "install", "fake-snap", "--channel", "strict/stable"],
        ]

    def test_install_fails(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"strict/stable": {"confinement": "strict"}}}}
        ]

        fake_snap_command.install_success = False
        snap_pkg = snaps.SnapPackage("fake-snap/strict/stable")
        with pytest.raises(errors.SnapInstallError):
            snap_pkg.install()

    def test_refresh(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"strict/stable": {"confinement": "strict"}}}}
        ]

        snap_pkg = snaps.SnapPackage("fake-snap/strict/stable")
        snap_pkg.refresh()
        assert fake_snap_command.calls == [
            ["snap", "whoami"],
            [
                "sudo",
                "snap",
                "refresh",
                "fake-snap",
                "--channel",
                "strict/stable",
            ],
        ]

    def test_download(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"strict/stable": {"confinement": "strict"}}}}
        ]

        snap_pkg = snaps.SnapPackage("fake-snap")
        snap_pkg.download()
        assert fake_snap_command.calls == [["snap", "download", "fake-snap"]]

    def test_download_channel(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"strict/edge": {"confinement": "strict"}}}}
        ]

        snap_pkg = snaps.SnapPackage("fake-snap/strict/stable")
        snap_pkg.download()
        assert fake_snap_command.calls == [
            ["snap", "download", "fake-snap", "--channel", "strict/stable"]
        ]

    def test_download_classic(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"classic/stable": {"confinement": "classic"}}}}
        ]

        snap_pkg = snaps.SnapPackage("fake-snap")
        snap_pkg.download()
        assert fake_snap_command.calls == [["snap", "download", "fake-snap"]]

    def test_download_snaps(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"latest/stable": {"confinement": "strict"}}}},
            {
                "other-fake-snap": {
                    "channels": {"latest/stable": {"confinement": "strict"}}
                }
            },
        ]

        snaps.download_snaps(
            snaps_list=["fake-snap", "other-fake-snap/latest/stable"],
            directory="fakedir",
        )
        assert fake_snap_command.calls == [
            ["snap", "download", "fake-snap"],
            [
                "snap",
                "download",
                "other-fake-snap",
                "--channel",
                "latest/stable",
            ],
        ]

    def test_download_snaps_with_invalid(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"latest/stable": {"confinement": "strict"}}}},
            {
                "other-fake-snap": {
                    "channels": {"latest/stable": {"confinement": "strict"}}
                }
            },
        ]

        with pytest.raises(errors.SnapUnavailableError):
            snaps.download_snaps(
                snaps_list=["fake-snap", "other-invalid"], directory="fakedir"
            )

        assert fake_snap_command.calls == [["snap", "download", "fake-snap"]]

    def test_refresh_to_classic(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"classic/stable": {"confinement": "classic"}}}}
        ]

        snap_pkg = snaps.SnapPackage("fake-snap/classic/stable")
        snap_pkg.refresh()
        assert fake_snap_command.calls == [
            ["snap", "whoami"],
            [
                "sudo",
                "snap",
                "refresh",
                "fake-snap",
                "--channel",
                "classic/stable",
                "--classic",
            ],
        ]

    def test_refresh_logged_in(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"strict/stable": {"confinement": "strict"}}}}
        ]

        fake_snap_command.login("user@email.com")
        snap_pkg = snaps.SnapPackage("fake-snap/strict/stable")
        snap_pkg.refresh()
        assert fake_snap_command.calls == [
            ["snap", "whoami"],
            ["snap", "refresh", "fake-snap", "--channel", "strict/stable"],
        ]

    def test_refresh_fails(self, fake_snapd, fake_snap_command):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"strict/stable": {"confinement": "strict"}}}}
        ]

        snap_pkg = snaps.SnapPackage("fake-snap/strict/stable")
        fake_snap_command.refresh_success = False
        with pytest.raises(errors.SnapRefreshError):
            snap_pkg.refresh()

    def test_install_snaps_returns_revision(self, fake_snapd):
        fake_snapd.find_result = [
            {
                "fake-snap": {
                    "channel": "stable",
                    "type": "app",
                    "channels": {"latest/stable": {"confinement": "strict"}},
                }
            }
        ]
        fake_snapd.snaps_result = [
            {
                "name": "fake-snap",
                "channel": "stable",
                "revision": "test-fake-snap-revision",
            }
        ]

        installed_snaps = snaps.install_snaps(["fake-snap"])
        assert installed_snaps == ["fake-snap=test-fake-snap-revision"]

    def test_install_snaps_non_stable_base(self, fake_snapd):
        fake_snapd.find_result = [
            {
                "fake-base-snap": {
                    "channel": "beta",
                    "type": "base",
                    "channels": {"latest/beta": {"confinement": "strict"}},
                }
            }
        ]
        fake_snapd.snaps_result = [
            {
                "name": "fake-base-snap",
                "channel": "beta",
                "revision": "test-fake-base-snap-revision",
            }
        ]

        installed_snaps = snaps.install_snaps(["fake-base-snap"])
        assert installed_snaps == ["fake-base-snap=test-fake-base-snap-revision"]

    def test_install_snaps_non_existent_snap(self, fake_snapd):
        fake_snapd.find_code = 404
        with pytest.raises(errors.SnapUnavailableError):
            snaps.install_snaps("fake-snap")

    def test_install_snaps_non_existent_channel(self, fake_snapd):
        fake_snapd.find_result = [
            {
                "fake-snap": {
                    "channel": "stable",
                    "type": "app",
                    "channels": {"latest/stable": {"confinement": "strict"}},
                }
            }
        ]

        with pytest.raises(errors.SnapUnavailableError):
            snaps.install_snaps("fake-snap/non-existent/edge")

    def test_install_snaps_refresh_to_invalid_channel(self, fake_snapd):
        fake_snapd.find_result = [
            {"fake-snap": {"channels": {"strict/edge": {"confinement": "strict"}}}}
        ]

        with pytest.raises(errors.SnapUnavailableError):
            snaps.install_snaps("fake-snap/strict/stable")


class TestInstalledSnaps:
    def test_get_installed_snaps(self, fake_snapd):
        fake_snapd.snaps_result = [
            {"name": "test-snap-1", "revision": "test-snap-1-revision"},
            {"name": "test-snap-2", "revision": "test-snap-2-revision"},
        ]
        installed_snaps = snaps.get_installed_snaps()
        assert installed_snaps == [
            "test-snap-1=test-snap-1-revision",
            "test-snap-2=test-snap-2-revision",
        ]


class TestSnapdNotInstalled:
    def test_get_installed_snaps(self, mocker):
        mocker.patch(
            "craft_parts.packages.snaps.get_snapd_socket_path_template",
            return_value="http+unix://nonexisting",
        )

        installed_snaps = snaps.get_installed_snaps()
        assert installed_snaps == []
