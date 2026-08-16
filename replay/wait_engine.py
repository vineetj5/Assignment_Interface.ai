"""Wait condition engine for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional
from automation.surface import PlaywrightSurface
from capability.models import WaitSpec
from replay.exceptions import ReplayTimeoutError


class WaitEngine:
    """Evaluates artifact WaitSpecs using condition polling rather than fixed sleeps."""

    async def wait(
        self,
        wait_spec: Optional[WaitSpec],
        surface: PlaywrightSurface,
        timeout_ms: Optional[int] = None,
    ) -> None:
        """Wait for the condition defined in wait_spec to be satisfied."""
        if not wait_spec:
            return

        timeout = (timeout_ms or wait_spec.timeout_ms or 5000) / 1000.0
        start_time = time.time()

        wait_type = wait_spec.type

        if wait_type == "sleep" or wait_type == "timeout":
            ms = int(wait_spec.value or 500)
            await asyncio.sleep(ms / 1000.0)
            return

        if wait_type in ["networkidle", "domcontentloaded", "load"]:
            try:
                page = surface.session_manager.page
                await page.wait_for_load_state(wait_type, timeout=int(timeout * 1000))
            except Exception as exc:
                raise ReplayTimeoutError(
                    f"Timed out waiting for page load state '{wait_type}' within {int(timeout * 1000)}ms."
                ) from exc
            return

        # Condition polling loop
        while (time.time() - start_time) < timeout:
            obs = await surface.observe(capture_screenshot=False)
            satisfied = self._evaluate_wait_condition(wait_spec, obs.visible_text)
            if satisfied:
                return
            await asyncio.sleep(0.15)

        raise ReplayTimeoutError(
            f"Timed out waiting for condition '{wait_type}' with value '{wait_spec.value}' within {int(timeout * 1000)}ms."
        )

    def _evaluate_wait_condition(self, wait_spec: WaitSpec, text: str) -> bool:
        wtype = wait_spec.type
        val = str(wait_spec.value or "").strip()

        if wtype == "text_visible":
            return val in text if val else True

        elif wtype == "any_of":
            if not wait_spec.conditions:
                return True
            return any(self._evaluate_wait_condition(sub, text) for sub in wait_spec.conditions)

        elif wtype == "all_of":
            if not wait_spec.conditions:
                return True
            return all(self._evaluate_wait_condition(sub, text) for sub in wait_spec.conditions)

        return False
