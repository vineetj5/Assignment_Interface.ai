"""Atomic control ownership transitions for Phase 7."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Dict, Optional
from handoff.exceptions import ControlOwnershipError, InvalidStateTransitionError
from handoff.models import ControlOwner, RunState


class ControlCoordinator:
    """Coordinates run state and control ownership using one asyncio lock per run."""

    def __init__(self):
        self._owners: Dict[str, ControlOwner] = {}
        self._states: Dict[str, RunState] = {}
        self._operators: Dict[str, Optional[str]] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def initialize_run(self, run_id: str) -> None:
        async with self._locks[run_id]:
            self._owners[run_id] = ControlOwner.AUTOMATION
            self._states[run_id] = RunState.CREATED
            self._operators[run_id] = None

    async def start_running(self, run_id: str) -> None:
        async with self._locks[run_id]:
            self._require_state(run_id, {RunState.CREATED, RunState.RESUMING})
            self._owners[run_id] = ControlOwner.AUTOMATION
            self._states[run_id] = RunState.RUNNING

    async def pause_automation(self, run_id: str, reason: str = "") -> None:
        async with self._locks[run_id]:
            self._require_state(run_id, {RunState.RUNNING})
            self._states[run_id] = RunState.WAITING_FOR_HUMAN
            self._owners[run_id] = ControlOwner.NONE

    async def claim_for_human(self, run_id: str, operator_id: str) -> None:
        async with self._locks[run_id]:
            self._require_state(run_id, {RunState.WAITING_FOR_HUMAN})
            self._states[run_id] = RunState.HUMAN_CONTROL
            self._owners[run_id] = ControlOwner.HUMAN
            self._operators[run_id] = operator_id

    async def return_to_automation(self, run_id: str, operator_id: str) -> None:
        async with self._locks[run_id]:
            self._require_state(run_id, {RunState.HUMAN_CONTROL})
            if self._operators.get(run_id) != operator_id:
                raise ControlOwnershipError("Only the claiming operator may return control.")
            self._states[run_id] = RunState.RESUMING
            self._owners[run_id] = ControlOwner.AUTOMATION
            self._operators[run_id] = None

    async def mark_completed(self, run_id: str) -> None:
        async with self._locks[run_id]:
            self._states[run_id] = RunState.COMPLETED
            self._owners[run_id] = ControlOwner.NONE

    async def mark_failed(self, run_id: str) -> None:
        async with self._locks[run_id]:
            self._states[run_id] = RunState.FAILED
            self._owners[run_id] = ControlOwner.NONE

    async def cancel(self, run_id: str, operator_id: str) -> None:
        async with self._locks[run_id]:
            if self._states.get(run_id) not in {RunState.WAITING_FOR_HUMAN, RunState.HUMAN_CONTROL, RunState.RUNNING}:
                raise InvalidStateTransitionError("Run cannot be cancelled from current state.")
            claimed_by = self._operators.get(run_id)
            if claimed_by and claimed_by != operator_id:
                raise ControlOwnershipError("Only the claiming operator may cancel this run.")
            self._states[run_id] = RunState.CANCELLED
            self._owners[run_id] = ControlOwner.NONE

    async def require_automation(self, run_id: str) -> None:
        async with self._locks[run_id]:
            if self._owners.get(run_id) != ControlOwner.AUTOMATION:
                raise ControlOwnershipError("Automation does not own this run.")

    def current_owner(self, run_id: str) -> ControlOwner:
        return self._owners.get(run_id, ControlOwner.NONE)

    def current_state(self, run_id: str) -> RunState:
        return self._states.get(run_id, RunState.CREATED)

    def claimed_by(self, run_id: str) -> Optional[str]:
        return self._operators.get(run_id)

    def _require_state(self, run_id: str, allowed: set[RunState]) -> None:
        current = self._states.get(run_id)
        if current not in allowed:
            raise InvalidStateTransitionError(f"Invalid state transition from {current}.")

