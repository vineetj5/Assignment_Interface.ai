"""Tests for Phase 6 deterministic response formatting."""

from replay.models import (
    BusinessOutcomeResult,
    EscalationResult,
    FailureCategory,
    ReplayFailure,
    ReplayResult,
    ReplayStatus,
)
from routing.models import ChatResponseStatus
from routing.response_formatter import ResponseFormatter


def test_formatter_success_balance_message():
    result = ReplayResult(
        status=ReplayStatus.SUCCESS,
        run_id="replay_1",
        capability="lookup_balance",
        version="1.0.0",
        outputs={
            "member_id": "12345",
            "account_type": "checking",
            "current_balance": {"amount": "460.87", "currency": "USD"},
        },
        steps_completed=4,
    )

    response = ResponseFormatter().format_replay(result)

    assert response.status == ChatResponseStatus.SUCCESS
    assert response.message == "Member 12345's current checking balance is $460.87."


def test_formatter_business_outcomes():
    result = ReplayResult(
        status=ReplayStatus.BUSINESS_OUTCOME,
        run_id="replay_2",
        capability="lookup_balance",
        version="1.0.0",
        outcome=BusinessOutcomeResult(code="MEMBER_NOT_FOUND"),
    )

    response = ResponseFormatter().format_replay(result)
    assert response.message == "I couldn't find a member with that ID."


def test_formatter_permission_denied_failure():
    result = ReplayResult(
        status=ReplayStatus.FAILED,
        run_id="replay_3",
        capability="lookup_balance",
        version="1.0.0",
        failure=ReplayFailure(category=FailureCategory.PERMISSION_DENIED),
    )

    response = ResponseFormatter().format_replay(result)
    assert response.message == "The lookup couldn't be completed because access was denied."


def test_formatter_escalation():
    result = ReplayResult(
        status=ReplayStatus.ESCALATED,
        run_id="replay_4",
        capability="lookup_balance",
        version="1.0.0",
        intervention_id="int_4",
        escalation=EscalationResult(code="VERIFICATION_REQUIRED", reason="verify"),
    )

    response = ResponseFormatter().format_replay(result)
    assert response.message == "This lookup requires manual verification before it can continue."
    assert response.run_id == "replay_4"
    assert response.intervention_id == "int_4"
