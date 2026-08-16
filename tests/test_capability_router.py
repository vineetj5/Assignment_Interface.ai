"""Tests for Phase 6 CapabilityRouter."""

import pytest
from routing.catalog import CapabilityCatalog
from routing.models import RoutingStatus
from routing.router import CapabilityRouter
from routing.session import ChatSessionState


@pytest.mark.asyncio
async def test_router_complete_checking_request():
    router = CapabilityRouter()
    decision = await router.route(
        "What is member 12345's checking balance?",
        CapabilityCatalog().list_capabilities(),
    )

    assert decision.status == RoutingStatus.INVOKE
    assert decision.capability == "lookup_balance"
    assert decision.arguments == {"member_id": "12345", "account_type": "checking"}


@pytest.mark.asyncio
async def test_router_savings_alternative_phrasings():
    router = CapabilityRouter()
    caps = CapabilityCatalog().list_capabilities()
    messages = [
        "Check savings for member 12345",
        "How much does member 12345 have in savings?",
        "Give me the current savings balance for 12345",
    ]

    for message in messages:
        decision = await router.route(message, caps)
        assert decision.status == RoutingStatus.INVOKE
        assert decision.arguments["member_id"] == "12345"
        assert decision.arguments["account_type"] == "savings"


@pytest.mark.asyncio
async def test_router_missing_account_type_clarifies():
    decision = await CapabilityRouter().route(
        "What is member 12345's balance?",
        CapabilityCatalog().list_capabilities(),
    )

    assert decision.status == RoutingStatus.CLARIFY
    assert decision.arguments == {"member_id": "12345"}
    assert decision.missing_arguments == ["account_type"]


@pytest.mark.asyncio
async def test_router_missing_member_clarifies():
    decision = await CapabilityRouter().route(
        "Check the savings balance.",
        CapabilityCatalog().list_capabilities(),
    )

    assert decision.status == RoutingStatus.CLARIFY
    assert decision.arguments == {"account_type": "savings"}
    assert decision.missing_arguments == ["member_id"]


@pytest.mark.asyncio
async def test_router_unsupported_request():
    decision = await CapabilityRouter().route(
        "Freeze member 12345's debit card.",
        CapabilityCatalog().list_capabilities(),
    )

    assert decision.status == RoutingStatus.UNSUPPORTED
    assert decision.reason_code == "NO_MATCHING_CAPABILITY"


@pytest.mark.asyncio
async def test_router_multi_turn_completion():
    state = ChatSessionState(
        session_id="s1",
        pending_capability="lookup_balance",
        collected_arguments={"member_id": "12345"},
        missing_arguments=["account_type"],
    )

    decision = await CapabilityRouter().route(
        "Checking.",
        CapabilityCatalog().list_capabilities(),
        session_state=state,
    )

    assert decision.status == RoutingStatus.INVOKE
    assert decision.arguments == {"member_id": "12345", "account_type": "checking"}


@pytest.mark.asyncio
async def test_router_new_query_interrupts_pending_state():
    state = ChatSessionState(
        session_id="s1",
        pending_capability="lookup_balance",
        collected_arguments={"member_id": "12345"},
        missing_arguments=["account_type"],
    )

    decision = await CapabilityRouter().route(
        "Actually, check member 54321's savings balance.",
        CapabilityCatalog().list_capabilities(),
        session_state=state,
    )

    assert decision.status == RoutingStatus.INVOKE
    assert decision.arguments == {"member_id": "54321", "account_type": "savings"}

