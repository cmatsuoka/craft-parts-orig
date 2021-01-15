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

"""The part crafter lifecycle manager."""

import logging
from typing import Dict, List, Optional

from craft_parts import errors, parts, steps
from craft_parts.parts import Part
from craft_parts.steps import Step

from .dependencies import Dependency
from .dirty_report import DirtyReport
from .outdated_report import OutdatedReport
from .states import PartState, load_state

logger = logging.getLogger(__name__)


# report types
_DirtyReports = Dict[str, Dict[Step, Optional[DirtyReport]]]
_OutdatedReports = Dict[str, Dict[Step, Optional[OutdatedReport]]]


class _EphemeralState:
    def __init__(self):
        self._state = {}  # type: Dict[str, Dict[Step, PartState]]

    def set(self, *, part_name: str, step: Step, state: Optional[PartState]) -> None:
        """Set a state for a given part and step."""

        if not state:
            self.remove(part_name=part_name, step=step)
            return

        if part_name not in self._state:
            self._state[part_name] = dict()

        self._state[part_name][step] = state

    def remove(self, *, part_name: str, step: Step) -> None:
        """Remove the state for a given part and step."""

        self._state[part_name].pop(step, None)

    def test(self, *, part_name: str, step: Step) -> bool:
        """Verify if there is a state for a given part and step."""

        if part_name not in self._state:
            return False
        return step in self._state[part_name]

    def get(self, *, part_name: str, step: Step) -> Optional[PartState]:
        """Retrieve the state for a give part and step."""

        if self.test(part_name=part_name, step=step):
            return self._state[part_name][step]
        return None


