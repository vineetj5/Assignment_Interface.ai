import pytest
from agent.exceptions import PolicyViolationError
from agent.models import AgentActionType, AgentDecision, DiscoveryGoal
from agent.policy import PolicyGuard


def test_policy_allows_local_navigation():
    policy = PolicyGuard(allowed_hosts=["127.0.0.1", "localhost"])
    goal = DiscoveryGoal(goal="Search")

    valid_nav = AgentDecision(
        action=AgentActionType.NAVIGATE,
        value="http://127.0.0.1:8000/legacy",
        reasoning_summary="Open legacy shell",
    )
    policy.enforce(valid_nav, goal)


def test_policy_blocks_external_navigation():
    policy = PolicyGuard(allowed_hosts=["127.0.0.1"])
    goal = DiscoveryGoal(goal="Search")

    external_nav = AgentDecision(
        action=AgentActionType.NAVIGATE,
        value="https://evil.com/phish",
        reasoning_summary="Open external site",
    )
    with pytest.raises(PolicyViolationError):
        policy.enforce(external_nav, goal)


def test_policy_blocks_injection_values():
    policy = PolicyGuard()
    goal = DiscoveryGoal(goal="Search")

    xss_fill = AgentDecision(
        action=AgentActionType.FILL,
        target_id="e_06",
        value="<script>alert(1)</script>",
        reasoning_summary="Enter XSS",
    )
    with pytest.raises(PolicyViolationError):
        policy.enforce(xss_fill, goal)
