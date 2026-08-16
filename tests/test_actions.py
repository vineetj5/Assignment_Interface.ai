import pytest
from automation.actions import ActionExecutor
from automation.exceptions import ActionExecutionError
from automation.models import ActionRequest, ActionType, TargetSpec


def test_action_executor_target_parsing():
    executor = ActionExecutor()
    spec1 = executor._parse_target("e_05")
    assert spec1.observation_id == "e_05"

    spec2 = executor._parse_target(".balance-value")
    assert spec2.css == ".balance-value"

    spec3 = executor._parse_target("Find Member")
    assert spec3.text == "Find Member"

    spec4 = executor._parse_target({"role": "button", "name": "Submit"})
    assert spec4.role == "button"
    assert spec4.name == "Submit"
