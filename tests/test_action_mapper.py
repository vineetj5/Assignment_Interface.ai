import pytest
from agent.action_mapper import map_agent_decision_to_surface_action
from agent.models import AgentActionType, AgentDecision
from automation.models import ActionType, InteractiveElement, Observation


def test_action_mapper():
    obs = Observation(
        observation_id="obs_001",
        interactive_elements=[
            InteractiveElement(
                observation_id="e_06",
                tag="input",
                role="textbox",
                name="Member Number",
                frame_path=["legacy-app", "workspace"],
            )
        ],
    )

    decision = AgentDecision(
        action=AgentActionType.FILL,
        target_id="e_06",
        value="13278",
        reasoning_summary="Enter member number",
    )

    surface_action = map_agent_decision_to_surface_action(decision, obs)
    assert surface_action.action_type == ActionType.FILL
    assert surface_action.target.observation_id == "e_06"
    assert surface_action.target.frame_path == ["legacy-app", "workspace"]
    assert surface_action.value == "13278"
