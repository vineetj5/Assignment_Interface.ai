from __future__ import annotations

import datetime
from typing import List, Optional
from automation.models import ActionRequest, ActionResult, ActionType
from automation.evidence import EvidenceStore


class ActionLogger:
    """Records structured action steps and dispatches to evidence storage."""

    def __init__(self, evidence_store: Optional[EvidenceStore] = None):
        self.evidence_store = evidence_store
        self.step_count = 0
        self.history: List[ActionResult] = []

    def start_action(self, request: ActionRequest) -> str:
        self.step_count += 1
        action_id = f"act_{self.step_count:03d}"
        return action_id

    def record_action(
        self,
        action_id: str,
        action_type: ActionType,
        status: str,
        started_at: str,
        completed_at: str,
        duration_ms: float,
        output: any = None,
        error: Optional[str] = None,
        before_observation_ref: Optional[str] = None,
        after_observation_ref: Optional[str] = None,
        screenshot_ref: Optional[str] = None,
    ) -> ActionResult:
        result = ActionResult(
            action_id=action_id,
            action_type=action_type,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            output=output,
            error=error,
            before_observation_ref=before_observation_ref,
            after_observation_ref=after_observation_ref,
            screenshot_ref=screenshot_ref,
        )
        self.history.append(result)
        if self.evidence_store:
            self.evidence_store.append_action(result, step=self.step_count)
        return result
