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

import contextlib
import textwrap
from pathlib import Path
from subprocess import CalledProcessError
from unittest import mock
from unittest.mock import call

import pytest

from craft_parts.packages import _deb, errors

# pylint: disable=line-too-long
# pylint: disable=missing-class-docstring
# pylint: disable=unused-argument


@pytest.fixture(autouse=True)
def mock_env_copy():
    with mock.patch("os.environ.copy", return_value=dict()) as m:
        yield m


@pytest.fixture
def fake_apt_cache(mocker):
    def get_installed_version(package_name, resolve_virtual_packages=False):
        return "1.0" if "installed" in package_name else None

    fake = mocker.patch("craft_parts.packages._deb.AptCache")
    fake.return_value.__enter__.return_value.get_installed_version.side_effect = (
        get_installed_version
    )
    return fake


@pytest.fixture
def fake_run(mocker):
    return mocker.patch("subprocess.check_call")


@pytest.fixture
def fake_dumb_terminal(mocker):
    return mocker.patch(
        "craft_parts.utils.os_utils.is_dumb_terminal", return_value=True
    )


@pytest.fixture(autouse=True)
def cache_dirs(mocker, tmpdir):
    stage_cache_path = Path(tmpdir, "stage-cache")
    debs_path = Path(tmpdir, "debs")
    debs_path.mkdir(parents=True, exist_ok=False)

    mocker.patch(
        "craft_parts.packages._deb.get_cache_dirs",
        return_value=(stage_cache_path, debs_path),
    )

    @contextlib.contextmanager
    def fake_tempdir(*, suffix: str, **kwargs):
        temp_dir = Path(tmpdir, suffix)
        temp_dir.mkdir(exist_ok=True, parents=True)
        yield str(temp_dir)

    mocker.patch(
        "craft_parts.packages._deb.tempfile.TemporaryDirectory",
        new=fake_tempdir,
    )


class TestPackages:
    def test_fetch_stage_packages(self, tmpdir, fake_apt_cache):
        stage_cache_path, debs_path = _deb.get_cache_dirs("test")
        fake_package = debs_path / "fake-package_1.0_all.deb"
        fake_package.touch()
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.return_value = [
            ("fake-package", "1.0", fake_package)
        ]

        fetched_packages = _deb.Ubuntu.fetch_stage_packages(
            application_name="test",
            package_names=["fake-package"],
            stage_packages_path=Path(tmpdir),
            base="core",
            target_arch="amd64",
        )

        fake_apt_cache.assert_has_calls(
            [
                call(stage_cache=stage_cache_path, stage_cache_arch="amd64"),
                call().__enter__(),
                call().__enter__().mark_packages({"fake-package"}),
                call()
                .__enter__()
                .unmark_packages(
                    required_names={"fake-package"},
                    filtered_names=set(_deb._DEFAULT_FILTERED_STAGE_PACKAGES),
                ),
                call().__enter__().fetch_archives(debs_path),
            ]
        )

        assert fetched_packages == ["fake-package=1.0"]

    def test_fetch_virtual_stage_package(self, tmpdir, fake_apt_cache):
        _, debs_path = _deb.get_cache_dirs("test")
        fake_package = debs_path / "fake-package_1.0_all.deb"
        fake_package.touch()
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.return_value = [
            ("fake-package", "1.0", fake_package)
        ]

        fetched_packages = _deb.Ubuntu.fetch_stage_packages(
            application_name="test",
            package_names=["virtual-fake-package"],
            stage_packages_path=Path(tmpdir),
            base="core",
            target_arch="amd64",
        )

        assert fetched_packages == ["fake-package=1.0"]

    def test_fetch_stage_package_with_deps(self, tmpdir, fake_apt_cache):
        _, debs_path = _deb.get_cache_dirs("test")
        fake_package = debs_path / "fake-package_1.0_all.deb"
        fake_package.touch()
        fake_package_dep = debs_path / "fake-package-dep_1.0_all.deb"
        fake_package_dep.touch()
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.return_value = [
            ("fake-package", "1.0", fake_package),
            ("fake-package-dep", "2.0", fake_package_dep),
        ]

        fetched_packages = _deb.Ubuntu.fetch_stage_packages(
            application_name="test",
            package_names=["fake-package"],
            stage_packages_path=Path(tmpdir),
            base="core",
            target_arch="amd64",
        )

        assert sorted(fetched_packages) == sorted(
            ["fake-package=1.0", "fake-package-dep=2.0"]
        )

    def test_get_package_fetch_error(self, tmpdir, fake_apt_cache):
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.side_effect = errors.PackageFetchError(
            "foo"
        )

        with pytest.raises(errors.PackageFetchError) as raised:
            _deb.Ubuntu.fetch_stage_packages(
                application_name="test",
                package_names=["fake-package"],
                stage_packages_path=Path(tmpdir),
                base="core",
                target_arch="amd64",
            )
        assert str(raised.value) == "Package fetch error: foo"


