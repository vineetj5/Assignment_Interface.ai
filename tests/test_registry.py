"""Tests for Phase 4 Capability Registry."""

import pytest
from capability.bindings import (
    LOOKUP_BALANCE_ENTRYPOINT,
    LOOKUP_BALANCE_IDENTITY,
    LOOKUP_BALANCE_INPUTS,
    LOOKUP_BALANCE_OUTPUTS,
    LOOKUP_BALANCE_SAFETY,
)
from capability.exceptions import ArtifactRegistryError
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
    LocatorStrategy,
    ProvenanceSpec,
    TargetSpec,
    ValueSource,
)
from capability.registry import CapabilityRegistry


def build_sample_artifact(version: str = "1.0.0") -> CapabilityArtifact:
    return CapabilityArtifact(
        schema_version="1",
        identity=CapabilityIdentity(
            name="lookup_balance",
            version=version,
            description="Look up balance capability.",
            status=ArtifactStatus.DRAFT,
        ),
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
            discovery_run_id="run_reg_test",
            created_at="2026-08-15T19:00:00Z",
        ),
    )


def test_registry_register_and_lookup(tmp_path):
    reg_file = tmp_path / "registry.json"
    registry = CapabilityRegistry(registry_file=reg_file)

    art = build_sample_artifact("1.0.0")
    entry = registry.register(art, relative_path="lookup_balance/1.0.0.json")

    assert entry.name == "lookup_balance"
    assert entry.latest_version == "1.0.0"
    assert entry.artifact_path == "lookup_balance/1.0.0.json"

    # Reload from file
    retrieved = registry.get("lookup_balance")
    assert retrieved is not None
    assert retrieved.name == "lookup_balance"
    assert retrieved.latest_version == "1.0.0"
    assert len(retrieved.inputs) == 2


def test_registry_set_approved_version(tmp_path):
    reg_file = tmp_path / "registry.json"
    registry = CapabilityRegistry(registry_file=reg_file)

    art = build_sample_artifact("1.0.0")
    registry.register(art)

    registry.set_approved_version("lookup_balance", "1.0.0")
    entry = registry.get("lookup_balance")
    assert entry.approved_version == "1.0.0"

    with pytest.raises(ArtifactRegistryError):
        registry.set_approved_version("unknown_cap", "1.0.0")
