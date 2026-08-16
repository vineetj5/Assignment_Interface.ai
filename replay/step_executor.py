"""Step executor for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

from typing import Any, Dict, Optional
from automation.surface import PlaywrightSurface
from capability.models import ArtifactActionType, CapabilityStep
from handoff.control import ControlCoordinator
from replay.binder import ValueBinder
from replay.condition_engine import ConditionEngine
from replay.exceptions import (
    ReplayBusinessOutcomeError,
    ReplayCheckpointFailedError,
    ReplayEscalationError,
    ReplayHardFailureError,
)
from replay.output_collector import OutputCollector
from replay.step_interpreter import StepInterpreter
from replay.wait_engine import WaitEngine


class StepExecutor:
    """Executes a single CapabilityStep lifecycle against Playwright SurfaceAdapter."""

    def __init__(
        self,
        binder: Optional[ValueBinder] = None,
        interpreter: Optional[StepInterpreter] = None,
        wait_engine: Optional[WaitEngine] = None,
        condition_engine: Optional[ConditionEngine] = None,
        output_collector: Optional[OutputCollector] = None,
        control: Optional[ControlCoordinator] = None,
        run_id: Optional[str] = None,
    ):
        self.binder = binder or ValueBinder()
        self.interpreter = interpreter or StepInterpreter(self.binder)
        self.wait_engine = wait_engine or WaitEngine()
        self.condition_engine = condition_engine or ConditionEngine(self.binder)
        self.output_collector = output_collector or OutputCollector()
        self.control = control
        self.run_id = run_id

    async def execute_step(
        self,
        step: CapabilityStep,
        surface: PlaywrightSurface,
        runtime_inputs: Dict[str, Any],
        context_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single step, evaluate waits/checkpoints, and return result dict."""
        # 1. Wait before
        if step.wait_before:
            await self.wait_engine.wait(step.wait_before, surface)

        # 2. Interpret step to ActionRequest
        action_request = self.interpreter.interpret(step, runtime_inputs, context_outputs)

        # 3. Execute via SurfaceAdapter
        if self.control and self.run_id:
            await self.control.require_automation(self.run_id)
        exec_result = await surface.execute(action_request)
        if exec_result.status != "success":
            raise ReplayCheckpointFailedError(
                f"Browser action execution failed on step '{step.id}': {exec_result.error}"
            )

        # 4. Wait after
        if step.wait_after:
            await self.wait_engine.wait(step.wait_after, surface)

        # Observe current state after step completion
        obs = await surface.observe(capture_screenshot=True)

        # 5. Check postconditions
        for postcond in step.postconditions:
            cond_res = self.condition_engine.evaluate(postcond, runtime_inputs, context_outputs, obs)
            if not cond_res.matched:
                raise ReplayCheckpointFailedError(
                    f"Postcondition checkpoint failed on step '{step.id}' (expected: {cond_res.expected}, details: {cond_res.details})"
                )

        # 6. Extract output if applicable
        extracted_data: Optional[Dict[str, Any]] = None
        if step.action == ArtifactActionType.EXTRACT and step.extraction:
            raw_text = exec_result.output.get("text") if isinstance(exec_result.output, dict) else str(exec_result.output)
            transformed = self.output_collector.transform_value(raw_text, step.extraction)
            extracted_data = {step.extraction.output: transformed}

        return {
            "status": "success",
            "action_result": exec_result.model_dump(),
            "observation_id": obs.observation_id,
            "extracted": extracted_data,
        }
