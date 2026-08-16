"""Exceptions for Phase 7 human handoff."""


class HandoffError(Exception):
    """Base handoff exception."""


class InvalidStateTransitionError(HandoffError):
    """Raised when a run lifecycle transition is invalid."""


class ControlOwnershipError(HandoffError):
    """Raised when an actor tries to act without owning control."""


class InterventionNotFoundError(HandoffError):
    """Raised when an intervention cannot be found."""

