from __future__ import annotations

import asyncio
import time
from typing import Optional
from agent.action_mapper import map_agent_decision_to_surface_action
from agent.config import AgentSettings
from agent.context import DiscoveryContext
from agent.exceptions import (
    DecisionValidationError,
    PolicyViolationError,
    StoppingConditionReached,
)
from agent.llm_client import LLMClient
from agent.models import AgentActionType, AgentDecision, DiscoveryGoal
from agent.policy import PolicyGuard
from agent.recorder import DiscoveryRecorder
from agent.results import DiscoveryRunResult, DiscoveryRunStatus
from agent.validator import ActionValidator
from automation.adapter import SurfaceAdapter


async def run_discovery(
    goal: DiscoveryGoal,
    surface: SurfaceAdapter,
    llm: LLMClient,
    settings: Optional[AgentSettings] = None,
    recorder: Optional[DiscoveryRecorder] = None,
) -> DiscoveryRunResult:
    """Execute the autonomous observe -> decide -> validate -> act discovery loop."""
    settings = settings or AgentSettings()
    start_time = time.time()

    # Initialize context and helpers
    run_id = f"discovery_{int(start_time)}"
    context = DiscoveryContext(run_id=run_id)
    validator = ActionValidator()
    policy = PolicyGuard()

    # Step 1: Open initial target URL
    await surface.open(goal.target_url)

    status = DiscoveryRunStatus.STOPPED
    stop_reason = None
    error_msg = None
    validation_error = None

    while context.step_number < goal.max_steps:
        # Check overall timeout
        elapsed = time.time() - start_time
        if elapsed > goal.timeout_seconds:
            status = DiscoveryRunStatus.STOPPED
            stop_reason = f"Overall timeout of {goal.timeout_seconds}s exceeded."
            break

        # Check consecutive failures
        if context.consecutive_failures >= settings.max_consecutive_failures:
            status = DiscoveryRunStatus.STOPPED
            stop_reason = f"Exceeded max consecutive failures ({settings.max_consecutive_failures})."
            break

        # 1. Observe current UI
        obs = await surface.observe(capture_screenshot=True)
        obs_ref = obs.observation_id
        obs_summary = obs.to_llm_summary(scope_to_target=True)

        # Loop detection
        fp = context.compute_observation_fingerprint(obs)
        context.observation_fingerprints.append(fp)
        if context.observation_fingerprints.count(fp) > settings.same_observation_limit:
            status = DiscoveryRunStatus.STOPPED
            stop_reason = f"Detected repeated UI state loop ({settings.same_observation_limit} times) without progress."
            break

        # 2. Decide next action via LLM
        decision: Optional[AgentDecision] = None
        for attempt in range(2 if settings.reprompt_on_invalid_decision else 1):
            try:
                decision = await llm.decide(
                    goal=goal,
                    observation_summary=obs_summary,
                    context=context,
                    validation_error=validation_error,
                )
                # 3. Validate decision
                validator.validate(decision, obs, goal, context)
                policy.enforce(decision, goal)
                validation_error = None
                break
            except (DecisionValidationError, PolicyViolationError) as e:
                validation_error = str(e)
                if attempt == 1 or not settings.reprompt_on_invalid_decision:
                    status = DiscoveryRunStatus.FAILED
                    error_msg = f"Decision validation failed: {e}"
                    break

        if error_msg or not decision:
            break

        # 4. Handle Terminal Decisions
        if decision.action == AgentActionType.FINISH:
            status = DiscoveryRunStatus.SUCCESS
            outputs = {**context.extracted_values, **(decision.extracted_output or {})}
            step_record = context.record_step(
                decision=decision,
                observation_ref=obs_ref,
                extracted_output=outputs,
                action_result={"status": "success", "terminal": "finish"},
            )
            if recorder:
                recorder.record_step(step_record)
            break

        if decision.action == AgentActionType.ESCALATE:
            status = DiscoveryRunStatus.ESCALATED
            error_msg = decision.escalation_reason or "Escalation requested by agent."
            step_record = context.record_step(
                decision=decision,
                observation_ref=obs_ref,
                action_result={"status": "escalated", "reason": error_msg},
            )
            if recorder:
                recorder.record_step(step_record)
            break

        # 5. Map & Execute action through SurfaceAdapter
        action_request = map_agent_decision_to_surface_action(decision, obs)
        resolved_target_dict = action_request.target.model_dump() if action_request.target else None

        extracted_output = None
        action_result_dict = None
        try:
            exec_result = await surface.execute(action_request)
            action_result_dict = exec_result.model_dump()

            if decision.action == AgentActionType.EXTRACT and exec_result.output:
                extracted_text = exec_result.output.get("text")
                if extracted_text:
                    extracted_output = {"current_balance": extracted_text}
                    context.extracted_values.update(extracted_output)

        except Exception as e:
            action_result_dict = {"status": "failed", "error": str(e)}

        # Record step
        step_record = context.record_step(
            decision=decision,
            observation_ref=obs_ref,
            resolved_target=resolved_target_dict,
            action_result=action_result_dict,
            extracted_output=extracted_output,
        )
        if recorder:
            recorder.record_step(step_record)

    # Post-loop finalization
    if context.step_number >= goal.max_steps and status not in [DiscoveryRunStatus.SUCCESS, DiscoveryRunStatus.ESCALATED]:
        status = DiscoveryRunStatus.STOPPED
        stop_reason = f"Reached maximum allowed steps ({goal.max_steps})."

    duration = round(time.time() - start_time, 2)
    final_outputs = context.extracted_values if status == DiscoveryRunStatus.SUCCESS else None

    result = DiscoveryRunResult(
        status=status,
        run_id=run_id,
        goal=goal,
        steps_count=context.step_number,
        duration_seconds=duration,
        outputs=final_outputs,
        stop_reason=stop_reason,
        error_message=error_msg,
        evidence_dir=str(recorder.run_dir) if recorder else None,
        steps=context.executed_actions,
    )

    if recorder:
        recorder.record_result(result)

    return result
