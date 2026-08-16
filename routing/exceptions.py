"""Exceptions for Phase 6 natural-language capability routing."""


class RoutingError(Exception):
    """Base class for routing errors."""


class RouterClientError(RoutingError):
    """Raised when the routing model/client fails."""


class RoutingValidationError(RoutingError):
    """Raised when a routing decision violates the capability contract."""

