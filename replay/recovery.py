"""Recovery engine for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional
from automation.surface import PlaywrightSurface
from capability.models import RecoverySpec, RuntimeConditionSpec
from replay.models import RecoveryRecord


class ReplayRecoveryEngine:
    """Executes bounded, schema-defined recovery operations for recoverable conditions."""

    def __init__(self):
        self.recovery_counts: Dict[str, int] = {}

    async def attempt_recovery(
        self,
        condition_spec: RuntimeConditionSpec,
        surface: PlaywrightSurface,
    ) -> Optional[RecoveryRecord]:
        """Attempt recovery if declared in RecoverySpec, enforcing bounded max_attempts."""
        rec_spec = condition_spec.recovery
        if not rec_spec:
            return None

        code = condition_spec.code
        current_attempts = self.recovery_counts.get(code, 0)

        if current_attempts >= rec_spec.max_attempts:
            return None

        self.recovery_counts[code] = current_attempts + 1

        if rec_spec.action == "wait":
            ms = rec_spec.timeout_ms or 3000
            await asyncio.sleep(ms / 1000.0)

        record = RecoveryRecord(
            code=code,
            attempt=current_attempts + 1,
            action=rec_spec.action,
            status="recovered",
        )
        return record
