"""Trace normalizer for Phase 4 Capability Artifact Schema.

Strips temporary LLM-specific artifacts (observation IDs like 'e_06', reasoning strings,
token metrics, raw prompts) while retaining the ordered sequence of actions,
resolved targets, and execution outcomes.
"""

from __future__ import annotations

from typing import Any, Dict, List
from capability.exceptions import ArtifactCompilationError


class TraceNormalizer:
    """Normalizes raw Phase 3 discovery traces into clean step records."""

    def normalize(self, discovery_run: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and normalize executed steps from a discovery run."""
        status = discovery_run.get("status")
        if status not in ["success", "SUCCESS"]:
            raise ArtifactCompilationError(
                f"Cannot compile artifact: Discovery run status is '{status}', expected 'success'."
            )

        raw_steps = discovery_run.get("steps", [])
        if not raw_steps:
            raise ArtifactCompilationError("Cannot compile artifact: Discovery run has no executed steps.")

        normalized_steps: List[Dict[str, Any]] = []

        for step in raw_steps:
            decision = step.get("model_decision") or {}
            action = decision.get("action")

            # Exclude terminal finish/escalate from physical browser step sequence
            if action in ["finish", "escalate"]:
                continue

            resolved_target = step.get("resolved_target")
            action_result = step.get("action_result") or {}
            extracted_output = step.get("extracted_output")

            clean_step: Dict[str, Any] = {
                "step_number": step.get("step"),
                "action": action,
                "value": decision.get("value"),
                "resolved_target": resolved_target,
                "result_status": action_result.get("status"),
                "extracted_output": extracted_output,
            }
            normalized_steps.append(clean_step)

        if not normalized_steps:
            raise ArtifactCompilationError("Cannot compile artifact: No actionable steps remained after normalization.")

        return normalized_steps
