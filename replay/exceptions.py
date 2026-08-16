"""Exceptions for Phase 5 Deterministic Replay Engine."""


class ReplayError(Exception):
    """Base exception for replay engine errors."""
    pass


class ReplayInputValidationError(ReplayError):
    """Raised when runtime inputs violate the capability artifact schema."""
    pass


class ReplayPolicyViolationError(ReplayError):
    """Raised when a replay operation violates the runtime safety policy."""
    pass


class ReplayTargetResolutionError(ReplayError):
    """Raised when a target cannot be resolved or is ambiguous."""
    pass


class ReplayCheckpointFailedError(ReplayError):
    """Raised when a step postcondition or checkpoint fails."""
    pass


class ReplayTimeoutError(ReplayError):
    """Raised when a wait or step execution times out."""
    pass


class ReplayBusinessOutcomeError(ReplayError):
    """Signal raised when a declared business outcome is encountered during step execution."""
    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


class ReplayEscalationError(ReplayError):
    """Signal raised when an escalation trap is encountered."""
    def __init__(self, code: str, reason: str = ""):
        super().__init__(reason or code)
        self.code = code
        self.reason = reason or code


class ReplayHardFailureError(ReplayError):
    """Signal raised when a hard failure condition (e.g. permission denied) is detected."""
    def __init__(self, category: str, message: str = ""):
        super().__init__(message or category)
        self.category = category
