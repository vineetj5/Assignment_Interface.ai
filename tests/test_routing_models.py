"""Tests for Phase 6 routing models."""

from routing.models import ChatRequest, RoutingDecision, RoutingStatus


def test_routing_decision_model():
    decision = RoutingDecision(
        status=RoutingStatus.INVOKE,
        capability="lookup_balance",
        arguments={"member_id": "12345", "account_type": "checking"},
    )

    assert decision.status == RoutingStatus.INVOKE
    assert decision.capability == "lookup_balance"
    assert decision.arguments["account_type"] == "checking"


def test_chat_request_model():
    req = ChatRequest(session_id="abc", message="What is member 12345's balance?")
    assert req.session_id == "abc"
    assert "12345" in req.message

