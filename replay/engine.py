"""Main Replay Engine for Phase 5 Deterministic Replay."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional
from automation.surface import PlaywrightSurface
from capability.models import CapabilityArtifact
from capability.repository import ArtifactRepository
from handoff.control import ControlCoordinator
from replay.binder import ValueBinder
from replay.condition_engine import ConditionEngine
from replay.exceptions import (
    ReplayBusinessOutcomeError,
    ReplayCheckpointFailedError,
    ReplayEscalationError,
    ReplayHardFailureError,
    ReplayInputValidationError,
    ReplayPolicyViolationError,
    ReplayTargetResolutionError,
    ReplayTimeoutError,
)
from replay.input_validator import ReplayInputValidator
from replay.models import FailureCategory, ReplayContext, ReplayRequest, ReplayResult
from replay.output_collector import OutputCollector
from replay.recorder import ReplayRecorder
from replay.recovery import ReplayRecoveryEngine
from replay.result_builder import ReplayResultBuilder
from replay.runtime_policy import ReplayRuntimePolicy
from replay.step_executor import StepExecutor


class ReplayEngine:
    """Orchestrates deterministic replay of capability artifacts without LLM decisions."""

    def __init__(
        self,
        repository: Optional[ArtifactRepository] = None,
        evidence_dir: Optional[Path] = None,
    ):
        self.repository = repository or ArtifactRepository()
        self.input_validator = ReplayInputValidator()
        self.binder = ValueBinder()
        self.condition_engine = ConditionEngine(self.binder)
        self.output_collector = OutputCollector()
        self.policy = ReplayRuntimePolicy()
        self.recovery_engine = ReplayRecoveryEngine()
        self.evidence_dir = evidence_dir

    async def execute(
        self,
        artifact: CapabilityArtifact,
        inputs: Dict[str, Any],
        run_id: Optional[str] = None,
        headful: bool = False,
        surface: Optional[PlaywrightSurface] = None,
        keep_session_on_escalation: bool = False,
        control: Optional[ControlCoordinator] = None,
    ) -> ReplayResult:
        """Execute a capability artifact with bound inputs deterministically."""
        start_time = time.time()
        capability_name = artifact.identity.name
        version = artifact.identity.version
        actual_run_id = run_id or f"replay_{int(start_time)}"

        builder = ReplayResultBuilder(
            run_id=actual_run_id,
            capability=capability_name,
            version=version,
            start_time=start_time,
        )

        recorder = ReplayRecorder(evidence_dir=self.evidence_dir, run_id=actual_run_id)

        # 1. Policy & Input Validation
        try:
            self.policy.validate_artifact(artifact)
            validated_inputs = self.input_validator.validate(artifact.inputs, inputs)
        except (ReplayPolicyViolationError, ReplayInputValidationError) as e:
            res = builder.failure(
                category=FailureCategory.INPUT_VALIDATION if isinstance(e, ReplayInputValidationError) else FailureCategory.POLICY_VIOLATION,
                message=str(e),
                evidence_dir=str(recorder.evidence_store.run_dir),
            )
            recorder.record_final_result(res)
            return res

        context = ReplayContext(
            run_id=actual_run_id,
            capability=capability_name,
            version=version,
            evidence_dir=str(recorder.evidence_store.run_dir),
        )

        owned_surface = surface is None
        surface = surface or PlaywrightSurface(
            headless=not headful,
            evidence_dir=self.evidence_dir or (Path(__file__).resolve().parent.parent / "evidence"),
            run_id=actual_run_id,
        )
        keep_surface_open = False

        steps_completed = 0
        step_executor = StepExecutor(
            binder=self.binder,
            condition_engine=self.condition_engine,
            output_collector=self.output_collector,
            control=control,
            run_id=actual_run_id,
        )

        try:
            # 2. Open entrypoint target URL
            await surface.open(artifact.entrypoint.url)
            self.policy.validate_origin(surface.session_manager.page.url, artifact.safety.allowed_origins)

            # 3. Step Loop
            search_submitted = False
            for idx, step in enumerate(artifact.steps, start=1):
                context.current_step_id = step.id
                context.current_step_index = idx

                # Execute step
                step_res = await step_executor.execute_step(step, surface, validated_inputs, context.outputs)
                steps_completed += 1
                if step.id == "search_member":
                    search_submitted = True

                # Collect extracted variables
                if step_res.get("extracted"):
                    context.outputs.update(step_res["extracted"])

                # Record step evidence
                recorder.record_step_execution(
                    step_id=step.id,
                    action=step.action.value,
                    target=step.target.model_dump() if step.target else None,
                    bound_value=self.binder.resolve(step.value, validated_inputs, context.outputs),
                    action_result=step_res.get("action_result"),
                    observation_ref=step_res.get("observation_id"),
                    extracted=step_res.get("extracted"),
                    redact_sensitive=not artifact.safety.persist_input_values,
                )

                # Check runtime traps and business outcome detectors only after the
                # search has been submitted. Demo setup steps, such as selecting the
                # test-condition dropdown, should not be interpreted as outcomes.
                if search_submitted:
                    post_step_obs = await surface.observe(capture_screenshot=False)
                    self._check_runtime_traps_and_outcomes(artifact, post_step_obs, validated_inputs, context.outputs, step.id)

            # 4. Final Success Condition Evaluation
            final_obs = await surface.observe(capture_screenshot=True)
            success_cond_res = self.condition_engine.evaluate(
                artifact.success_condition,
                validated_inputs,
                context.outputs,
                final_obs,
            )

            if not success_cond_res.matched:
                res = builder.failure(
                    category=FailureCategory.CHECKPOINT_FAILED,
                    message="Final top-level success condition failed.",
                    expected=str(success_cond_res.expected),
                    observed=str(success_cond_res.observed),
                    steps_completed=steps_completed,
                    evidence_dir=str(recorder.evidence_store.run_dir),
                )
                recorder.record_final_result(res)
                return res

            # 5. Finalize Outputs
            final_outputs = self.output_collector.finalize_outputs(
                artifact.outputs,
                validated_inputs,
                context.outputs,
            )

            res = builder.success(
                outputs=final_outputs,
                steps_completed=steps_completed,
                evidence_dir=str(recorder.evidence_store.run_dir),
            )
            recorder.record_final_result(res)
            return res

        except ReplayBusinessOutcomeError as e:
            res = builder.business_outcome(
                code=e.code,
                step_id=context.current_step_id,
                steps_completed=steps_completed,
                evidence_dir=str(recorder.evidence_store.run_dir),
            )
            recorder.record_final_result(res)
            return res

        except ReplayEscalationError as e:
            keep_surface_open = keep_session_on_escalation
            res = builder.escalation(
                code=e.code,
                reason=e.reason,
                step_id=context.current_step_id,
                steps_completed=steps_completed,
                evidence_dir=str(recorder.evidence_store.run_dir),
            )
            recorder.record_final_result(res)
            return res

        except ReplayCheckpointFailedError as e:
            res = builder.failure(
                category=FailureCategory.CHECKPOINT_FAILED,
                step_id=context.current_step_id,
                message=str(e),
                steps_completed=steps_completed,
                evidence_dir=str(recorder.evidence_store.run_dir),
            )
            recorder.record_final_result(res)
            return res

        except ReplayHardFailureError as e:
            cat_map = {
                "permission_denied": FailureCategory.PERMISSION_DENIED,
                "session_expired": FailureCategory.SESSION_EXPIRED,
                "application_error": FailureCategory.APPLICATION_ERROR,
            }
            cat = cat_map.get(e.category, FailureCategory.ACTION_FAILED)
            res = builder.failure(
                category=cat,
                step_id=context.current_step_id,
                message=str(e),
                steps_completed=steps_completed,
                evidence_dir=str(recorder.evidence_store.run_dir),
            )
            recorder.record_final_result(res)
            return res

        except Exception as e:
            res = builder.failure(
                category=FailureCategory.ACTION_FAILED,
                step_id=context.current_step_id,
                message=str(e),
                steps_completed=steps_completed,
                evidence_dir=str(recorder.evidence_store.run_dir),
            )
            recorder.record_final_result(res)
            return res

        finally:
            if owned_surface and not keep_surface_open:
                await surface.close()

    def _check_runtime_traps_and_outcomes(
        self,
        artifact: CapabilityArtifact,
        observation: Any,
        runtime_inputs: Dict[str, Any],
        step_outputs: Dict[str, Any],
        step_id: str,
    ) -> None:
        """Evaluate declared business outcomes and runtime conditions against observation."""
        # 1. Business Outcomes
        for outcome in artifact.business_outcomes:
            cond_res = self.condition_engine.evaluate(outcome.detect, runtime_inputs, step_outputs, observation)
            if cond_res.matched:
                raise ReplayBusinessOutcomeError(code=outcome.code, message=outcome.description or outcome.code)

        # 2. Runtime Conditions (failures / escalations)
        for rcond in artifact.runtime_conditions:
            cond_res = self.condition_engine.evaluate(rcond.detect, runtime_inputs, step_outputs, observation)
            if cond_res.matched:
                cat_val = rcond.category.value
                if cat_val == "escalate":
                    raise ReplayEscalationError(code=rcond.code, reason=rcond.description or rcond.code)
                elif cat_val in ["hard_failure", "business_outcome"]:
                    code_lower = rcond.code.lower()
                    raise ReplayHardFailureError(category=code_lower, message=rcond.description or rcond.code)

    async def execute_capability(
        self,
        name: str,
        inputs: Dict[str, Any],
        version: Optional[str] = None,
        headful: bool = False,
    ) -> ReplayResult:
        """Convenience loader + replay method."""
        if version is None:
            artifact = self.repository.get_approved(name)
            if artifact is None:
                raise ReplayPolicyViolationError(f"No approved version found for capability '{name}'.")
        else:
            artifact = self.repository.load(name, version)
        return await self.execute(artifact, inputs=inputs, headful=headful)
