"""Tests for Phase 4 Artifact Repository."""

import pytest
from capability.bindings import (
    LOOKUP_BALANCE_ENTRYPOINT,
    LOOKUP_BALANCE_IDENTITY,
    LOOKUP_BALANCE_INPUTS,
    LOOKUP_BALANCE_OUTPUTS,
    LOOKUP_BALANCE_SAFETY,
)
from capability.exceptions import ArtifactNotFoundError
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
from capability.repository import ArtifactRepository


def build_sample_artifact(version: str = "1.0.0", status: ArtifactStatus = ArtifactStatus.DRAFT) -> CapabilityArtifact:
    return CapabilityArtifact(
        schema_version="1",
        identity=CapabilityIdentity(
            name="lookup_balance",
            version=version,
            description="Look up balance capability.",
            status=status,
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
            discovery_run_id="run_repo_test",
            created_at="2026-08-15T19:00:00Z",
        ),
    )


def test_repository_save_and_load(tmp_path):
    repo = ArtifactRepository(root_dir=tmp_path)
    art_v1 = build_sample_artifact("1.0.0")

    saved_path = repo.save(art_v1)
    assert saved_path.exists()
    assert saved_path.name == "1.0.0.json"
    assert saved_path.parent.name == "lookup_balance"

    loaded = repo.load("lookup_balance", "1.0.0")
    assert loaded.identity.name == "lookup_balance"
    assert loaded.identity.version == "1.0.0"


def test_repository_version_management(tmp_path):
    repo = ArtifactRepository(root_dir=tmp_path)
    art_v1 = build_sample_artifact("1.0.0", ArtifactStatus.APPROVED)
    art_v2 = build_sample_artifact("1.1.0", ArtifactStatus.DRAFT)

    repo.save(art_v1)
    repo.save(art_v2)

    versions = repo.list_versions("lookup_balance")
    assert versions == ["1.0.0", "1.1.0"]

    latest = repo.get_latest("lookup_balance")
    assert latest.identity.version == "1.1.0"

    approved = repo.get_approved("lookup_balance")
    assert approved is not None
    assert approved.identity.version == "1.0.0"


def test_repository_not_found(tmp_path):
    repo = ArtifactRepository(root_dir=tmp_path)
    with pytest.raises(ArtifactNotFoundError):
        repo.load("non_existent", "1.0.0")
