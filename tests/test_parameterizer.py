"""Tests for Phase 4 Parameterizer."""

from capability.bindings import LOOKUP_BALANCE_INPUTS
from capability.models import ValueSource
from capability.parameterizer import Parameterizer


def test_parameterize_member_id_value():
    parameterizer = Parameterizer(LOOKUP_BALANCE_INPUTS)

    # By target name matching "Member Number"
    vs1 = parameterizer.parameterize_fill_value(
        step_action="fill",
        target_name="Member Number",
        concrete_value="13278",
    )
    assert vs1 is not None
    assert vs1.source == "input"
    assert vs1.name == "member_id"

    # By numeric value length
    vs2 = parameterizer.parameterize_fill_value(
        step_action="fill",
        target_name="Search",
        concrete_value="99999",
    )
    assert vs2.source == "input"
    assert vs2.name == "member_id"


def test_parameterize_account_mapping():
    parameterizer = Parameterizer(LOOKUP_BALANCE_INPUTS)
    vs = parameterizer.parameterize_account_mapping("account_type")

    assert vs.source == "input_map"
    assert vs.input == "account_type"
    assert vs.mapping["savings"] == "SAV"
    assert vs.mapping["checking"] == "DDA"
