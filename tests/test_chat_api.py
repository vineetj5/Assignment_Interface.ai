"""Tests for Phase 6 chat API endpoint."""

from fastapi.testclient import TestClient
from app import app
from replay.models import ReplayResult, ReplayStatus
from routing.router import CapabilityRouter
from routing.service import ChatService
from routing.session import ChatSessionStore
import api.chat as chat_api


client = TestClient(app)


class FakeReplayEngine:
    async def execute_capability(self, name, inputs):
        return ReplayResult(
            status=ReplayStatus.SUCCESS,
            run_id="replay_api_fake",
            capability=name,
            version="1.0.0",
            outputs={
                "member_id": inputs["member_id"],
                "account_type": inputs["account_type"],
                "current_balance": {"amount": "460.87", "currency": "USD"},
            },
            steps_completed=4,
        )


def install_deterministic_chat_service(tmp_path):
    chat_api.chat_service = ChatService(
        router=CapabilityRouter(use_llm=False),
        replay_engine=FakeReplayEngine(),
        session_store=ChatSessionStore(),
        evidence_dir=tmp_path,
    )


def test_chat_api_is_configured_for_llm_routing():
    assert chat_api.chat_service.router.use_llm is True


def test_chat_api_clarification_response(tmp_path):
    install_deterministic_chat_service(tmp_path)
    response = client.post(
        "/api/chat/message",
        json={"session_id": "api_test_clarify", "message": "What is member 12345's balance?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_input"
    assert data["pending_capability"] == "lookup_balance"
    assert data["missing_arguments"] == ["account_type"]


def test_chat_api_unsupported_response(tmp_path):
    install_deterministic_chat_service(tmp_path)
    response = client.post(
        "/api/chat/message",
        json={"session_id": "api_test_unsupported", "message": "Freeze member 12345's debit card."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unsupported"
    assert data["reason_code"] == "NO_MATCHING_CAPABILITY"


def test_chat_api_prepare_ready_response(tmp_path):
    install_deterministic_chat_service(tmp_path)
    response = client.post(
        "/api/chat/prepare",
        json={"session_id": "api_test_prepare", "message": "What is member 12345's checking balance?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["capability"] == "lookup_balance"
    assert data["data"] == {"member_id": "12345", "account_type": "checking"}


def test_chat_api_replay_prepared_response(tmp_path):
    install_deterministic_chat_service(tmp_path)
    response = client.post(
        "/api/chat/replay",
        json={
            "session_id": "api_test_replay",
            "capability": "lookup_balance",
            "arguments": {"member_id": "12345", "account_type": "checking"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Member 12345's current checking balance is $460.87."
