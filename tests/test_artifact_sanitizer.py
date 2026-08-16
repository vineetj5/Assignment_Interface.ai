"""Tests for Phase 4 Artifact Sanitizer."""

import pytest
from capability.bindings import LOOKUP_BALANCE_SAFETY
from capability.exceptions import ArtifactSanitizationError
from capability.models import (
    ArtifactActionType,
    ArtifactStatus,
    CapabilityArtifact,
    CapabilityIdentity,
    CapabilityStep,
    CompatibilitySpec,
    ConditionSpec,
    EntryPointSpec,
    ExtractionSpec,
    ExtractionTransformSpec,
    InputSpec,
    InputType,
    LocatorStrategy,
    OutputSpec,
    OutputType,
    ProvenanceSpec,
    TargetSpec,
    ValueSource,
)
from capability.sanitizer import ArtifactSanitizer


def build_test_artifact() -> CapabilityArtifact:
    return CapabilityArtifact(
        schema_version="1",
        identity=CapabilityIdentity(
            name="lookup_balance",
            version="1.0.0",
            description="Look up a member balance.",
            status=ArtifactStatus.DRAFT,
        ),
        inputs=[
            InputSpec(name="member_id", type=InputType.STRING, required=True, sensitive=True),
            InputSpec(name="account_type", type=InputType.ENUM, values=["savings", "checking"], required=True),
        ],
        outputs=[
            OutputSpec(name="member_id", type=OutputType.STRING),
            OutputSpec(name="account_type", type=OutputType.ENUM, values=["savings", "checking"]),
            OutputSpec(name="current_balance", type=OutputType.MONEY),
        ],
        entrypoint=EntryPointSpec(url="http://127.0.0.1:8000"),
        steps=[
            CapabilityStep(
                id="enter_member_id",
                action=ArtifactActionType.FILL,
                target=TargetSpec(
                    primary=LocatorStrategy(strategy="role_name", role="textbox", name="Member Number")
                ),
                value=ValueSource(source="input", name="member_id"),
            ),
            CapabilityStep(
                id="extract_current_balance",
                action=ArtifactActionType.EXTRACT,
                target=TargetSpec(
                    primary=LocatorStrategy(strategy="field_by_label", label="Current Balance")
                ),
                extraction=ExtractionSpec(
                    output="current_balance",
                    transform=ExtractionTransformSpec(type="parse_currency"),
                ),
            ),
        ],
        success_condition=ConditionSpec(
            type="all_of",
            conditions=[ConditionSpec(type="output_present", output="current_balance")],
        ),
        safety=LOOKUP_BALANCE_SAFETY,
        compatibility=CompatibilitySpec(),
        provenance=ProvenanceSpec(
            created_from="llm_discovery",
            discovery_run_id="run_123",
            created_at="2026-08-15T19:00:00Z",
        ),
    )


def test_sanitizer_passes_clean_artifact():
    sanitizer = ArtifactSanitizer()
    art = build_test_artifact()
    sanitizer.sanitize(art, known_discovery_values=["13278", "$5,521.10"])


def test_sanitizer_rejects_concrete_member_id_literal():
    sanitizer = ArtifactSanitizer()
    art = build_test_artifact()
    # Leak concrete member id literal into the step description or target name
    art.steps[0].target.primary.name = "Member Number 13278"
    with pytest.raises(ArtifactSanitizationError, match="Concrete discovery literal '13278'"):
        sanitizer.sanitize(art, known_discovery_values=["13278"])


def test_sanitizer_rejects_concrete_currency_pattern():
    sanitizer = ArtifactSanitizer()
    art = build_test_artifact()
    # Leak concrete balance "$5,521.10" into a field
    art.identity.description = "Look up member and return $5,521.10 balance."
    with pytest.raises(ArtifactSanitizationError, match="sensitive concrete pattern"):
        sanitizer.sanitize(art)


def test_sanitizer_rejects_ephemeral_observation_id():
    sanitizer = ArtifactSanitizer()
    art = build_test_artifact()
    art.steps[0].target.primary.name = "e_06"
    with pytest.raises(ArtifactSanitizationError, match="Ephemeral observation IDs"):
        sanitizer.sanitize(art)