class StateManager:
    """Keep track of parts execution state."""

    def __init__(self, all_parts: List[Part]):
        self._state = _EphemeralState()
        self._all_parts = all_parts

        for part in all_parts:
            # Initialize from persistent state
            for step in list(Step):
                state = load_state(part, step)
                if state:
                    self._state.set(part_name=part.name, step=step, state=state)

    def set_state(self, part: Part, step: Step, *, state: PartState) -> None:
        self._state.set(part_name=part.name, step=step, state=state)

    def should_step_run(self, part: Part, step: Step) -> bool:
        """Determine if a given step of a given part should run.

        :param Part part: Part in question.
        :param Step step: Step in question.
        :return: Whether or not step should run.
        :rtype: bool

        A given step should run if it:
            1. Hasn't yet run
            2. Is dirty
            3. Is outdated
            4. Either (1), (2), or (3) apply to any earlier steps in the part's
               lifecycle
        """
        if (
            not self.has_step_run(part, step)
            or self.outdated_report(part, step) is not None
            or self.dirty_report(part, step) is not None
        ):
            return True

        previous_steps = step.previous_steps()
        if previous_steps:
            return self.should_step_run(part, previous_steps[-1])

        return False

    def has_step_run(self, part: Part, step: Step) -> bool:
        """Determine if a given step of a given part has already run.

        :param Part part: Part in question.
        :param Step step: Step in question.
        :return: Whether or not the step has run.
        """
        return self._state.test(part_name=part.name, step=step)

    def clean_part(self, part: Part, step: Step) -> None:
        """Remove the state for this and all later steps."""

        for s in [step] + step.next_steps():
            self._state.remove(part_name=part.name, step=step)

    def dirty_report(self, part: Part, step: Step) -> Optional[DirtyReport]:
        """Obtain the dirty report for a given step of the given part.

        :param Part part: Part in question.
        :param Step step: Step in question.
        :return: Dirty report (could be None)
        """

        # With V2 plugins we don't need to repull if dependency is restaged
        if step is Step.PULL:
            return None

        # Get the dirty report from the PluginHandler. If it's dirty, we can
        # stop here
        report = self._dirty_report_for_part(part_name=part.name, step=step)
        if report:
            return report

        # The dirty report from the PluginHandler only takes into account
        # properties specific to that part. If it's not dirty because of those,
        # we need to expand it here to also take its dependencies (if any) into
        # account
        prerequisite_step = steps.dependency_prerequisite_step(step)
        dependencies = parts.part_dependencies(
            part.name, part_list=self._all_parts, recursive=True
        )

        changed_dependencies: List[Dependency] = []

        this_state = self._state.get(part_name=part.name, step=step)
        logger.debug("state for %s:%s: %s", part.name, step, this_state)

        # consistency check
        if not this_state:
            raise errors.InternalError(
                f"{part.name}:{step} should already have been run"
            )
        if not this_state.timestamp:
            raise errors.InternalError(
                f"state for {part.name}:{step} doesn't have a timestamp"
            )

        for dependency in dependencies:
            # Make sure the prerequisite step of this dependency has not
            # run more recently than (or should run _before_) this step.

            prerequisite_state = self._state.get(
                part_name=dependency.name, step=prerequisite_step
            )
            if prerequisite_state:  # and this_state and this_state.timestamp:
                prerequisite_timestamp = prerequisite_state.timestamp
                dependency_changed = this_state.timestamp < prerequisite_timestamp
            else:
                dependency_changed = True

            if dependency_changed or self.should_step_run(
                dependency, prerequisite_step
            ):
                changed_dependencies.append(
                    Dependency(part_name=dependency.name, step=prerequisite_step)
                )

        if changed_dependencies:
            return DirtyReport(changed_dependencies=changed_dependencies)

        return None

    def outdated_report(self, part: Part, step: Step) -> Optional[OutdatedReport]:
        """Obtain the outdated report for a given step of the given part.

        :param Part part: Part in question.
        :param Step step: Step in question.
        :return: Outdated report (could be None)
        """

        return self._outdated_report_for_part(part_name=part.name, step=step)

    def _dirty_report_for_part(
        self, *, part_name: str, step: Step
    ) -> Optional[DirtyReport]:
        """Return a DirtyReport class describing why the step is dirty.

        A step is considered to be dirty if either YAML properties used by it
        (`stage-packages` are used by the `pull` step, for example), or project
        options used by it (`--target-arch` is used by the `pull` step as well)
        have changed since the step was run. This means the step needs to be
        cleaned and run again. This is in contrast to an "outdated" step, which
        typically doesn't need to be cleaned, just updated with files from an
        earlier step in the lifecycle.

        :param steps.Step step: The step to be checked.
        :returns: DirtyReport if the step is dirty, None otherwise.
        """

        # Retrieve the stored state for this step (assuming it has already run)
        state = self._state.get(part_name=part_name, step=step)
        if state:
            # state properties contains the old state that this step cares
            # about, and we're comparing it to those same keys in the current
            # state (current_properties). If they've changed, then this step
            # is dirty and needs to run again.
            # properties = diff_properties_of_interest(current_properties)
            properties: List[str] = []

            # state project_options contains the old project options that this
            # step cares about, and we're comparing it to those same options in
            # the current state. If they've changed, then this step is dirty
            # and needs to run again.
            # options = diff_project_options_of_interest(current_project_options)
            options: List[str] = []

            if properties or options:
                return DirtyReport(
                    dirty_properties=properties, dirty_project_options=options
                )

        return None

    def _outdated_report_for_part(
        self, *, part_name: str, step: Step
    ) -> Optional[OutdatedReport]:
        """Return an OutdatedReport class describing why the step is outdated.

        A step is considered to be outdated if an earlier step in the lifecycle
        has been run more recently, or if the source code changed on disk.
        This means the step needs to be updated by taking modified files from
        the previous step. This is in contrast to a "dirty" step, which must
        be cleaned and run again.

        :param steps.Step step: The step to be checked.
        :returns: OutdatedReport if the step is outdated, None otherwise.
        """

        # TODO: implement outdated check

        return None
