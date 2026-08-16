import pytest
from agent.context import DiscoveryContext
from agent.exceptions import DecisionValidationError
from agent.models import AgentActionType, AgentDecision, DiscoveryGoal
from agent.validator import ActionValidator
from automation.models import InteractiveElement, Observation


@pytest.fixture
def sample_obs():
    return Observation(
        observation_id="obs_001",
        interactive_elements=[
            InteractiveElement(
                observation_id="e_06",
                tag="input",
                role="textbox",
                name="Member Number",
                editable=True,
            ),
            InteractiveElement(
                observation_id="e_07",
                tag="input",
                role="button",
                name="Find Member",
            ),
            InteractiveElement(
                observation_id="e_08",
                tag="select",
                role="combobox",
                name="Test condition",
            ),
            InteractiveElement(
                observation_id="e_09",
                tag="a",
                role="link",
                name="View (SAV · Regular Savings)",
                disabled=True,
            ),
        ],
    )


def test_validator_success(sample_obs):
    validator = ActionValidator()
    goal = DiscoveryGoal(goal="Find balance")
    context = DiscoveryContext(run_id="run_1")

    valid_fill = AgentDecision(
        action=AgentActionType.FILL,
        target_id="e_06",
        value="13278",
        reasoning_summary="Fill member number",
    )
    validator.validate(valid_fill, sample_obs, goal, context)


def test_validator_rejects_missing_target(sample_obs):
    validator = ActionValidator()
    goal = DiscoveryGoal(goal="Find balance")
    context = DiscoveryContext(run_id="run_1")

    decision = AgentDecision(
        action=AgentActionType.CLICK,
        target_id="e_99",
        reasoning_summary="Click missing target",
    )
    with pytest.raises(DecisionValidationError):
        validator.validate(decision, sample_obs, goal, context)


def test_validator_rejects_disabled_target(sample_obs):
    validator = ActionValidator()
    goal = DiscoveryGoal(goal="Find balance")
    context = DiscoveryContext(run_id="run_1")

    decision = AgentDecision(
        action=AgentActionType.CLICK,
        target_id="e_09",
        reasoning_summary="Click disabled link",
    )
    with pytest.raises(DecisionValidationError):
        validator.validate(decision, sample_obs, goal, context)


def test_validator_rejects_premature_finish(sample_obs):
    validator = ActionValidator()
    goal = DiscoveryGoal(goal="Read member 13278 savings balance")
    context = DiscoveryContext(run_id="run_1")

    premature_finish = AgentDecision(
        action=AgentActionType.FINISH,
        reasoning_summary="Finish without extracting balance",
    )
    with pytest.raises(DecisionValidationError):
        validator.validate(premature_finish, sample_obs, goal, context)
