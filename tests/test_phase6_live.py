"""Phase 6 live test: natural language route -> deterministic Phase 5 replay."""

import pytest
from capability.repository import ArtifactRepository
from replay.engine import ReplayEngine
from routing.models import ChatResponseStatus
from routing.service import ChatService
from routing.session import ChatSessionStore
from tests.conftest import BASE_URL


@pytest.mark.asyncio
async def test_phase6_live_balance_lookup(tmp_path):
    repo = ArtifactRepository()
    service = ChatService(
        repository=repo,
        replay_engine=ReplayEngine(repository=repo, evidence_dir=tmp_path / "evidence"),
        session_store=ChatSessionStore(),
        evidence_dir=tmp_path / "evidence",
        replay_target_url=BASE_URL,
    )

    response = await service.handle_message("phase6_live", "What is member 12345's checking balance?")

    assert response.status == ChatResponseStatus.SUCCESS
    assert response.capability == "lookup_balance"
    assert response.replay_run_id is not None
    assert response.data["current_balance"]["amount"] == "460.87"
    assert response.message == "Member 12345's current checking balance is $460.87."

