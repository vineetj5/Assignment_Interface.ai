"""Tests for Phase 4 Artifact Compiler (Trace-to-Artifact Pipeline)."""

import pytest
from capability.compiler import ArtifactCompiler
from capability.exceptions import ArtifactCompilationError
from capability.registry import CapabilityRegistry
from capability.repository import ArtifactRepository


def build_mock_discovery_run() -> dict:
    """Simulate a successful Phase 3 discovery run record."""
    return {
        "status": "success",
        "run_id": "discovery_1786831472",
        "goal": {
            "goal": "Look up member 13278 and read their current savings balance.",
            "target_url": "http://127.0.0.1:8000",
            "max_steps": 15,
            "timeout_seconds": 120,
        },
        "steps_count": 5,
        "duration_seconds": 4.86,
        "outputs": {
            "current_balance": "$5,521.10",
            "member_id": "13278",
            "account_type": "Regular Savings",
        },
        "steps": [
            {
                "step": 1,
                "model_decision": {
                    "action": "fill",
                    "target_id": "e_06",
                    "value": "13278",
                    "reasoning_summary": "Entering member number 13278.",
                    "expected_result": "Member number filled.",
                },
                "resolved_target": {
                    "observation_id": "e_06",
                    "role": "textbox",
                    "name": "Member Number",
                    "tag": "input",
                    "attributes": {"name": "member_number"},
                    "frame_path": ["legacy-app", "workspace"],
                },
                "action_result": {"status": "success", "output": {"filled": "13278"}},
            },
            {
                "step": 2,
                "model_decision": {
                    "action": "click",
                    "target_id": "e_07",
                    "reasoning_summary": "Click Find Member.",
                    "expected_result": "Profile loaded.",
                },
                "resolved_target": {
                    "observation_id": "e_07",
                    "role": "button",
                    "name": "Find Member",
                    "tag": "input",
                    "attributes": {"type": "submit", "value": "Find Member"},
                    "frame_path": ["legacy-app", "workspace"],
                },
                "action_result": {"status": "success", "output": {"clicked": True}},
            },
            {
                "step": 3,
                "model_decision": {
                    "action": "click",
                    "target_id": "e_09",
                    "reasoning_summary": "Click View on Regular Savings.",
                    "expected_result": "Account Detail loaded.",
                },
                "resolved_target": {
                    "observation_id": "e_09",
                    "role": "link",
                    "name": "View",
                    "tag": "a",
                    "frame_path": ["legacy-app", "workspace"],
                },
                "action_result": {"status": "success", "output": {"clicked": True}},
            },
            {
                "step": 4,
                "model_decision": {
                    "action": "extract",
                    "target_id": "e_06",
                    "reasoning_summary": "Extract Current Balance.",
                    "expected_result": "Balance read.",
                },
                "resolved_target": {
                    "observation_id": "e_06",
                    "role": "",
                    "name": "Current Balance",
                    "tag": "span",
                    "attributes": {"class": "balance-value"},
                    "frame_path": ["legacy-app", "workspace"],
                },
                "action_result": {"status": "success", "output": {"text": "$5,521.10"}},
            },
            {
                "step": 5,
                "model_decision": {
                    "action": "finish",
                    "extracted_output": {"current_balance": "$5,521.10", "member_id": "13278"},
                    "reasoning_summary": "Complete discovery.",
                },
                "action_result": {"status": "success", "terminal": "finish"},
            },
        ],
    }


def test_compile_successful_discovery_trace(tmp_path):
    repo = ArtifactRepository(root_dir=tmp_path / "artifacts")
    registry = CapabilityRegistry(registry_file=tmp_path / "artifacts" / "registry.json")
    compiler = ArtifactCompiler(repository=repo, registry=registry)

    discovery_run = build_mock_discovery_run()
    artifact = compiler.compile(discovery_run=discovery_run, capability_name="lookup_balance", version="1.0.0")

    assert artifact.identity.name == "lookup_balance"
    assert artifact.identity.version == "1.0.0"
    assert len(artifact.steps) == 4  # physical browser steps: fill, click, click, extract

    # 1. Step 1: Member Number fill
    step1 = artifact.steps[0]
    assert step1.id == "enter_member_id"
    assert step1.action.value == "fill"
    assert step1.value.source == "input"
    assert step1.value.name == "member_id"
    assert step1.target.primary.strategy == "role_name"
    assert step1.target.primary.name == "Member Number"

    # 2. Step 2: Search button click
    step2 = artifact.steps[1]
    assert step2.id == "search_member"
    assert step2.action.value == "click"
    assert step2.wait_after is not None

    # 3. Step 3: Account row View click
    step3 = artifact.steps[2]
    assert step3.id == "open_account"
    assert step3.action.value == "click"
    assert step3.target.primary.strategy == "table_row_action"
    assert step3.target.primary.row_match["column"] == "Type"

    # 4. Step 4: Extract balance
    step4 = artifact.steps[3]
    assert step4.id == "extract_current_balance"
    assert step4.action.value == "extract"
    assert step4.extraction.output == "current_balance"

    # Verify no discovery literals or temporary IDs in the JSON
    json_dump = artifact.model_dump_json()
    assert "13278" not in json_dump
    assert "$5,521.10" not in json_dump
    assert '"e_06"' not in json_dump
    assert '"e_09"' not in json_dump

    # Test compile and save
    saved_path = compiler.compile_and_save(discovery_run=discovery_run, capability_name="lookup_balance", version="1.0.0")
    assert saved_path.exists()
    assert registry.get("lookup_balance") is not None


def test_reject_failed_discovery():
    compiler = ArtifactCompiler()
    failed_run = {"status": "failed", "error_message": "Network error", "steps": []}
    with pytest.raises(ArtifactCompilationError, match="expected 'success'"):
        compiler.compile(failed_run)
