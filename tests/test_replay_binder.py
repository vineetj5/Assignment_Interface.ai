"""Tests for Phase 5 Value Binder."""

import pytest
from capability.models import ValueSource
from replay.binder import ValueBinder
from replay.exceptions import ReplayInputValidationError


def test_binder_resolves_input_reference():
    binder = ValueBinder()
    vs = ValueSource(source="input", name="member_id")
    val = binder.resolve(vs, runtime_inputs={"member_id": "76821"})
    assert val == "76821"


def test_binder_resolves_input_map():
    binder = ValueBinder()
    vs = ValueSource(
        source="input_map",
        input="account_type",
        mapping={"savings": "SAV", "checking": "DDA"},
    )
    val_savings = binder.resolve(vs, runtime_inputs={"account_type": "savings"})
    assert val_savings == "SAV"

    val_checking = binder.resolve(vs, runtime_inputs={"account_type": "checking"})
    assert val_checking == "DDA"


def test_binder_resolves_literal():
    binder = ValueBinder()
    vs = ValueSource(source="literal", value="Find Member")
    val = binder.resolve(vs, runtime_inputs={})
    assert val == "Find Member"


def test_binder_rejects_missing_input():
    binder = ValueBinder()
    vs = ValueSource(source="input", name="missing_var")
    with pytest.raises(ReplayInputValidationError):
        binder.resolve(vs, runtime_inputs={})
