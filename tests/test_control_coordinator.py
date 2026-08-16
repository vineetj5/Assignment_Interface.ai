"""Tests for Phase 7 ControlCoordinator."""

import pytest
from handoff.control import ControlCoordinator
from handoff.exceptions import ControlOwnershipError, InvalidStateTransitionError
from handoff.models import ControlOwner, RunState


@pytest.mark.asyncio
async def test_control_lifecycle():
    control = ControlCoordinator()
    await control.initialize_run("run_1")
    await control.start_running("run_1")
    assert control.current_owner("run_1") == ControlOwner.AUTOMATION

    await control.pause_automation("run_1", "verify")
    assert control.current_state("run_1") == RunState.WAITING_FOR_HUMAN

    await control.claim_for_human("run_1", "op")
    assert control.current_owner("run_1") == ControlOwner.HUMAN

    with pytest.raises(ControlOwnershipError):
        await control.require_automation("run_1")

    await control.return_to_automation("run_1", "op")
    assert control.current_owner("run_1") == ControlOwner.AUTOMATION


@pytest.mark.asyncio
async def test_invalid_transition_fails_closed():
    control = ControlCoordinator()
    await control.initialize_run("run_1")
    with pytest.raises(InvalidStateTransitionError):
        await control.claim_for_human("run_1", "op")

