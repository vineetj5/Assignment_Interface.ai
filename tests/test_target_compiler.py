"""Tests for Phase 4 Target Compiler."""

from capability.models import ValueSource
from capability.target_compiler import TargetCompiler


def test_compile_member_input_target():
    compiler = TargetCompiler()
    resolved = {
        "observation_id": "e_06",
        "role": "textbox",
        "name": "Member Number",
        "tag": "input",
        "attributes": {"name": "member_number", "id": "f_member"},
        "frame_path": ["legacy-app", "workspace"],
    }

    target = compiler.compile_target(resolved, action="fill", step_index=1)
    assert target is not None
    assert len(target.frame_path) == 2
    assert target.frame_path[0].name == "legacy-app"
    assert target.frame_path[1].name == "workspace"
    assert target.primary.strategy == "role_name"
    assert target.primary.role == "textbox"
    assert target.primary.name == "Member Number"
    # Verify no ephemeral observation IDs in fallbacks
    for fb in target.fallbacks:
        assert fb.name != "e_06"


def test_compile_account_view_link_target():
    compiler = TargetCompiler()
    resolved = {
        "observation_id": "e_09",
        "role": "link",
        "name": "View",
        "tag": "a",
        "frame_path": ["legacy-app", "workspace"],
    }
    account_vs = ValueSource(
        source="input_map",
        input="account_type",
        mapping={"savings": "SAV", "checking": "DDA"},
    )

    target = compiler.compile_target(resolved, action="click", step_index=3, account_type_value_source=account_vs)
    assert target is not None
    assert target.primary.strategy == "table_row_action"
    assert target.primary.table == "SHARE / DRAFT ACCOUNTS"
    assert target.primary.row_match["column"] == "Type"
    assert target.primary.row_match["value"]["source"] == "input_map"
    assert target.primary.action_control["role"] == "link"


def test_compile_balance_extract_target():
    compiler = TargetCompiler()
    resolved = {
        "observation_id": "e_06",
        "role": "",
        "name": "Current Balance",
        "tag": "span",
        "attributes": {"class": "balance-value"},
        "frame_path": ["legacy-app", "workspace"],
    }

    target = compiler.compile_target(resolved, action="extract", step_index=4)
    assert target is not None
    assert target.primary.strategy == "field_by_label"
    assert target.primary.label == "Current Balance"
