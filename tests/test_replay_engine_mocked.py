"""Unit tests for Phase 5 Replay Engine (Mocked Repository & Input Validation)."""

import pytest
from capability.bindings import (
    LOOKUP_BALANCE_ENTRYPOINT,
    LOOKUP_BALANCE_IDENTITY,
    LOOKUP_BALANCE_INPUTS,
    LOOKUP_BALANCE_OUTPUTS,
    get_lookup_balance_safety,
)
from capability.models import (
    ArtifactActionType,
    ArtifactStatus,
    CapabilityArtifact,
    CapabilityIdentity,
    CapabilityStep,
    CompatibilitySpec,
    ConditionSpec,
    EntryPointSpec,
    ExtractionSpec,
    ExtractionTransformSpec,
    LocatorStrategy,
    ProvenanceSpec,
    TargetSpec,
    ValueSource,
)
from capability.repository import ArtifactRepository
from replay.engine import ReplayEngine
from replay.models import FailureCategory, ReplayStatus


from tests.conftest import BASE_URL


def build_mock_replay_artifact() -> CapabilityArtifact:
    safety = get_lookup_balance_safety()
    if BASE_URL not in safety.allowed_origins:
        safety.allowed_origins.append(BASE_URL)

    return CapabilityArtifact(
        schema_version="1",
        identity=CapabilityIdentity(
            name="lookup_balance",
            version="1.0.0",
            description="Mock balance capability.",
            status=ArtifactStatus.APPROVED,
        ),
        inputs=LOOKUP_BALANCE_INPUTS,
        outputs=LOOKUP_BALANCE_OUTPUTS,
        entrypoint=EntryPointSpec(url=BASE_URL),
        steps=[
            CapabilityStep(
                id="enter_member_id",
                action=ArtifactActionType.FILL,
                target=TargetSpec(primary=LocatorStrategy(strategy="role_name", role="textbox", name="Member Number")),
                value=ValueSource(source="input", name="member_id"),
            ),
            CapabilityStep(
                id="extract_current_balance",
                action=ArtifactActionType.EXTRACT,
                target=TargetSpec(primary=LocatorStrategy(strategy="field_by_label", label="Current Balance")),
                extraction=ExtractionSpec(output="current_balance", transform=ExtractionTransformSpec(type="parse_currency")),
            ),
        ],
        success_condition=ConditionSpec(type="all_of", conditions=[ConditionSpec(type="output_present", output="current_balance")]),
        safety=safety,
        compatibility=CompatibilitySpec(),
        provenance=ProvenanceSpec(created_from="llm_discovery", discovery_run_id="run_mock_001", created_at="2026-08-15T19:00:00Z"),
    )


@pytest.mark.asyncio
async def test_replay_engine_input_validation_failure(tmp_path):
    repo = ArtifactRepository(root_dir=tmp_path / "artifacts")
    art = build_mock_replay_artifact()
    repo.save(art)

    engine = ReplayEngine(repository=repo, evidence_dir=tmp_path / "evidence")

    # Pass missing member_id
    res = await engine.execute(art, inputs={"account_type": "savings"})
    assert res.status == ReplayStatus.FAILED
    assert res.failure.category == FailureCategory.INPUT_VALIDATION
    assert "member_id" in res.failure.message


@pytest.mark.asyncio
async def test_replay_engine_policy_violation(tmp_path):
    repo = ArtifactRepository(root_dir=tmp_path / "artifacts")
    art = build_mock_replay_artifact()
    art.safety.allowed_actions = ["click"]  # exclude 'fill'
    repo.save(art)

    engine = ReplayEngine(repository=repo, evidence_dir=tmp_path / "evidence")

    res = await engine.execute(art, inputs={"member_id": "76821", "account_type": "checking"})
    assert res.status == ReplayStatus.FAILED
    assert res.failure.category == FailureCategory.POLICY_VIOLATION
