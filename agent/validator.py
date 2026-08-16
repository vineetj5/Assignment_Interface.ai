from __future__ import annotations

from typing import Optional
from agent.context import DiscoveryContext
from agent.exceptions import DecisionValidationError
from agent.models import AgentActionType, AgentDecision, DiscoveryGoal
from automation.models import Observation


class ActionValidator:
    """Validates that an AgentDecision is semantically sound and compatible with current UI state."""

    def validate(
        self,
        decision: AgentDecision,
        observation: Observation,
        goal: DiscoveryGoal,
        context: DiscoveryContext,
    ) -> None:
        action = decision.action

        # 1. Target ID Validation for targeted actions
        if action in [AgentActionType.CLICK, AgentActionType.FILL, AgentActionType.SELECT, AgentActionType.EXTRACT]:
            if not decision.target_id:
                raise DecisionValidationError(f"Action '{action.value}' requires a non-empty 'target_id'.")

            el = observation.get_element(decision.target_id)
            if not el:
                valid_ids = [e.observation_id for e in observation.interactive_elements]
                raise DecisionValidationError(
                    f"Target ID '{decision.target_id}' was not found in the current observation. "
                    f"Available controls: {valid_ids[:10]}"
                )

            if el.disabled:
                raise DecisionValidationError(
                    f"Target '{decision.target_id}' ({el.name or el.tag}) is currently disabled in the UI."
                )

            # Element-Action Compatibility
            if action == AgentActionType.FILL:
                if decision.value is None or str(decision.value).strip() == "":
                    raise DecisionValidationError(f"Action 'fill' requires a non-empty 'value'.")
                if not el.editable and el.tag not in ["input", "textarea"]:
                    raise DecisionValidationError(
                        f"Target '{decision.target_id}' (tag: <{el.tag}>, role: {el.role}) is not an editable input field."
                    )

            elif action == AgentActionType.SELECT:
                if decision.value is None or str(decision.value).strip() == "":
                    raise DecisionValidationError(f"Action 'select' requires a 'value'.")
                if el.tag != "select" and el.role != "combobox":
                    raise DecisionValidationError(
                        f"Target '{decision.target_id}' (tag: <{el.tag}>, role: {el.role}) is not a dropdown select element."
                    )

            elif action == AgentActionType.CLICK:
                if el.tag not in ["button", "a", "input"] and el.role not in ["button", "link"]:
                    raise DecisionValidationError(
                        f"Target '{decision.target_id}' (<{el.tag}>) is not a clickable button or link."
                    )

        elif action == AgentActionType.NAVIGATE:
            if not decision.value or not (decision.value.startswith("http://") or decision.value.startswith("https://") or decision.value.startswith("/")):
                raise DecisionValidationError(f"Action 'navigate' requires a valid URL in 'value'.")

        elif action == AgentActionType.ESCALATE:
            if not decision.escalation_reason or decision.escalation_reason.strip() == "":
                raise DecisionValidationError(f"Action 'escalate' requires a non-empty 'escalation_reason'.")

        elif action == AgentActionType.FINISH:
            # Validate that either requested balance is extracted OR a valid business outcome is declared
            combined_outputs = {**context.extracted_values, **(decision.extracted_output or {})}
            is_business_outcome = any(k in combined_outputs for k in ["status", "outcome", "error", "business_outcome"])
            if not is_business_outcome and "balance" in goal.goal.lower():
                if not combined_outputs.get("current_balance") and not any("$" in str(v) for v in combined_outputs.values()):
                    raise DecisionValidationError(
                        "Cannot FINISH: Goal requested reading a balance, but no balance value has been extracted yet. "
                        "Navigate to the account detail screen and extract the balance first."
                    )
