from __future__ import annotations


class AgentLoopError(Exception):
    """Base exception for all agent discovery loop errors."""
    pass


class DecisionValidationError(AgentLoopError):
    """Raised when an LLM decision fails schema or semantic validation."""
    pass


class PolicyViolationError(AgentLoopError):
    """Raised when an action violates safety or scope policy."""
    pass


class LLMClientError(AgentLoopError):
    """Raised when the LLM provider fails or returns an unparseable response."""
    pass


class StoppingConditionReached(AgentLoopError):
    """Raised when a loop stopping condition (e.g. max steps, timeout) is reached."""
    pass
