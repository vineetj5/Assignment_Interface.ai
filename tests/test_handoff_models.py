"""Tests for Phase 7 handoff models."""

from handoff.models import ControlOwner, InterventionRequest, InterventionSource, InterventionStatus, RunHandle, RunState


def test_intervention_model_defaults():
    intervention = InterventionRequest(
        intervention_id="int_1",
        run_id="run_1",
        source=InterventionSource.REPLAY,
        reason_code="VERIFICATION_REQUIRED",
        reason="Verification required.",
        browser_session_id="browser_session_1",
    )

    assert intervention.status == InterventionStatus.OPEN
    assert intervention.browser_session_id == "browser_session_1"


def test_run_handle_model():
    handle = RunHandle(
        run_id="run_1",
        capability="lookup_balance",
        owner=ControlOwner.AUTOMATION,
        state=RunState.RUNNING,
        browser_session_id="browser_session_1",
    )

    assert handle.state == RunState.RUNNING
    assert handle.owner == ControlOwner.AUTOMATION

