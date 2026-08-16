"""Phase 5 Integration Tests — Live Browser Replay without LLM Decisions."""

import os
import pytest
from capability.repository import ArtifactRepository
from replay.engine import ReplayEngine
from replay.models import ReplayStatus
from tests.conftest import BASE_URL


async def _run_test_replay(engine: ReplayEngine, repo: ArtifactRepository, name: str, version: str, inputs: dict):
    art = repo.load(name, version)
    art.entrypoint.url = BASE_URL
    if BASE_URL not in art.safety.allowed_origins:
        art.safety.allowed_origins.append(BASE_URL)
    return await engine.execute(art, inputs=inputs)


@pytest.mark.asyncio
async def test_live_replay_savings_account(tmp_path):
    repo = ArtifactRepository()
    engine = ReplayEngine(repository=repo, evidence_dir=tmp_path / "evidence")

    result = await _run_test_replay(engine, repo, "lookup_balance", "1.0.0", {"member_id": "13278", "account_type": "savings"})

    assert result.status == ReplayStatus.SUCCESS
    assert result.outputs is not None
    assert result.outputs["member_id"] == "13278"
    assert result.outputs["account_type"] == "savings"
    assert result.outputs["current_balance"]["amount"] == "5521.10"
    assert result.outputs["current_balance"]["currency"] == "USD"
    assert result.steps_completed == 4


@pytest.mark.asyncio
async def test_live_replay_checking_account_different_member(tmp_path):
    """Proves replay parameterization: member_id=12345 and account_type=checking (maps to DDA)."""
    repo = ArtifactRepository()
    engine = ReplayEngine(repository=repo, evidence_dir=tmp_path / "evidence")

    result = await _run_test_replay(engine, repo, "lookup_balance", "1.0.0", {"member_id": "12345", "account_type": "checking"})

    assert result.status == ReplayStatus.SUCCESS
    assert result.outputs is not None
    assert result.outputs["member_id"] == "12345"
    assert result.outputs["account_type"] == "checking"
    assert result.outputs["current_balance"]["amount"] == "460.87"
    assert result.outputs["current_balance"]["currency"] == "USD"
    assert result.steps_completed == 4


@pytest.mark.asyncio
async def test_live_replay_member_not_found_business_outcome(tmp_path):
    """Proves business outcome handling during replay for nonexistent member 99999."""
    repo = ArtifactRepository()
    engine = ReplayEngine(repository=repo, evidence_dir=tmp_path / "evidence")

    result = await _run_test_replay(engine, repo, "lookup_balance", "1.0.0", {"member_id": "99999", "account_type": "savings"})

    assert result.status == ReplayStatus.BUSINESS_OUTCOME
    assert result.outcome is not None
    assert result.outcome.code == "MEMBER_NOT_FOUND"


@pytest.mark.asyncio
async def test_live_replay_no_llm_verification(tmp_path, monkeypatch):
    """Proves replay executes with 100% zero Groq LLM API dependency by removing GROQ_API_KEY."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    repo = ArtifactRepository()
    engine = ReplayEngine(repository=repo, evidence_dir=tmp_path / "evidence")

    result = await _run_test_replay(engine, repo, "lookup_balance", "1.0.0", {"member_id": "76821", "account_type": "checking"})

    # Replay must succeed without any LLM API key or calls
    assert result.status in [ReplayStatus.SUCCESS, ReplayStatus.BUSINESS_OUTCOME]
