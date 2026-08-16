"""Checkpoint and condition compiler for Phase 4 Capability Artifact Schema.

Generates structured postconditions, explicit wait conditions, member verification
checkpoints, outcome handlers, and the top-level success condition.
"""

from __future__ import annotations

from typing import List
from capability.models import (
    ConditionSpec,
    ExtractionSpec,
    ExtractionTransformSpec,
    OutcomeCategory,
    OutcomeSpec,
    RuntimeConditionSpec,
    ValueSource,
    WaitSpec,
)


class CheckpointCompiler:
    """Builds robust checkpoints, condition handlers, and success assertions."""

    def build_fill_postcondition(self, input_name: str = "member_id") -> List[ConditionSpec]:
        """Postcondition asserting the input field holds the parameter value."""
        return [
            ConditionSpec(
                type="input_value_equals",
                expected=ValueSource(source="input", name=input_name),
            )
        ]

    def build_search_wait(self) -> WaitSpec:
        """Meaningful wait after searching for a member, checking for success or terminal outcomes."""
        return WaitSpec(
            type="any_of",
            conditions=[
                WaitSpec(type="text_visible", value="Member loaded.", timeout_ms=5000),
                WaitSpec(type="text_visible", value="Member not found", timeout_ms=5000),
                WaitSpec(type="text_visible", value="Permission denied", timeout_ms=5000),
            ],
            timeout_ms=5000,
        )

    def build_member_identity_checkpoint(self, input_name: str = "member_id") -> ConditionSpec:
        """Checkpoint asserting that the loaded member profile matches requested member_id."""
        return ConditionSpec(
            type="field_equals",
            field={
                "strategy": "table_field",
                "table": "MEMBER PROFILE",
                "field": "Member Number",
            },
            expected=ValueSource(source="input", name=input_name),
        )

    def build_account_wait(self) -> WaitSpec:
        """Wait for Account Detail page to be visible."""
        return WaitSpec(
            type="text_visible",
            value="Account Detail",
            timeout_ms=5000,
        )

    def build_balance_extraction(self, output_name: str = "current_balance") -> ExtractionSpec:
        """Extraction specification with currency parser transform."""
        return ExtractionSpec(
            output=output_name,
            transform=ExtractionTransformSpec(
                type="parse_currency",
                default_currency="USD",
            ),
        )

    def build_success_condition(
        self,
        member_input: str = "member_id",
        account_input: str = "account_type",
        balance_output: str = "current_balance",
    ) -> ConditionSpec:
        """Top-level success condition requiring member match, account match, and balance output."""
        return ConditionSpec(
            type="all_of",
            conditions=[
                ConditionSpec(type="member_matches_input", input=member_input),
                ConditionSpec(type="account_matches_input", input=account_input),
                ConditionSpec(type="output_present", output=balance_output),
            ],
        )

    def build_default_business_outcomes(self) -> List[OutcomeSpec]:
        """Declared business outcomes (expected non-success domain states)."""
        return [
            OutcomeSpec(
                code="MEMBER_NOT_FOUND",
                category=OutcomeCategory.BUSINESS_OUTCOME,
                detect=ConditionSpec(
                    type="all_of",
                    conditions=[
                        ConditionSpec(type="text_matches", pattern="Member not found"),
                        # Ensure we don't fire on the test condition dropdown option:
                        # "Member loaded." is always shown upon successful search.
                        ConditionSpec(type="not_text", pattern="Member loaded."),
                    ],
                ),
                description="The requested member identifier was not found in the servicing database.",
            ),
            OutcomeSpec(
                code="ACCOUNT_NOT_FOUND",
                category=OutcomeCategory.BUSINESS_OUTCOME,
                detect=ConditionSpec(
                    type="table_row_missing",
                    table="SHARE / DRAFT ACCOUNTS",
                    column="Type",
                ),
                description="The requested account type (savings/checking) does not exist for this member.",
            ),
        ]

    def build_default_runtime_conditions(self) -> List[RuntimeConditionSpec]:
        """Declared runtime error, permission, and escalation conditions."""
        return [
            RuntimeConditionSpec(
                code="PERMISSION_DENIED",
                category=OutcomeCategory.HARD_FAILURE,
                detect=ConditionSpec(
                    type="text_matches",
                    pattern="Permission denied",
                ),
                description="Servicing user does not have permission to view this member profile.",
            ),
            RuntimeConditionSpec(
                code="SESSION_EXPIRED",
                category=OutcomeCategory.HARD_FAILURE,
                detect=ConditionSpec(
                    type="text_matches",
                    pattern="Session expired",
                ),
                description="Legacy session has timed out and requires re-authentication.",
            ),
            RuntimeConditionSpec(
                code="VERIFICATION_REQUIRED",
                category=OutcomeCategory.ESCALATE,
                detect=ConditionSpec(
                    type="dialog_matches",
                    pattern="Verification",
                ),
                description="Step-up verification modal encountered requiring human intervention.",
            ),
            RuntimeConditionSpec(
                code="APPLICATION_ERROR",
                category=OutcomeCategory.HARD_FAILURE,
                detect=ConditionSpec(
                    type="text_matches",
                    pattern="Application error",
                ),
                description="Legacy application returned an unexpected 500/unhandled error page.",
            ),
        ]
