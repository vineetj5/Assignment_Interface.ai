"""Deterministic chat formatting for Phase 6 replay results."""

from __future__ import annotations

from replay.models import FailureCategory, ReplayResult, ReplayStatus
from routing.models import ChatResponse, ChatResponseStatus


class ResponseFormatter:
    """Formats structured replay results into safe chat responses."""

    def format_replay(self, result: ReplayResult) -> ChatResponse:
        if result.status == ReplayStatus.SUCCESS and result.outputs:
            outputs = result.outputs
            balance = outputs.get("current_balance") or {}
            amount = balance.get("amount")
            account_type = outputs.get("account_type")
            member_id = outputs.get("member_id")
            message = f"Member {member_id}'s current {account_type} balance is ${amount}."
            return ChatResponse(
                status=ChatResponseStatus.SUCCESS,
                message=message,
                capability=result.capability,
                replay_run_id=result.run_id,
                data=outputs,
            )

        if result.status == ReplayStatus.BUSINESS_OUTCOME and result.outcome:
            mapping = {
                "MEMBER_NOT_FOUND": "I couldn't find a member with that ID.",
                "ACCOUNT_NOT_FOUND": "That member doesn't have the requested account type.",
            }
            return ChatResponse(
                status=ChatResponseStatus.BUSINESS_OUTCOME,
                message=mapping.get(result.outcome.code, "The lookup reached a business outcome."),
                capability=result.capability,
                replay_run_id=result.run_id,
                reason_code=result.outcome.code,
            )

        if result.status == ReplayStatus.ESCALATED and result.escalation:
            return ChatResponse(
                status=ChatResponseStatus.ESCALATED,
                message="This lookup requires manual verification before it can continue.",
                capability=result.capability,
                replay_run_id=result.run_id,
                run_id=result.run_id,
                intervention_id=result.intervention_id,
                reason_code=result.escalation.code,
            )

        category = result.failure.category if result.failure else None
        message = "The lookup couldn't be completed."
        if category == FailureCategory.PERMISSION_DENIED:
            message = "The lookup couldn't be completed because access was denied."
        elif category == FailureCategory.SESSION_EXPIRED:
            message = "The lookup couldn't be completed because the legacy session expired."
        elif category == FailureCategory.APPLICATION_ERROR:
            message = "The lookup couldn't be completed because the legacy application returned an error."

        return ChatResponse(
            status=ChatResponseStatus.FAILED,
            message=message,
            capability=result.capability,
            replay_run_id=result.run_id,
            reason_code=category.value if category else None,
        )
