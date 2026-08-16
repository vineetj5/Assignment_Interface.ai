from __future__ import annotations

import re
from urllib.parse import urlparse
from agent.exceptions import PolicyViolationError
from agent.models import AgentActionType, AgentDecision, DiscoveryGoal


class PolicyGuard:
    """Enforces safety, navigation scope, and security boundaries on all agent actions."""

    def __init__(self, allowed_hosts: list[str] = None):
        self.allowed_hosts = allowed_hosts or ["127.0.0.1", "localhost", "0.0.0.0"]

    def enforce(self, decision: AgentDecision, goal: DiscoveryGoal) -> None:
        # 1. Navigation Scope Policy
        if decision.action == AgentActionType.NAVIGATE and decision.value:
            parsed = urlparse(decision.value)
            if parsed.hostname and parsed.hostname not in self.allowed_hosts:
                raise PolicyViolationError(
                    f"Policy violation: Navigation to external host '{parsed.hostname}' is prohibited. "
                    f"Allowed hosts: {self.allowed_hosts}"
                )

        # 2. Block Arbitrary Code / Injections in input values
        if decision.value:
            dangerous_patterns = [
                r"<script\b",
                r"javascript:",
                r"document\.cookie",
                r"eval\(",
                r"__proto__",
                r"\|\s*bash",
                r";\s*rm\s+",
            ]
            for pat in dangerous_patterns:
                if re.search(pat, decision.value, re.IGNORECASE):
                    raise PolicyViolationError(
                        f"Policy violation: Value contains disallowed executable syntax or injection pattern: {pat}"
                    )
