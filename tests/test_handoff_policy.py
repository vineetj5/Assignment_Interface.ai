"""Tests for Phase 7 handoff policy."""

import pytest
from handoff.exceptions import ControlOwnershipError
from handoff.models import ControlOwner, RunHandle, RunState
from handoff.policy import HandoffPolicy


def test_policy_requires_same_browser_session():
    policy = HandoffPolicy()
    policy.require_same_browser_session("browser_1", "browser_1")
    with pytest.raises(ControlOwnershipError):
        policy.require_same_browser_session("browser_1", "browser_2")


def test_policy_requires_human_owner():
    handle = RunHandle(
        run_id="run_1",
        capability="lookup_balance",
        state=RunState.HUMAN_CONTROL,
        owner=ControlOwner.HUMAN,
        browser_session_id="browser_1",
    )
    HandoffPolicy().require_human_owner(handle, "op1", "op1")