class TestBuildPackages:
    def test_install_build_package(self, fake_apt_cache, fake_run):
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package", "1.0"),
            ("package-installed", "1.0"),
            ("versioned-package", "2.0"),
            ("dependency-package", "1.0"),
        ]

        build_packages = _deb.Ubuntu.install_build_packages(
            ["package-installed", "package", "versioned-package=2.0"]
        )

        assert build_packages == [
            "dependency-package=1.0",
            "package=1.0",
            "package-installed=1.0",
            "versioned-package=2.0",
        ]
        fake_run.assert_has_calls(
            [
                call(["sudo", "--preserve-env", "apt-get", "update"]),
                call(
                    [
                        "sudo",
                        "--preserve-env",
                        "apt-get",
                        "--no-install-recommends",
                        "-y",
                        "--allow-downgrades",
                        "install",
                        "dependency-package=1.0",
                        "package=1.0",
                        "package-installed=1.0",
                        "versioned-package=2.0",
                    ],
                    env={
                        "DEBIAN_FRONTEND": "noninteractive",
                        "DEBCONF_NONINTERACTIVE_SEEN": "true",
                        "DEBIAN_PRIORITY": "critical",
                    },
                ),
                call(
                    [
                        "sudo",
                        "apt-mark",
                        "auto",
                        "dependency-package",
                        "package",
                        "package-installed",
                        "versioned-package",
                    ],
                    env={
                        "DEBIAN_FRONTEND": "noninteractive",
                        "DEBCONF_NONINTERACTIVE_SEEN": "true",
                        "DEBIAN_PRIORITY": "critical",
                    },
                ),
            ]
        )

    def test_already_installed_no_specified_version(self, fake_apt_cache, fake_run):
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package-installed", "1.0")
        ]

        build_packages = _deb.Ubuntu.install_build_packages(["package-installed"])

        assert build_packages == ["package-installed=1.0"]
        fake_run.assert_has_calls([])

    def test_already_installed_with_specified_version(self, fake_apt_cache, fake_run):
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package-installed", "1.0")
        ]

        build_packages = _deb.Ubuntu.install_build_packages(["package-installed=1.0"])

        assert build_packages == ["package-installed=1.0"]
        fake_run.assert_has_calls([])

    def test_already_installed_with_different_version(self, fake_apt_cache, fake_run):
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package-installed", "3.0")
        ]

        build_packages = _deb.Ubuntu.install_build_packages(["package-installed=3.0"])

        assert build_packages == ["package-installed=3.0"]
        fake_run.assert_has_calls(
            [
                call(["sudo", "--preserve-env", "apt-get", "update"]),
                call(
                    [
                        "sudo",
                        "--preserve-env",
                        "apt-get",
                        "--no-install-recommends",
                        "-y",
                        "--allow-downgrades",
                        "install",
                        "package-installed=3.0",
                    ],
                    env={
                        "DEBIAN_FRONTEND": "noninteractive",
                        "DEBCONF_NONINTERACTIVE_SEEN": "true",
                        "DEBIAN_PRIORITY": "critical",
                    },
                ),
                call(
                    ["sudo", "apt-mark", "auto", "package-installed"],
                    env={
                        "DEBIAN_FRONTEND": "noninteractive",
                        "DEBCONF_NONINTERACTIVE_SEEN": "true",
                        "DEBIAN_PRIORITY": "critical",
                    },
                ),
            ]
        )

    def test_install_virtual_build_package(self, fake_apt_cache, fake_run):
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package", "1.0")
        ]

        build_packages = _deb.Ubuntu.install_build_packages(["virtual-package"])

        assert build_packages == ["package=1.0"]
        fake_run.assert_has_calls(
            [
                call(["sudo", "--preserve-env", "apt-get", "update"]),
                call(
                    [
                        "sudo",
                        "--preserve-env",
                        "apt-get",
                        "--no-install-recommends",
                        "-y",
                        "--allow-downgrades",
                        "install",
                        "package=1.0",
                    ],
                    env={
                        "DEBIAN_FRONTEND": "noninteractive",
                        "DEBCONF_NONINTERACTIVE_SEEN": "true",
                        "DEBIAN_PRIORITY": "critical",
                    },
                ),
                call(
                    ["sudo", "apt-mark", "auto", "package"],
                    env={
                        "DEBIAN_FRONTEND": "noninteractive",
                        "DEBCONF_NONINTERACTIVE_SEEN": "true",
                        "DEBIAN_PRIORITY": "critical",
                    },
                ),
            ]
        )

    def test_smart_terminal(self, fake_apt_cache, fake_run, fake_dumb_terminal):
        fake_dumb_terminal.return_value = False
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package", "1.0")
        ]

        _deb.Ubuntu.install_build_packages(["package"])

        fake_run.assert_has_calls(
            [
                call(["sudo", "--preserve-env", "apt-get", "update"]),
                call(
                    [
                        "sudo",
                        "--preserve-env",
                        "apt-get",
                        "--no-install-recommends",
                        "-y",
                        "--allow-downgrades",
                        "-o",
                        "Dpkg::Progress-Fancy=1",
                        "install",
                        "package=1.0",
                    ],
                    env={
                        "DEBIAN_FRONTEND": "noninteractive",
                        "DEBCONF_NONINTERACTIVE_SEEN": "true",
                        "DEBIAN_PRIORITY": "critical",
                    },
                ),
                call(
                    ["sudo", "apt-mark", "auto", "package"],
                    env={
                        "DEBIAN_FRONTEND": "noninteractive",
                        "DEBCONF_NONINTERACTIVE_SEEN": "true",
                        "DEBIAN_PRIORITY": "critical",
                    },
                ),
            ]
        )

    def test_invalid_package_requested(self, fake_apt_cache, fake_run):
        fake_apt_cache.return_value.__enter__.return_value.mark_packages.side_effect = (
            errors.PackageNotFound("package-invalid")
        )

        with pytest.raises(errors.BuildPackageNotFound):
            _deb.Ubuntu.install_build_packages(["package-invalid"])

    def test_broken_package_apt_install(self, fake_apt_cache, fake_run, mocker):
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package", "1.0")
        ]
        mocker.patch("craft_parts.packages._deb.Ubuntu.refresh_build_packages")
        fake_run.side_effect = CalledProcessError(100, "apt-get")

        with pytest.raises(errors.BuildPackagesNotInstalled) as raised:
            _deb.Ubuntu.install_build_packages(["package=1.0"])
        assert (
            str(raised.value)
            == "Could not install all requested build packages: package=1.0"
        )

    def test_refresh_build_packages(self, fake_run):
        _deb.Ubuntu.refresh_build_packages()

        fake_run.assert_called_once_with(
            ["sudo", "--preserve-env", "apt-get", "update"]
        )

    def test_refresh_build_packages_fails(self, fake_run):
        fake_run.side_effect = CalledProcessError(
            returncode=1, cmd=["sudo", "--preserve-env", "apt-get", "update"]
        )

        with pytest.raises(errors.CacheUpdateFailed):
            _deb.Ubuntu.refresh_build_packages()

        fake_run.assert_has_calls(
            [call(["sudo", "--preserve-env", "apt-get", "update"])]
        )


