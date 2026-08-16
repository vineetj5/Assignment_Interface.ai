"""Step interpreter for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

from typing import Any, Dict, Optional
from capability.models import ArtifactActionType, CapabilityStep
from automation.models import ActionRequest, ActionType
from replay.binder import ValueBinder
from replay.target_resolver import TargetResolver


class StepInterpreter:
    """Translates a CapabilityStep + bound runtime inputs into a Phase 2 ActionRequest."""

    def __init__(self, binder: Optional[ValueBinder] = None, target_resolver: Optional[TargetResolver] = None):
        self.binder = binder or ValueBinder()
        self.target_resolver = target_resolver or TargetResolver(self.binder)

    def interpret(
        self,
        step: CapabilityStep,
        runtime_inputs: Dict[str, Any],
        step_outputs: Optional[Dict[str, Any]] = None,
    ) -> ActionRequest:
        """Construct Phase 2 ActionRequest from CapabilityStep and runtime environment."""
        action_str = step.action.value
        action_map = {
            "navigate": ActionType.NAVIGATE,
            "click": ActionType.CLICK,
            "fill": ActionType.FILL,
            "select": ActionType.SELECT,
            "extract": ActionType.EXTRACT,
            "wait": ActionType.WAIT,
        }

        if action_str not in action_map:
            raise ValueError(f"Unsupported step action type '{action_str}' in step '{step.id}'")

        action_type = action_map[action_str]

        # Bind target spec
        surface_target = self.target_resolver.resolve(
            artifact_target=step.target,
            runtime_inputs=runtime_inputs,
            step_outputs=step_outputs,
        )

        # Bind value
        bound_val = self.binder.resolve(step.value, runtime_inputs, step_outputs)
        val_str = str(bound_val) if bound_val is not None else None

        return ActionRequest(
            action_type=action_type,
            target=surface_target,
            value=val_str,
            metadata={"step_id": step.id},
        )
