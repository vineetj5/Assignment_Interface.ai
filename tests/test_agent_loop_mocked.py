import threading
import time
import pytest
import uvicorn
from app import app
from agent.config import AgentSettings
from agent.llm_client import MockLLMClient
from agent.loop import run_discovery
from agent.models import DiscoveryGoal
from agent.recorder import DiscoveryRecorder
from agent.results import DiscoveryRunStatus
from automation.surface import PlaywrightSurface

TEST_PORT = 8009
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"




@pytest.mark.asyncio
async def test_agent_discovery_happy_path_13278(tmp_path):
    goal = DiscoveryGoal(
        goal="Look up member 13278 and read their current savings balance.",
        target_url=BASE_URL,
    )
    surface = PlaywrightSurface(
        headless=True,
        evidence_dir=tmp_path / "evidence",
        run_id="test_discovery_13278",
    )
    recorder = DiscoveryRecorder(
        evidence_dir=tmp_path / "evidence",
        run_id="test_discovery_13278",
    )
    mock_llm = MockLLMClient(rule_based=True)

    try:
        result = await run_discovery(
            goal=goal,
            surface=surface,
            llm=mock_llm,
            recorder=recorder,
        )

        if result.status != DiscoveryRunStatus.SUCCESS:
            print("ERROR MSG:", result.error_message)
            print("STOP REASON:", result.stop_reason)
        assert result.status == DiscoveryRunStatus.SUCCESS
        assert result.outputs is not None
        assert result.outputs.get("current_balance") == "$5,521.10"
        assert result.steps_count >= 3

        # Verify recorded trace
        assert (tmp_path / "evidence" / "test_discovery_13278" / "discovery_trace.jsonl").exists()
        assert (tmp_path / "evidence" / "test_discovery_13278" / "result.json").exists()
        assert len(list((tmp_path / "evidence" / "test_discovery_13278" / "decisions").glob("*.json"))) >= 3

    finally:
        await surface.close()


@pytest.mark.asyncio
async def test_agent_discovery_happy_path_12345(tmp_path):
    goal = DiscoveryGoal(
        goal="What is member 12345's savings balance?",
        target_url=BASE_URL,
    )
    surface = PlaywrightSurface(
        headless=True,
        evidence_dir=tmp_path / "evidence",
        run_id="test_discovery_12345",
    )
    recorder = DiscoveryRecorder(
        evidence_dir=tmp_path / "evidence",
        run_id="test_discovery_12345",
    )
    mock_llm = MockLLMClient(rule_based=True)

    try:
        result = await run_discovery(
            goal=goal,
            surface=surface,
            llm=mock_llm,
            recorder=recorder,
        )

        assert result.status == DiscoveryRunStatus.SUCCESS
        assert result.outputs is not None
        assert result.outputs.get("current_balance") == "$1,214.87"

    finally:
        await surface.close()


@pytest.mark.asyncio
async def test_agent_discovery_member_not_found(tmp_path):
    goal = DiscoveryGoal(
        goal="Look up member 99999 and read their current savings balance.",
        target_url=BASE_URL,
    )
    surface = PlaywrightSurface(
        headless=True,
        evidence_dir=tmp_path / "evidence",
        run_id="test_discovery_99999",
    )
    mock_llm = MockLLMClient(rule_based=True)

    try:
        result = await run_discovery(
            goal=goal,
            surface=surface,
            llm=mock_llm,
        )

        assert result.status == DiscoveryRunStatus.SUCCESS
        assert result.outputs is not None
        assert result.outputs.get("status") == "member_not_found"

    finally:
        await surface.close()
