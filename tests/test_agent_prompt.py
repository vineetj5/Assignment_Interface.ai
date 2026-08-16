import pytest
from agent.context import DiscoveryContext
from agent.models import AgentActionType, AgentDecision, DiscoveryGoal
from agent.prompt import build_step_prompt, build_system_prompt


def test_prompt_construction():
    sys_prompt = build_system_prompt()
    assert "You are a precise, autonomous UI discovery agent" in sys_prompt
    assert "fill" in sys_prompt
    assert "click" in sys_prompt

    goal = DiscoveryGoal(goal="Find member 13278 savings balance")
    context = DiscoveryContext(run_id="run_test")
    context.previous_action = AgentDecision(
        action=AgentActionType.FILL,
        target_id="e_06",
        value="13278",
        reasoning_summary="Fill member number",
    )
    context.previous_action_result = {"status": "success"}

    prompt = build_step_prompt(
        goal=goal,
        context=context,
        observation_summary="e_07 button 'Find Member'",
    )

    assert "Find member 13278 savings balance" in prompt
    assert "PREVIOUS ACTION" in prompt
    assert "e_07 button 'Find Member'" in prompt
