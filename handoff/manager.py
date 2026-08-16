"""Replay run manager for Phase 7 same-session human handoff."""

from __future__ import annotations

import copy
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from automation.surface import PlaywrightSurface
from capability.models import ArtifactActionType, CapabilityArtifact, CapabilityStep, FrameTarget, LocatorStrategy, TargetSpec, ValueSource
from capability.repository import ArtifactRepository
from handoff.action_capture import HumanActionCapture
from handoff.cleanup import HandoffCleanup
from handoff.continuation import ReplayContinuationBuilder
from handoff.control import ControlCoordinator
from handoff.exceptions import InterventionNotFoundError
from handoff.models import (
    ControlOwner,
    InterventionRequest,
    InterventionSource,
    InterventionStatus,
    RunHandle,
    RunState,
)
from handoff.policy import HandoffPolicy
from handoff.recorder import HandoffRecorder
from handoff.store import HandoffStore, store
from replay.engine import ReplayEngine
from replay.models import ReplayResult, ReplayStatus


class ReplayRunManager:
    """Owns replay browser sessions and coordinates human handoff lifecycle."""

    def __init__(
        self,
        repository: Optional[ArtifactRepository] = None,
        replay_engine: Optional[ReplayEngine] = None,
        control: Optional[ControlCoordinator] = None,
        handoff_store: Optional[HandoffStore] = None,
        evidence_dir: Optional[Path] = None,
    ):
        self.repository = repository or ArtifactRepository()
        self.replay_engine = replay_engine or ReplayEngine(repository=self.repository, evidence_dir=evidence_dir)
        self.control = control or ControlCoordinator()
        self.store = handoff_store or store
        self.evidence_dir = evidence_dir
        self.recorder = HandoffRecorder(evidence_dir=evidence_dir)
        self.cleanup = HandoffCleanup()
        self.policy = HandoffPolicy()
        self.continuations = ReplayContinuationBuilder()
        self.action_capture = HumanActionCapture()
        self._surfaces: Dict[str, PlaywrightSurface] = {}

    async def start(
        self,
        capability: str,
        inputs: Dict[str, Any],
        headful: bool = False,
        target_url: Optional[str] = None,
    ) -> RunHandle:
        run_id = f"handoff_{uuid.uuid4().hex[:10]}"
        browser_session_id = f"browser_session_{uuid.uuid4().hex[:10]}"
        await self.control.initialize_run(run_id)
        await self.control.start_running(run_id)

        artifact = self.repository.get_approved(capability)
        if artifact is None:
            raise ValueError(f"No approved artifact for {capability}.")
        artifact = self._with_demo_test_condition(artifact, inputs)
        if target_url:
            artifact.entrypoint.url = target_url
            if target_url not in artifact.safety.allowed_origins:
                artifact.safety.allowed_origins.append(target_url)

        surface = PlaywrightSurface(
            headless=not headful,
            evidence_dir=self.evidence_dir or (Path(__file__).resolve().parent.parent / "evidence"),
            run_id=run_id,
        )
        surface.session_manager.session_id = browser_session_id
        self._surfaces[run_id] = surface

        handle = RunHandle(
            run_id=run_id,
            capability=capability,
            inputs=dict(inputs),
            state=RunState.RUNNING,
            owner=ControlOwner.AUTOMATION,
            browser_session_id=browser_session_id,
            capability_version=artifact.identity.version,
            continuation=self.continuations.build(
                run_id=run_id,
                artifact_name=capability,
                artifact_version=artifact.identity.version,
                inputs=dict(inputs),
            ),
        )
        self.store.save_run(handle)

        result = await self.replay_engine.execute(
            artifact,
            inputs=inputs,
            run_id=run_id,
            headful=headful,
            surface=surface,
            keep_session_on_escalation=True,
            control=self.control,
        )
        handle.replay_run_id = result.run_id
        handle.evidence_dir = result.evidence_dir

        if result.status == ReplayStatus.ESCALATED:
            await self.control.pause_automation(run_id, reason=result.escalation.reason if result.escalation else "")
            handle.state = RunState.WAITING_FOR_HUMAN
            handle.owner = ControlOwner.NONE
            intervention = self._create_intervention(handle, result)
            handle.intervention_id = intervention.intervention_id
            result.intervention_id = intervention.intervention_id
            self.store.save_intervention(intervention)
            self.recorder.record_event(run_id, "intervention_opened", intervention.model_dump(mode="json"))
        else:
            await self._terminal_cleanup(handle, result)

        self.store.save_run(handle)
        return handle

    async def claim(self, run_id: str, operator_id: str) -> InterventionRequest:
        handle = self.get(run_id)
        intervention = self._get_intervention(handle)
        await self.control.claim_for_human(run_id, operator_id)
        intervention.status = InterventionStatus.CLAIMED
        intervention.claimed_by = operator_id
        import datetime
        intervention.claimed_at = datetime.datetime.now(datetime.timezone.utc)
        handle.state = RunState.HUMAN_CONTROL
        handle.owner = ControlOwner.HUMAN
        self.store.save_intervention(intervention)
        self.store.save_run(handle)
        self.recorder.record_event(run_id, "claimed", {"operator_id": operator_id})
        return intervention

    async def resume(self, run_id: str, operator_id: str) -> ReplayResult:
        handle = self.get(run_id)
        intervention = self._get_intervention(handle)
        self.policy.require_human_owner(handle, operator_id, intervention.claimed_by)
        before = handle.browser_session_id
        surface = self._surfaces.get(run_id)
        if not surface:
            raise InterventionNotFoundError("Live browser session is not available.")
        self.policy.require_same_browser_session(before, surface.session_manager.session_id)

        await self.control.return_to_automation(run_id, operator_id)
        handle.state = RunState.RESUMING
        handle.owner = ControlOwner.AUTOMATION
        self.store.save_run(handle)

        # Phase 7 safe-resume seam: re-observe the same live session. If the
        # escalation is still present, re-open the intervention. If it is gone,
        # return a deterministic resumed result for this demo boundary.
        obs = await surface.observe(capture_screenshot=True)
        if "Verification" in obs.visible_text or "verification" in obs.visible_text:
            await self.control.pause_automation(run_id, reason="Escalation condition still present.")
            handle.state = RunState.WAITING_FOR_HUMAN
            handle.owner = ControlOwner.NONE
            intervention.status = InterventionStatus.OPEN
            self.store.save_intervention(intervention)
            self.store.save_run(handle)
            return ReplayResult(
                status=ReplayStatus.ESCALATED,
                run_id=run_id,
                capability=handle.capability,
                version=handle.capability_version or "",
                steps_completed=handle.continuation.current_step_index if handle.continuation else 0,
                evidence_dir=handle.evidence_dir,
            )

        intervention.status = InterventionStatus.RESOLVED
        import datetime
        intervention.resumed_at = datetime.datetime.now(datetime.timezone.utc)
        await self.control.mark_completed(run_id)
        handle.state = RunState.COMPLETED
        handle.owner = ControlOwner.NONE
        self.store.save_intervention(intervention)
        self.store.save_run(handle)
        await self.cleanup.close_surface(surface)
        self._surfaces.pop(run_id, None)
        self.recorder.record_event(run_id, "resumed", {"operator_id": operator_id})
        return ReplayResult(
            status=ReplayStatus.SUCCESS,
            run_id=run_id,
            capability=handle.capability,
            version=handle.capability_version or "",
            outputs={},
            steps_completed=handle.continuation.current_step_index if handle.continuation else 0,
            evidence_dir=handle.evidence_dir,
        )

    async def cancel(self, run_id: str, operator_id: str) -> ReplayResult:
        handle = self.get(run_id)
        intervention = self._get_intervention(handle)
        await self.control.cancel(run_id, operator_id)
        intervention.status = InterventionStatus.CANCELLED
        handle.state = RunState.CANCELLED
        handle.owner = ControlOwner.NONE
        surface = self._surfaces.pop(run_id, None)
        await self.cleanup.close_surface(surface)
        self.store.save_intervention(intervention)
        self.store.save_run(handle)
        self.recorder.record_event(run_id, "cancelled", {"operator_id": operator_id})
        return ReplayResult(
            status=ReplayStatus.FAILED,
            run_id=run_id,
            capability=handle.capability,
            version=handle.capability_version or "",
            steps_completed=0,
            evidence_dir=handle.evidence_dir,
        )

    def get(self, run_id: str) -> RunHandle:
        handle = self.store.get_run(run_id)
        if not handle:
            raise InterventionNotFoundError(f"Run '{run_id}' not found.")
        return handle

    def list_open_interventions(self):
        return self.store.list_open()

    def surface_for(self, run_id: str) -> Optional[PlaywrightSurface]:
        return self._surfaces.get(run_id)

    def _with_demo_test_condition(self, artifact: CapabilityArtifact, inputs: Dict[str, Any]) -> CapabilityArtifact:
        """Add a demo-only legacy test-condition selector without changing the approved artifact on disk."""
        test_condition = inputs.get("test_condition")
        if not test_condition or test_condition == "normal":
            return artifact

        allowed_conditions = {
            "member_not_found",
            "permission_denied",
            "slow_response",
            "session_expired",
            "unexpected_dialog",
            "app_error",
        }
        if test_condition not in allowed_conditions:
            raise ValueError(f"Unsupported demo test_condition: {test_condition}")

        demo_artifact = copy.deepcopy(artifact)
        if ArtifactActionType.SELECT.value not in demo_artifact.safety.allowed_actions:
            demo_artifact.safety.allowed_actions.append(ArtifactActionType.SELECT.value)

        select_step = CapabilityStep(
            id="select_demo_test_condition",
            action=ArtifactActionType.SELECT,
            target=TargetSpec(
                frame_path=[FrameTarget(name="legacy-app"), FrameTarget(name="workspace")],
                primary=LocatorStrategy(
                    strategy="attributes",
                    tag="select",
                    attributes={"name": "test_condition"},
                ),
            ),
            value=ValueSource(source="literal", value=test_condition),
        )

        if any(step.id == select_step.id for step in demo_artifact.steps):
            return demo_artifact

        insert_at = 1
        for idx, step in enumerate(demo_artifact.steps):
            if step.id == "enter_member_id":
                insert_at = idx + 1
                break
        demo_artifact.steps.insert(insert_at, select_step)
        return demo_artifact

    def _create_intervention(self, handle: RunHandle, result: ReplayResult) -> InterventionRequest:
        escalation = result.escalation
        return InterventionRequest(
            intervention_id=f"int_{uuid.uuid4().hex[:10]}",
            run_id=handle.run_id,
            source=InterventionSource.REPLAY,
            capability=handle.capability,
            capability_version=handle.capability_version,
            reason_code=escalation.code if escalation else "ESCALATED",
            reason=escalation.reason if escalation else "Replay requires human intervention.",
            expected_state="Automation-safe replay condition",
            observed_state=escalation.reason if escalation else "Escalation encountered",
            browser_session_id=handle.browser_session_id,
        )

    async def _terminal_cleanup(self, handle: RunHandle, result: ReplayResult) -> None:
        if result.status in {ReplayStatus.SUCCESS, ReplayStatus.BUSINESS_OUTCOME}:
            await self.control.mark_completed(handle.run_id)
            handle.state = RunState.COMPLETED
        else:
            await self.control.mark_failed(handle.run_id)
            handle.state = RunState.FAILED
        handle.owner = ControlOwner.NONE
        surface = self._surfaces.pop(handle.run_id, None)
        await self.cleanup.close_surface(surface)

    def _get_intervention(self, handle: RunHandle) -> InterventionRequest:
        if not handle.intervention_id:
            raise InterventionNotFoundError("Run has no intervention.")
        intervention = self.store.get_intervention(handle.intervention_id)
        if not intervention:
            raise InterventionNotFoundError(handle.intervention_id)
        return intervention


manager = ReplayRunManager()
