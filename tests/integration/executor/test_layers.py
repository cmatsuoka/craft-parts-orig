# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2021 Canonical Ltd
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

import textwrap
from unittest.mock import call

import pytest
import yaml

import craft_parts
from craft_parts import Action, Step


@pytest.fixture
def fake_apt_cache(mocker):
    def get_installed_version(package_name, resolve_virtual_packages=False):
        return "1.0"

    fake = mocker.patch("craft_parts.packages._deb.AptCache")
    fake.return_value.__enter__.return_value.get_installed_version.side_effect = (
        get_installed_version
    )
    return fake


@pytest.fixture
def fake_chroot(mocker):
    fake = mocker.patch("pychroot.Chroot")
    fake.return_value.__enter__.return_value = None
    fake.return_value.__exit__.return_value = None
    return fake


@pytest.fixture
def fake_run(mocker):
    return mocker.patch("subprocess.check_call")


class TestStagePackages:
    def test_stage_package_overlay(
        self, new_dir, fake_chroot, fake_apt_cache, fake_run
    ):
        parts_yaml = textwrap.dedent(
            """\
            parts:
              foo:
                plugin: nil
                stage-packages: [fake-package]
            """
        )

        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.return_value = [
            ("fake-package", "1.0", "")
        ]

        parts = yaml.safe_load(parts_yaml)

        lf = craft_parts.LifecycleManager(
            parts, application_name="test_layers", enable_stage_layers=True
        )

        with lf.execution_context() as ctx:
            ctx.execute(Action("foo", Step.PULL))
            ctx.execute(Action("foo", Step.BUILD))

        fake_chroot.assert_has_calls([call(new_dir / "layer/stage_packages_overlay")])

        upper_dir = f"{new_dir}/layer/stage_packages"
        lower_dir = "layer/base"
        work_dir = f"{new_dir}/layer/stage_packages_work"

        fake_run.assert_has_calls(
            [
                call(
                    [
                        "/bin/mount",
                        "-toverlay",
                        f"-olowerdir={lower_dir},upperdir={upper_dir},workdir={work_dir}",
                        "overlay",
                        f"{new_dir}/layer/stage_packages_overlay",
                    ]
                ),
                # call(["sudo", "--preserve-env", "apt-get", "update"]),
                call(["apt-get", "update"]),
                call(["/bin/umount", f"{new_dir}/layer/stage_packages_overlay"]),
            ]
        )
