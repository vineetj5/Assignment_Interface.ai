"""Tests for Phase 4 Artifact Validator."""

import pytest
from capability.bindings import (
    LOOKUP_BALANCE_ENTRYPOINT,
    LOOKUP_BALANCE_IDENTITY,
    LOOKUP_BALANCE_INPUTS,
    LOOKUP_BALANCE_OUTPUTS,
    LOOKUP_BALANCE_SAFETY,
)
from capability.exceptions import ArtifactValidationError
from capability.models import (
    ArtifactActionType,
    CapabilityArtifact,
    CapabilityStep,
    CompatibilitySpec,
    ConditionSpec,
    ExtractionSpec,
    ExtractionTransformSpec,
    InputSpec,
    InputType,
    LocatorStrategy,
    OutputSpec,
    OutputType,
    ProvenanceSpec,
    SafetySpec,
    TargetSpec,
    ValueSource,
)
from capability.validator import ArtifactValidator


def build_valid_artifact() -> CapabilityArtifact:
    return CapabilityArtifact(
        schema_version="1",
        identity=LOOKUP_BALANCE_IDENTITY,
        inputs=LOOKUP_BALANCE_INPUTS,
        outputs=LOOKUP_BALANCE_OUTPUTS,
        entrypoint=LOOKUP_BALANCE_ENTRYPOINT,
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


def test_validator_accepts_valid_artifact():
    validator = ArtifactValidator()
    art = build_valid_artifact()
    validator.validate(art)  # Should not raise


def test_validator_rejects_missing_input_reference():
    validator = ArtifactValidator()
    art = build_valid_artifact()
    # Reference an undeclared input 'non_existent_input'
    art.steps[0].value = ValueSource(source="input", name="non_existent_input")
    with pytest.raises(ArtifactValidationError, match="non_existent_input"):
        validator.validate(art)


def test_validator_rejects_missing_output_producer():
    validator = ArtifactValidator()
    art = build_valid_artifact()
    # Add an unproduced output 'interest_rate'
    art.outputs.append(OutputSpec(name="interest_rate", type=OutputType.NUMBER))
    with pytest.raises(ArtifactValidationError, match="interest_rate"):
        validator.validate(art)


def test_validator_rejects_ephemeral_observation_id():
    validator = ArtifactValidator()
    art = build_valid_artifact()
    # Put ephemeral observation ID 'e_06' in target name
    art.steps[0].target.primary.name = "e_06"
    with pytest.raises(ArtifactValidationError, match="temporary observation ID"):
        validator.validate(art)


def test_validator_rejects_forbidden_action():
    validator = ArtifactValidator()
    art = build_valid_artifact()
    # Restrict safety spec allowed actions to exclude 'fill'
    art.safety.allowed_actions = ["click", "extract"]
    with pytest.raises(ArtifactValidationError, match="not permitted by safety spec"):
        validator.validate(art)
