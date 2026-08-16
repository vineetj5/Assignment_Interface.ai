from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable
from automation.models import (
    ActionRequest,
    ActionResult,
    Observation,
    SessionState,
    ControlOwner,
)


@runtime_checkable
class SurfaceAdapter(Protocol):
    """Generic interface / protocol for any computer control surface adapter."""

    async def open(self, target: str) -> None:
        """Open or navigate to the target surface."""
        ...

    async def observe(self, capture_screenshot: bool = True) -> Observation:
        """Capture the current state, controls, messages, and layout of the surface."""
        ...

    async def execute(self, action: ActionRequest) -> ActionResult:
        """Execute a typed action against the surface."""
        ...

    async def screenshot(self, name: Optional[str] = None) -> str:
        """Capture and persist a screenshot, returning the relative path or identifier."""
        ...

    async def pause(self) -> None:
        """Pause automation operations on this session."""
        ...

    async def resume(self) -> None:
        """Resume automation operations on this session."""
        ...

    async def cede_control(self) -> None:
        """Cede control to a human operator."""
        ...

    async def reclaim_control(self) -> None:
        """Reclaim control from human operator back to automation."""
        ...

    async def close(self) -> None:
        """Close the session and release resources."""
        ...

    def get_session_state(self) -> SessionState:
        """Get the current session state and control ownership."""
        ...
