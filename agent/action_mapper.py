from __future__ import annotations

from typing import Optional
from agent.models import AgentActionType, AgentDecision
from automation.models import ActionRequest, ActionType, Observation, TargetSpec


def map_agent_decision_to_surface_action(
    decision: AgentDecision,
    observation: Observation,
) -> ActionRequest:
    """Map a high-level AgentDecision into a concrete Phase 2 ActionRequest."""
    target_spec: Optional[TargetSpec] = None

    if decision.target_id:
        el = observation.get_element(decision.target_id)
        if el:
            target_spec = TargetSpec(
                observation_id=el.observation_id,
                role=el.role,
                name=el.name,
                text=el.text,
                tag=el.tag,
                attributes=el.attributes,
                frame_path=el.frame_path,
            )
        else:
            target_spec = TargetSpec(observation_id=decision.target_id)

    action_type = ActionType(decision.action.value)

    return ActionRequest(
        action_type=action_type,
        target=target_spec,
        value=decision.value,
        metadata={
            "reasoning_summary": decision.reasoning_summary,
            "expected_result": decision.expected_result,
        },
    )
