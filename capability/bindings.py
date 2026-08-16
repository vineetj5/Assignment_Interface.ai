"""Predefined capability definitions and bindings for standard banking workflows."""

from __future__ import annotations

from typing import Any, Dict, List
from capability.models import (
    ArtifactStatus,
    CapabilityIdentity,
    EntryPointSpec,
    InputSpec,
    InputType,
    InputValidationSpec,
    OutputSpec,
    OutputType,
    SafetySpec,
)


LOOKUP_BALANCE_IDENTITY = CapabilityIdentity(
    name="lookup_balance",
    version="1.0.0",
    description="Look up a member in the legacy core servicing app and return the current balance for their savings or checking account.",
    status=ArtifactStatus.DRAFT,
)

LOOKUP_BALANCE_INPUTS: List[InputSpec] = [
    InputSpec(
        name="member_id",
        type=InputType.STRING,
        required=True,
        description="Credit union member identifier (numeric digits).",
        validation=InputValidationSpec(pattern=r"^\d+$", min_length=4, max_length=10),
        sensitive=True,
    ),
    InputSpec(
        name="account_type",
        type=InputType.ENUM,
        required=True,
        description="Account type category to inspect.",
        values=["savings", "checking"],
        sensitive=False,
    ),
]

LOOKUP_BALANCE_OUTPUTS: List[OutputSpec] = [
    OutputSpec(
        name="member_id",
        type=OutputType.STRING,
        description="Verified member number.",
    ),
    OutputSpec(
        name="account_type",
        type=OutputType.ENUM,
        values=["savings", "checking"],
        description="Account category.",
    ),
    OutputSpec(
        name="current_balance",
        type=OutputType.MONEY,
        description="Current account balance amount and currency.",
        schema_def={
            "amount": {"type": "decimal"},
            "currency": {"type": "string"},
        },
    ),
]

LOOKUP_BALANCE_ENTRYPOINT = EntryPointSpec(
    url="http://127.0.0.1:8000",
)

def get_lookup_balance_safety() -> SafetySpec:
    return SafetySpec(
        risk_class="read_only",
        allowed_actions=["fill", "click", "extract", "wait", "navigate"],
        allowed_origins=["http://127.0.0.1:8000", "http://127.0.0.1:8009"],
        contains_sensitive_inputs=True,
        persist_input_values=False,
    )


LOOKUP_BALANCE_SAFETY = get_lookup_balance_safety()
