"""Continuation helpers for Phase 7 replay resume."""

from __future__ import annotations

from handoff.models import ReplayContinuation, ResumeMode


class ReplayContinuationBuilder:
    def build(
        self,
        run_id: str,
        artifact_name: str,
        artifact_version: str,
        inputs: dict,
        current_step_index: int = 0,
        current_step_id: str | None = None,
        collected_outputs: dict | None = None,
        resume_mode: ResumeMode = ResumeMode.RECHECK_CURRENT_STEP,
    ) -> ReplayContinuation:
        return ReplayContinuation(
            run_id=run_id,
            artifact_name=artifact_name,
            artifact_version=artifact_version,
            current_step_index=current_step_index,
            current_step_id=current_step_id,
            inputs=inputs,
            collected_outputs=collected_outputs or {},
            resume_mode=resume_mode,
        )

