"""Tests for Phase 5 Target Resolver."""

from capability.models import FrameTarget, LocatorStrategy, TargetSpec as ArtifactTargetSpec, ValueSource
from replay.target_resolver import TargetResolver


def test_target_resolver_table_row_action():
    resolver = TargetResolver()
    art_target = ArtifactTargetSpec(
        frame_path=[FrameTarget(name="legacy-app"), FrameTarget(name="workspace")],
        primary=LocatorStrategy(
            strategy="table_row_action",
            table="SHARE / DRAFT ACCOUNTS",
            row_match={
                "column": "Type",
                "value": ValueSource(
                    source="input_map",
                    input="account_type",
                    mapping={"savings": "SAV", "checking": "DDA"},
                ),
            },
            action_control={"role": "link", "name": "View"},
        ),
    )

    # Test checking -> DDA
    surface_target_checking = resolver.resolve(art_target, runtime_inputs={"account_type": "checking"})
    assert surface_target_checking is not None
    assert surface_target_checking.frame_path == ["legacy-app", "workspace"]
    assert "DDA" in surface_target_checking.css
    assert "View" in surface_target_checking.css

    # Test savings -> SAV
    surface_target_savings = resolver.resolve(art_target, runtime_inputs={"account_type": "savings"})
    assert "SAV" in surface_target_savings.css


def test_target_resolver_role_name():
    resolver = TargetResolver()
    art_target = ArtifactTargetSpec(
        frame_path=[FrameTarget(name="legacy-app")],
        primary=LocatorStrategy(strategy="role_name", role="button", name="Find Member"),
    )
    surface_target = resolver.resolve(art_target, runtime_inputs={})
    assert surface_target.role == "button"
    assert surface_target.name == "Find Member"
    assert surface_target.frame_path == ["legacy-app"]
