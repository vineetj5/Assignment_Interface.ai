"""Tests for Phase 5 Replay data models."""

from replay.models import (
    BusinessOutcomeResult,
    FailureCategory,
    ReplayFailure,
    ReplayRequest,
    ReplayResult,
    ReplayStatus,
)


def test_replay_request_model():
    req = ReplayRequest(
        capability="lookup_balance",
        version="1.0.0",
        inputs={"member_id": "76821", "account_type": "checking"},
        headful=False,
    )
    assert req.capability == "lookup_balance"
    assert req.inputs["member_id"] == "76821"


def test_replay_result_serialization():
    res = ReplayResult(
        status=ReplayStatus.SUCCESS,
        run_id="replay_123",
        capability="lookup_balance",
        version="1.0.0",
        outputs={"current_balance": {"amount": "8241.32", "currency": "USD"}},
        steps_completed=4,
    )
    json_str = res.model_dump_json()
    assert '"status":"success"' in json_str or '"status": "success"' in json_str
    assert "8241.32" in json_str
