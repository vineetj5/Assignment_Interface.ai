import pytest
from agent.models import AgentActionType, AgentDecision, DiscoveryGoal, RecordedDiscoveryStep
from agent.results import DiscoveryRunResult, DiscoveryRunStatus


def test_agent_models():
    goal = DiscoveryGoal(goal="Look up member 13278 and read savings balance.")
    assert goal.max_steps == 15
    assert goal.timeout_seconds == 120

    decision = AgentDecision(
        action=AgentActionType.FILL,
        target_id="e_06",
        value="13278",
        reasoning_summary="Enter member number into search box.",
        expected_result="Input contains 13278",
    )
    assert decision.action == AgentActionType.FILL
    assert decision.target_id == "e_06"
    assert decision.value == "13278"

    step = RecordedDiscoveryStep(
        step=1,
        observation_ref="obs_001",
        model_decision=decision,
        action_result={"status": "success"},
    )
    assert step.step == 1

    result = DiscoveryRunResult(
        status=DiscoveryRunStatus.SUCCESS,
        run_id="disc_001",
        goal=goal,
        steps_count=4,
        duration_seconds=1.25,
        outputs={"member_id": "13278", "current_balance": "$5,521.10"},
    )
    assert result.status == DiscoveryRunStatus.SUCCESS
    assert result.outputs["current_balance"] == "$5,521.10"
