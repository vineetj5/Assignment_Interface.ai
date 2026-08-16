"""Tests for Phase 5 Runtime Safety Policy."""

import pytest
from capability.bindings import (
    LOOKUP_BALANCE_ENTRYPOINT,
    LOOKUP_BALANCE_IDENTITY,
    LOOKUP_BALANCE_INPUTS,
    LOOKUP_BALANCE_OUTPUTS,
    get_lookup_balance_safety,
)
from capability.models import (
    ArtifactActionType,
    ArtifactStatus,
    CapabilityArtifact,
    CapabilityStep,
    CompatibilitySpec,
    ConditionSpec,
    LocatorStrategy,
    ProvenanceSpec,
    TargetSpec,
)
from replay.exceptions import ReplayPolicyViolationError
from replay.runtime_policy import ReplayRuntimePolicy


def build_policy_test_artifact() -> CapabilityArtifact:
    identity = LOOKUP_BALANCE_IDENTITY.model_copy(update={"status": ArtifactStatus.APPROVED})
    return CapabilityArtifact(
        schema_version="1",
        identity=identity,
        inputs=LOOKUP_BALANCE_INPUTS,
        outputs=LOOKUP_BALANCE_OUTPUTS,
        entrypoint=LOOKUP_BALANCE_ENTRYPOINT,
        steps=[
            CapabilityStep(
                id="search_member",
                action=ArtifactActionType.CLICK,
                target=TargetSpec(primary=LocatorStrategy(strategy="role_name", role="button", name="Find Member")),
            )
        ],
        success_condition=ConditionSpec(type="all_of", conditions=[]),
        safety=get_lookup_balance_safety(),
        compatibility=CompatibilitySpec(),
        provenance=ProvenanceSpec(
            created_from="llm_discovery",
            discovery_run_id="run_pol",
            created_at="2026-08-15T19:00:00Z",
        ),
    )


def test_policy_allows_valid_origin():
    policy = ReplayRuntimePolicy()
    policy.validate_origin("http://127.0.0.1:8000/legacy", allowed_origins=["http://127.0.0.1:8000"])


def test_policy_blocks_external_origin():
    policy = ReplayRuntimePolicy()
    with pytest.raises(ReplayPolicyViolationError, match="violates allowed origins"):
        policy.validate_origin("https://evil-site.com", allowed_origins=["http://127.0.0.1:8000"])


def test_policy_blocks_forbidden_action_type():
    policy = ReplayRuntimePolicy()
    art = build_policy_test_artifact()
    art.safety.allowed_actions = ["extract"]  # exclude 'click'
    with pytest.raises(ReplayPolicyViolationError, match="not in allowed actions"):
        policy.validate_artifact(art)


def test_policy_blocks_unapproved_artifact():
    policy = ReplayRuntimePolicy()
    art = build_policy_test_artifact()
    art.identity.status = ArtifactStatus.DRAFT
    with pytest.raises(ReplayPolicyViolationError, match="not approved"):
        policy.validate_artifact(art)


def test_policy_blocks_unsupported_schema_version():
    policy = ReplayRuntimePolicy()
    art = build_policy_test_artifact()
    art.schema_version = "999"
    with pytest.raises(ReplayPolicyViolationError, match="Unsupported artifact schema_version"):
        policy.validate_artifact(art)
