"""Final guardrail tests for Phase 7."""

import pytest
from handoff.control import ControlCoordinator
from handoff.exceptions import ControlOwnershipError
from routing.router import CapabilityRouter


@pytest.mark.asyncio
async def test_automation_blocked_while_human_owns_control():
    control = ControlCoordinator()
    await control.initialize_run("run_1")
    await control.start_running("run_1")
    await control.pause_automation("run_1", "verify")
    await control.claim_for_human("run_1", "op1")

    with pytest.raises(ControlOwnershipError):
        await control.require_automation("run_1")


def test_phase6_router_llm_call_counter_is_routing_only():
    router = CapabilityRouter(use_llm=False)
    assert router.routing_llm_calls == 0

