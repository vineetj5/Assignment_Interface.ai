"""Tests for Phase 7 ReplayRunManager intervention lifecycle."""

import pytest
from handoff.manager import ReplayRunManager
from handoff.models import InterventionStatus, RunState
from handoff.store import HandoffStore
from replay.models import EscalationResult, ReplayResult, ReplayStatus


class FakeRepository:
    def get_approved(self, capability):
        from capability.bindings import LOOKUP_BALANCE_ENTRYPOINT, LOOKUP_BALANCE_INPUTS, LOOKUP_BALANCE_OUTPUTS, get_lookup_balance_safety
        from capability.models import ArtifactStatus, CapabilityArtifact, CapabilityIdentity, CompatibilitySpec, ConditionSpec, ProvenanceSpec

        return CapabilityArtifact(
            schema_version="1",
            identity=CapabilityIdentity(
                name=capability,
                version="1.0.0",
                description="Lookup balance.",
                status=ArtifactStatus.APPROVED,
            ),
            inputs=LOOKUP_BALANCE_INPUTS,
            outputs=LOOKUP_BALANCE_OUTPUTS,
            entrypoint=LOOKUP_BALANCE_ENTRYPOINT,
            steps=[],
            success_condition=ConditionSpec(type="all_of", conditions=[]),
            safety=get_lookup_balance_safety(),
            compatibility=CompatibilitySpec(),
            provenance=ProvenanceSpec(created_from="test", discovery_run_id="d1", created_at="2026-08-16T00:00:00Z"),
        )


class FakeEscalatingEngine:
    async def execute(self, artifact, inputs, run_id=None, headful=False, surface=None, keep_session_on_escalation=False, control=None):
        return ReplayResult(
            status=ReplayStatus.ESCALATED,
            run_id=run_id,
            capability=artifact.identity.name,
            version=artifact.identity.version,
            escalation=EscalationResult(code="VERIFICATION_REQUIRED", reason="Verification dialog visible."),
            steps_completed=2,
            evidence_dir="/tmp/evidence",
        )


@pytest.mark.asyncio
async def test_manager_creates_intervention_on_escalation(tmp_path):
    manager = ReplayRunManager(
        repository=FakeRepository(),
        replay_engine=FakeEscalatingEngine(),
        handoff_store=HandoffStore(),
        evidence_dir=tmp_path,
    )

    handle = await manager.start("lookup_balance", {"member_id": "76821", "account_type": "checking"})

    assert handle.state == RunState.WAITING_FOR_HUMAN
    assert handle.intervention_id is not None
    intervention = manager.store.get_intervention(handle.intervention_id)
    assert intervention.status == InterventionStatus.OPEN
    assert intervention.browser_session_id == handle.browser_session_id


@pytest.mark.asyncio
async def test_manager_claim_cancel_closes_run(tmp_path):
    manager = ReplayRunManager(
        repository=FakeRepository(),
        replay_engine=FakeEscalatingEngine(),
        handoff_store=HandoffStore(),
        evidence_dir=tmp_path,
    )
    handle = await manager.start("lookup_balance", {"member_id": "76821", "account_type": "checking"})

    claimed = await manager.claim(handle.run_id, "op1")
    assert claimed.status == InterventionStatus.CLAIMED

    result = await manager.cancel(handle.run_id, "op1")
    assert result.status == ReplayStatus.FAILED
    assert manager.get(handle.run_id).state == RunState.CANCELLED

