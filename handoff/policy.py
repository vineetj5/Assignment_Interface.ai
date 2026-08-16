"""Policy checks for Phase 7 handoff."""

from __future__ import annotations

from handoff.exceptions import ControlOwnershipError
from handoff.models import ControlOwner, RunHandle, RunState


class HandoffPolicy:
    def require_human_owner(self, handle: RunHandle, operator_id: str, claimed_by: str | None) -> None:
        if handle.owner != ControlOwner.HUMAN or handle.state != RunState.HUMAN_CONTROL:
            raise ControlOwnershipError("Run is not currently under human control.")
        if claimed_by != operator_id:
            raise ControlOwnershipError("Operator does not own this intervention.")

    def require_same_browser_session(self, before: str, after: str) -> None:
        if before != after:
            raise ControlOwnershipError("Browser session identity changed during handoff.")

