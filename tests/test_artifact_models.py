"""Tests for Phase 4 Capability Artifact Schema data models and JSON serialization."""

import json
from capability.bindings import (
    LOOKUP_BALANCE_ENTRYPOINT,
    LOOKUP_BALANCE_IDENTITY,
    LOOKUP_BALANCE_INPUTS,
    LOOKUP_BALANCE_OUTPUTS,
    LOOKUP_BALANCE_SAFETY,
)
from capability.models import (
    ArtifactActionType,
    ArtifactStatus,
    CapabilityArtifact,
    CapabilityIdentity,
    CapabilityStep,
    CompatibilitySpec,
    ConditionSpec,
    ExtractionSpec,
    ExtractionTransformSpec,
    FrameTarget,
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


def test_artifact_model_instantiation_and_roundtrip():
    step1 = CapabilityStep(
        id="enter_member_id",
        action=ArtifactActionType.FILL,
        target=TargetSpec(
            frame_path=[FrameTarget(name="legacy-app"), FrameTarget(name="workspace")],
            primary=LocatorStrategy(strategy="role_name", role="textbox", name="Member Number"),
        ),
        value=ValueSource(source="input", name="member_id"),
        postconditions=[
            ConditionSpec(
                type="input_value_equals",
                expected=ValueSource(source="input", name="member_id"),
            )
        ],
    )

    step2 = CapabilityStep(
        id="extract_current_balance",
        action=ArtifactActionType.EXTRACT,
        target=TargetSpec(
            primary=LocatorStrategy(strategy="field_by_label", label="Current Balance"),
        ),
        extraction=ExtractionSpec(
            output="current_balance",
            transform=ExtractionTransformSpec(type="parse_currency", default_currency="USD"),
        ),
    )

    artifact = CapabilityArtifact(
        schema_version="1",
        identity=LOOKUP_BALANCE_IDENTITY,
        inputs=LOOKUP_BALANCE_INPUTS,
        outputs=LOOKUP_BALANCE_OUTPUTS,
        entrypoint=LOOKUP_BALANCE_ENTRYPOINT,
        steps=[step1, step2],
        success_condition=ConditionSpec(
            type="all_of",
            conditions=[
                ConditionSpec(type="member_matches_input", input="member_id"),
                ConditionSpec(type="output_present", output="current_balance"),
            ],
        ),
        safety=LOOKUP_BALANCE_SAFETY,
        compatibility=CompatibilitySpec(),
        provenance=ProvenanceSpec(
            created_from="llm_discovery",
            discovery_run_id="discovery_test_001",
            created_at="2026-08-15T19:00:00Z",
            model_provider="groq",
            model="llama-3.3-70b-versatile",
        ),
    )

    # Serialize to JSON
    json_str = artifact.model_dump_json(indent=2, exclude_none=True)
    data = json.loads(json_str)

    assert data["schema_version"] == "1"
    assert data["identity"]["name"] == "lookup_balance"
    assert data["identity"]["version"] == "1.0.0"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["action"] == "fill"
    assert data["steps"][0]["value"]["source"] == "input"

    # Deserialize back into model
    reloaded = CapabilityArtifact.model_validate(data)
    assert reloaded.identity.name == "lookup_balance"
    assert reloaded.steps[1].extraction.output == "current_balance"
    assert reloaded.steps[1].extraction.transform.type == "parse_currency"
