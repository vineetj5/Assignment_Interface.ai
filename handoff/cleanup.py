"""Resource cleanup helpers for Phase 7."""

from __future__ import annotations

from typing import Any


class HandoffCleanup:
    async def close_surface(self, surface: Any) -> None:
        if surface:
            await surface.close()

