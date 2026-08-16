from __future__ import annotations

import datetime
import hashlib
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from agent.models import AgentDecision, RecordedDiscoveryStep
from automation.models import Observation


class DiscoveryContext(BaseModel):
    run_id: str
    started_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    step_number: int = 0
    previous_action: Optional[AgentDecision] = None
    previous_action_result: Optional[Dict[str, Any]] = None
    executed_actions: List[RecordedDiscoveryStep] = Field(default_factory=list)
    extracted_values: Dict[str, Any] = Field(default_factory=dict)
    observation_fingerprints: List[str] = Field(default_factory=list)
    consecutive_failures: int = 0

    def compute_observation_fingerprint(self, obs: Observation) -> str:
        """Create a compact fingerprint of the current target observation to detect loops."""
        content = f"{obs.page_url}|{obs.page_title}|"
        for m in obs.detected_messages:
            content += f"msg:{m.code}:{m.title}|"
        for d in obs.detected_dialogs:
            content += f"dlg:{d.title}|"
        for el in obs.interactive_elements:
            content += f"{el.tag}:{el.name}:{el.value}:{el.disabled}|"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def record_step(
        self,
        decision: AgentDecision,
        observation_ref: Optional[str] = None,
        resolved_target: Optional[Dict[str, Any]] = None,
        action_result: Optional[Dict[str, Any]] = None,
        extracted_output: Optional[Dict[str, Any]] = None,
    ) -> RecordedDiscoveryStep:
        self.step_number += 1
        step = RecordedDiscoveryStep(
            step=self.step_number,
            observation_ref=observation_ref,
            model_decision=decision,
            resolved_target=resolved_target,
            action_result=action_result,
            extracted_output=extracted_output,
        )
        self.executed_actions.append(step)
        self.previous_action = decision
        self.previous_action_result = action_result

        if extracted_output:
            self.extracted_values.update(extracted_output)

        if action_result and action_result.get("status") == "success":
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1

        return step