@pytest.fixture
def fake_dpkg_query(mocker):
    def dpkg_query(*args, **kwargs):
        # dpkg-query -S file_path
        if args[0][2] == "/bin/bash":
            return "bash: /bin/bash\n".encode()

        if args[0][2] == "/bin/sh":
            return (
                "diversion by dash from: /bin/sh\n"
                "diversion by dash to: /bin/sh.distrib\n"
                "dash: /bin/sh\n"
            ).encode()

        raise CalledProcessError(
            1,
            "dpkg-query: no path found matching pattern {}".format(args[0][2]),
        )

    mocker.patch("subprocess.check_output", side_effect=dpkg_query)


@pytest.mark.usefixtures("fake_dpkg_query")
class PackageForFileTest:
    def test_get_package_for_file(self):
        assert _deb.Ubuntu.get_package_for_file("/bin/bash") == "bash"

    def test_get_package_for_file_with_no_leading_slash(self):
        assert _deb.Ubuntu.get_package_for_file("bin/bash") == "bash"

    def test_get_package_for_file_with_diversions(self):
        assert _deb.Ubuntu.get_package_for_file("/bin/sh") == "dash"

    def test_get_package_for_file_not_found(self):
        with pytest.raises(errors.FileProviderNotFound):
            _deb.Ubuntu.get_package_for_file("/bin/not-found")


class TestGetPackagesInBase:
    def test_hardcoded_bases(self):
        for base in ("core", "core16", "core18"):
            assert (
                _deb.get_packages_in_base(base=base)
                == _deb._DEFAULT_FILTERED_STAGE_PACKAGES
            )

    def test_package_list_from_dpkg_list(self, tmpdir, mocker):
        dpkg_list_path = Path(tmpdir, "dpkg.list")
        mocker.patch(
            "craft_parts.packages._deb._get_dpkg_list_path", return_value=dpkg_list_path
        )
        with dpkg_list_path.open("w") as dpkg_list_file:
            print(
                textwrap.dedent(
                    """\
            Desired=Unknown/Install/Remove/Purge/Hold
            | Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
            |/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
            ||/ Name                          Version                    Architecture Description
            +++-=============================-==========================-============-===========
            ii  adduser                       3.118ubuntu1               all          add and rem
            ii  apparmor                      2.13.3-7ubuntu2            amd64        user-space
            ii  apt                           2.0.1                      amd64        commandline
            ii  base-files                    11ubuntu4                  amd64        Debian base
            ii  base-passwd                   3.5.47                     amd64        Debian base
            ii  zlib1g:amd64                  1:1.2.11.dfsg-2ubuntu1     amd64        compression
            """
                ),
                file=dpkg_list_file,
            )

        assert _deb.get_packages_in_base(base="core20") == [
            "adduser",
            "apparmor",
            "apt",
            "base-files",
            "base-passwd",
            "zlib1g:amd64",
        ]

    def test_package_empty_list_from_missing_dpkg_list(self, tmpdir, mocker):
        dpkg_list_path = Path(tmpdir, "dpkg.list")
        mocker.patch(
            "craft_parts.packages._deb._get_dpkg_list_path", return_value=dpkg_list_path
        )

        assert _deb.get_packages_in_base(base="core22") == list()
