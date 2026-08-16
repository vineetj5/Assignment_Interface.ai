"""Result builder helper for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from replay.models import (
    BusinessOutcomeResult,
    EscalationResult,
    FailureCategory,
    ReplayFailure,
    ReplayResult,
    ReplayStatus,
)


class ReplayResultBuilder:
    """Helper class to construct standardized ReplayResult objects."""

    def __init__(self, run_id: str, capability: str, version: str, start_time: float):
        self.run_id = run_id
        self.capability = capability
        self.version = version
        self.start_time = start_time

    def _elapsed(self) -> float:
        return round(time.time() - self.start_time, 2)

    def success(
        self,
        outputs: Dict[str, Any],
        steps_completed: int,
        evidence_dir: Optional[str] = None,
    ) -> ReplayResult:
        return ReplayResult(
            status=ReplayStatus.SUCCESS,
            run_id=self.run_id,
            capability=self.capability,
            version=self.version,
            outputs=outputs,
            steps_completed=steps_completed,
            duration_seconds=self._elapsed(),
            evidence_dir=evidence_dir,
        )

    def business_outcome(
        self,
        code: str,
        step_id: Optional[str] = None,
        description: Optional[str] = None,
        steps_completed: int = 0,
        evidence_dir: Optional[str] = None,
    ) -> ReplayResult:
        return ReplayResult(
            status=ReplayStatus.BUSINESS_OUTCOME,
            run_id=self.run_id,
            capability=self.capability,
            version=self.version,
            outcome=BusinessOutcomeResult(code=code, step_id=step_id, description=description),
            steps_completed=steps_completed,
            duration_seconds=self._elapsed(),
            evidence_dir=evidence_dir,
        )

    def failure(
        self,
        category: FailureCategory,
        step_id: Optional[str] = None,
        message: Optional[str] = None,
        expected: Optional[str] = None,
        observed: Optional[str] = None,
        recoverable: bool = False,
        steps_completed: int = 0,
        evidence_dir: Optional[str] = None,
    ) -> ReplayResult:
        return ReplayResult(
            status=ReplayStatus.FAILED,
            run_id=self.run_id,
            capability=self.capability,
            version=self.version,
            failure=ReplayFailure(
                category=category,
                step_id=step_id,
                message=message,
                expected=expected,
                observed=observed,
                recoverable=recoverable,
            ),
            steps_completed=steps_completed,
            duration_seconds=self._elapsed(),
            evidence_dir=evidence_dir,
        )

    def escalation(
        self,
        code: str,
        reason: str,
        step_id: Optional[str] = None,
        steps_completed: int = 0,
        evidence_dir: Optional[str] = None,
    ) -> ReplayResult:
        return ReplayResult(
            status=ReplayStatus.ESCALATED,
            run_id=self.run_id,
            capability=self.capability,
            version=self.version,
            escalation=EscalationResult(code=code, step_id=step_id, reason=reason),
            steps_completed=steps_completed,
            duration_seconds=self._elapsed(),
            evidence_dir=evidence_dir,
        )
