from __future__ import annotations


class SurfaceError(Exception):
    """Base exception for all surface automation errors."""
    pass


class SessionError(SurfaceError):
    """Raised when an operation is invalid for current session status or ownership."""
    pass


class ActionExecutionError(SurfaceError):
    """Raised when an action fails to execute on the surface."""
    pass


class ElementNotFoundError(ActionExecutionError):
    """Raised when a target interactive element cannot be resolved."""
    pass


class ConditionTimeoutError(ActionExecutionError):
    """Raised when waiting for a condition times out."""
    pass


class ControlOwnershipError(SessionError):
    """Raised when attempting an automation action while control is ceded to a human."""
    pass
