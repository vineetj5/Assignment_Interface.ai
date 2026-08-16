"""Tests for Phase 5 Step Interpreter."""

from capability.models import ArtifactActionType, CapabilityStep, LocatorStrategy, TargetSpec as ArtifactTargetSpec, ValueSource
from replay.step_interpreter import StepInterpreter


def test_step_interpreter_fill_action():
    interpreter = StepInterpreter()
    step = CapabilityStep(
        id="enter_member_id",
        action=ArtifactActionType.FILL,
        target=ArtifactTargetSpec(
            primary=LocatorStrategy(strategy="role_name", role="textbox", name="Member Number")
        ),
        value=ValueSource(source="input", name="member_id"),
    )

    action_request = interpreter.interpret(step, runtime_inputs={"member_id": "76821"})
    assert action_request.action_type.value == "fill"
    assert action_request.value == "76821"
    assert action_request.target.name == "Member Number"
