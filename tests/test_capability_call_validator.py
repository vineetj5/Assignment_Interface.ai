"""Tests for Phase 6 CapabilityCallValidator."""

import pytest
from routing.catalog import CapabilityCatalog
from routing.exceptions import RoutingValidationError
from routing.models import RoutingDecision, RoutingStatus
from routing.validator import CapabilityCallValidator


def validator() -> CapabilityCallValidator:
    return CapabilityCallValidator(CapabilityCatalog())


def test_validator_accepts_valid_call():
    decision = RoutingDecision(
        status=RoutingStatus.INVOKE,
        capability="lookup_balance",
        arguments={"member_id": "12345", "account_type": "checking"},
    )

    validated = validator().validate(decision)

    assert validated.status == RoutingStatus.INVOKE
    assert validated.arguments["account_type"] == "checking"


def test_validator_rejects_hallucinated_capability():
    decision = RoutingDecision(
        status=RoutingStatus.INVOKE,
        capability="transfer_funds",
        arguments={"amount": 5000},
    )

    with pytest.raises(RoutingValidationError):
        validator().validate(decision)


def test_validator_rejects_invalid_enum():
    decision = RoutingDecision(
        status=RoutingStatus.INVOKE,
        capability="lookup_balance",
        arguments={"member_id": "12345", "account_type": "credit"},
    )

    with pytest.raises(RoutingValidationError):
        validator().validate(decision)


def test_validator_rejects_extra_argument():
    decision = RoutingDecision(
        status=RoutingStatus.INVOKE,
        capability="lookup_balance",
        arguments={"member_id": "12345", "account_type": "checking", "admin": True},
    )

    with pytest.raises(RoutingValidationError):
        validator().validate(decision)


def test_validator_converts_missing_required_to_clarify():
    decision = RoutingDecision(
        status=RoutingStatus.INVOKE,
        capability="lookup_balance",
        arguments={"member_id": "12345"},
    )

    validated = validator().validate(decision)

    assert validated.status == RoutingStatus.CLARIFY
    assert validated.missing_arguments == ["account_type"]

