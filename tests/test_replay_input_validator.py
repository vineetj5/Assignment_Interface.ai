"""Tests for Phase 5 Runtime Input Validator."""

import pytest
from capability.bindings import LOOKUP_BALANCE_INPUTS
from replay.exceptions import ReplayInputValidationError
from replay.input_validator import ReplayInputValidator


def test_input_validator_accepts_valid_inputs():
    validator = ReplayInputValidator()
    inputs = {"member_id": "76821", "account_type": "checking"}
    validated = validator.validate(LOOKUP_BALANCE_INPUTS, inputs)

    assert validated["member_id"] == "76821"
    assert validated["account_type"] == "checking"


def test_input_validator_rejects_missing_required():
    validator = ReplayInputValidator()
    inputs = {"account_type": "savings"}
    with pytest.raises(ReplayInputValidationError, match="member_id"):
        validator.validate(LOOKUP_BALANCE_INPUTS, inputs)


def test_input_validator_rejects_invalid_enum():
    validator = ReplayInputValidator()
    inputs = {"member_id": "76821", "account_type": "crypto"}
    with pytest.raises(ReplayInputValidationError, match="Allowed values"):
        validator.validate(LOOKUP_BALANCE_INPUTS, inputs)


def test_input_validator_rejects_pattern_mismatch():
    validator = ReplayInputValidator()
    inputs = {"member_id": "abc_invalid", "account_type": "savings"}
    with pytest.raises(ReplayInputValidationError, match="required pattern"):
        validator.validate(LOOKUP_BALANCE_INPUTS, inputs)
