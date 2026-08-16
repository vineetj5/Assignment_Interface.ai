"""Tests for Phase 6 ChatService."""

import pytest
from replay.models import ReplayResult, ReplayStatus
from routing.models import ChatResponseStatus
from routing.router import CapabilityRouter
from routing.service import ChatService
from routing.session import ChatSessionStore


class FakeRoutingClient:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.calls = []

    async def route_json(self, system_prompt, user_prompt):
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return self.decisions.pop(0)


class FakeReplayEngine:
    def __init__(self):
        self.calls = []

    async def execute_capability(self, name, inputs):
        self.calls.append((name, inputs))
        return ReplayResult(
            status=ReplayStatus.SUCCESS,
            run_id="replay_fake",
            capability=name,
            version="1.0.0",
            outputs={
                "member_id": inputs["member_id"],
                "account_type": inputs["account_type"],
                "current_balance": {"amount": "460.87", "currency": "USD"},
            },
            steps_completed=4,
        )


@pytest.mark.asyncio
async def test_chat_service_invokes_replay_for_complete_request(tmp_path):
    fake = FakeReplayEngine()
    service = ChatService(replay_engine=fake, session_store=ChatSessionStore(), evidence_dir=tmp_path)

    response = await service.handle_message("s1", "What is member 12345's checking balance?")

    assert response.status == ChatResponseStatus.SUCCESS
    assert fake.calls == [("lookup_balance", {"member_id": "12345", "account_type": "checking"})]
    assert "$460.87" in response.message


@pytest.mark.asyncio
async def test_chat_service_clarifies_and_completes_multi_turn(tmp_path):
    fake = FakeReplayEngine()
    service = ChatService(replay_engine=fake, session_store=ChatSessionStore(), evidence_dir=tmp_path)

    first = await service.handle_message("s1", "What is member 12345's balance?")
    second = await service.handle_message("s1", "checking")

    assert first.status == ChatResponseStatus.NEEDS_INPUT
    assert first.missing_arguments == ["account_type"]
    assert second.status == ChatResponseStatus.SUCCESS
    assert fake.calls == [("lookup_balance", {"member_id": "12345", "account_type": "checking"})]


@pytest.mark.asyncio
async def test_chat_service_rejects_unsupported_without_replay(tmp_path):
    fake = FakeReplayEngine()
    service = ChatService(replay_engine=fake, session_store=ChatSessionStore(), evidence_dir=tmp_path)

    response = await service.handle_message("s1", "Freeze member 12345's debit card.")

    assert response.status == ChatResponseStatus.UNSUPPORTED
    assert fake.calls == []


@pytest.mark.asyncio
async def test_chat_service_uses_llm_router_once_then_replay(tmp_path):
    routing_client = FakeRoutingClient([
        {
            "status": "invoke",
            "capability": "lookup_balance",
            "arguments": {"member_id": "12345", "account_type": "checking"},
            "missing_arguments": [],
            "clarification_question": None,
            "reason_code": None,
        }
    ])
    router = CapabilityRouter(client=routing_client, use_llm=True)
    replay = FakeReplayEngine()
    service = ChatService(
        router=router,
        replay_engine=replay,
        session_store=ChatSessionStore(),
        evidence_dir=tmp_path,
    )

    response = await service.handle_message("s1", "What is member 12345's checking balance?")

    assert response.status == ChatResponseStatus.SUCCESS
    assert router.routing_llm_calls == 1
    assert len(routing_client.calls) == 1
    assert replay.calls == [("lookup_balance", {"member_id": "12345", "account_type": "checking"})]


@pytest.mark.asyncio
async def test_llm_follow_up_reuses_pending_member_id(tmp_path):
    routing_client = FakeRoutingClient([
        {
            "status": "clarify",
            "capability": "lookup_balance",
            "arguments": {"member_id": "76821"},
            "missing_arguments": ["account_type"],
            "clarification_question": "What type of account would you like to check the balance for, savings or checking?",
            "reason_code": None,
        },
        {
            "status": "invoke",
            "capability": "lookup_balance",
            "arguments": {"account_type": "savings"},
            "missing_arguments": [],
            "clarification_question": None,
            "reason_code": None,
        },
    ])
    router = CapabilityRouter(client=routing_client, use_llm=True)
    replay = FakeReplayEngine()
    service = ChatService(
        router=router,
        replay_engine=replay,
        session_store=ChatSessionStore(),
        evidence_dir=tmp_path,
    )

    first = await service.handle_message("s1", "What is member 76821's balance?")
    second = await service.handle_message("s1", "savings")

    assert first.status == ChatResponseStatus.NEEDS_INPUT
    assert second.status == ChatResponseStatus.SUCCESS
    assert replay.calls == [("lookup_balance", {"member_id": "76821", "account_type": "savings"})]
    assert "Pending capability: lookup_balance" in routing_client.calls[1]["user_prompt"]


@pytest.mark.asyncio
async def test_unsupported_short_follow_up_uses_pending_context(tmp_path):
    routing_client = FakeRoutingClient([
        {
            "status": "clarify",
            "capability": "lookup_balance",
            "arguments": {"member_id": "76821"},
            "missing_arguments": ["account_type"],
            "clarification_question": "What type of account would you like to check the balance for, savings or checking?",
            "reason_code": None,
        },
        {
            "status": "unsupported",
            "capability": None,
            "arguments": {},
            "missing_arguments": [],
            "clarification_question": None,
            "reason_code": "NO_MATCHING_CAPABILITY",
        },
    ])
    router = CapabilityRouter(client=routing_client, use_llm=True)
    replay = FakeReplayEngine()
    service = ChatService(
        router=router,
        replay_engine=replay,
        session_store=ChatSessionStore(),
        evidence_dir=tmp_path,
    )

    first = await service.handle_message("s1", "76821")
    second = await service.handle_message("s1", "checking")

    assert first.status == ChatResponseStatus.NEEDS_INPUT
    assert second.status == ChatResponseStatus.SUCCESS
    assert replay.calls == [("lookup_balance", {"member_id": "76821", "account_type": "checking"})]


@pytest.mark.asyncio
async def test_clarify_short_follow_up_with_complete_args_invokes(tmp_path):
    routing_client = FakeRoutingClient([
        {
            "status": "clarify",
            "capability": "lookup_balance",
            "arguments": {"member_id": "76821"},
            "missing_arguments": ["account_type"],
            "clarification_question": "What type of account would you like to check the balance for, savings or checking?",
            "reason_code": None,
        },
        {
            "status": "clarify",
            "capability": "lookup_balance",
            "arguments": {"account_type": "checking"},
            "missing_arguments": ["member_id"],
            "clarification_question": "Which member's checking balance would you like to look up?",
            "reason_code": None,
        },
    ])
    router = CapabilityRouter(client=routing_client, use_llm=True)
    replay = FakeReplayEngine()
    service = ChatService(
        router=router,
        replay_engine=replay,
        session_store=ChatSessionStore(),
        evidence_dir=tmp_path,
    )

    first = await service.handle_message("s1", "What is member 76821's balance?")
    second = await service.handle_message("s1", "checking")

    assert first.status == ChatResponseStatus.NEEDS_INPUT
    assert second.status == ChatResponseStatus.SUCCESS
    assert replay.calls == [("lookup_balance", {"member_id": "76821", "account_type": "checking"})]
