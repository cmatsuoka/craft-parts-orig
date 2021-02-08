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

import pytest

from craft_parts import callbacks, errors
from craft_parts.parts import Part
from craft_parts.step_info import StepInfo
from craft_parts.steps import Step


def _callback_1(info: StepInfo) -> bool:
    greet = getattr(info, "greet")
    print(f"{greet} callback 1")
    return True


def _callback_2(info: StepInfo) -> bool:
    greet = getattr(info, "greet")
    print(f"{greet} callback 2")
    return False


class TestCallbackRegistration:
    """Test different scenarios of callback function registration."""

    def setup_method(self):
        callbacks.clear()

    def test_register_pre(self):
        callbacks.register_pre(_callback_1)

        # A callback function shouldn't be registered again
        with pytest.raises(errors.CallbackRegistration) as raised:
            callbacks.register_pre(_callback_1)
        assert (
            str(raised.value) == "Callback registration error: the callback "
            "function is already registered."
        )

        # But we can register a different one
        callbacks.register_pre(_callback_2)

    def test_register_post(self):
        callbacks.register_post(_callback_1)

        # A callback function shouldn't be registered again
        with pytest.raises(errors.CallbackRegistration) as raised:
            callbacks.register_post(_callback_1)
        assert (
            str(raised.value) == "Callback registration error: the callback "
            "function is already registered."
        )

        # But we can register a different one
        callbacks.register_post(_callback_2)

    def test_register_both(self):
        callbacks.register_pre(_callback_1)
        callbacks.register_post(_callback_1)

    def test_clear(self):
        callbacks.register_pre(_callback_1)
        callbacks.clear()
        callbacks.register_pre(_callback_1)

    def test_register_steps(self):
        callbacks.register_pre(_callback_1, step_list=[Step.PULL, Step.BUILD])

        # A callback function shouldn't be registered again, even for a different step
        with pytest.raises(errors.CallbackRegistration) as raised:
            callbacks.register_pre(_callback_1, step_list=[Step.PRIME])
        assert (
            str(raised.value) == "Callback registration error: the callback "
            "function is already registered."
        )


class TestCallbackExecution:
    """Test different scenarios of callback function execution."""

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        self._part = Part("foo", {})
        self._info = StepInfo(
            application_name="test",
            target_arch="x86_64",
            parallel_build_count=4,
            local_plugins_dir=None,
            greet="hello",
        )
        callbacks.clear()

    def test_run_pre(self, capfd):
        callbacks.register_pre(_callback_1)
        callbacks.register_pre(_callback_2)
        callbacks.run_pre(self._part, Step.BUILD, step_info=self._info)
        out, err = capfd.readouterr()
        assert not err
        assert out == "hello callback 1\nhello callback 2\n"

    def test_run_post(self, capfd):
        callbacks.register_post(_callback_1)
        callbacks.register_post(_callback_2)
        callbacks.run_post(self._part, Step.BUILD, step_info=self._info)
        out, err = capfd.readouterr()
        assert not err
        assert out == "hello callback 1\nhello callback 2\n"
