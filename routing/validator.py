"""Validation for Phase 6 routing decisions."""

from __future__ import annotations

import re
from typing import Any, Dict
from capability.models import CapabilityRegistryEntry, InputType
from routing.catalog import CapabilityCatalog
from routing.exceptions import RoutingValidationError
from routing.models import RoutingDecision, RoutingStatus


class CapabilityCallValidator:
    """Fail-closed validator for router output before Phase 5 replay."""

    def __init__(self, catalog: CapabilityCatalog):
        self.catalog = catalog

    def validate(self, decision: RoutingDecision) -> RoutingDecision:
        if decision.status == RoutingStatus.UNSUPPORTED:
            return decision

        if not decision.capability:
            raise RoutingValidationError("Routing decision did not include a capability.")

        cap = self.catalog.get(decision.capability)
        if not cap:
            raise RoutingValidationError(f"Capability '{decision.capability}' is not approved or does not exist.")

        declared = {spec.name: spec for spec in cap.inputs}
        extra = set(decision.arguments) - set(declared)
        if extra:
            raise RoutingValidationError(f"Undeclared argument(s): {', '.join(sorted(extra))}.")

        missing = [spec.name for spec in cap.inputs if spec.required and spec.name not in decision.arguments]
        if missing:
            return RoutingDecision(
                status=RoutingStatus.CLARIFY,
                capability=cap.name,
                arguments=dict(decision.arguments),
                missing_arguments=missing,
                clarification_question=decision.clarification_question or self._question_for_missing(missing, cap),
            )

        normalized_args = self._validate_arguments(cap, decision.arguments)
        return RoutingDecision(
            status=RoutingStatus.INVOKE,
            capability=cap.name,
            arguments=normalized_args,
            missing_arguments=[],
            clarification_question=None,
            reason_code=decision.reason_code,
        )

    def _validate_arguments(self, cap: CapabilityRegistryEntry, arguments: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for spec in cap.inputs:
            if spec.name not in arguments:
                continue
            value = arguments[spec.name]
            if spec.type == InputType.STRING:
                value = str(value).strip()
                if spec.validation:
                    if spec.validation.pattern and not re.match(spec.validation.pattern, value):
                        raise RoutingValidationError(f"Argument '{spec.name}' does not match required pattern.")
                    if spec.validation.min_length and len(value) < spec.validation.min_length:
                        raise RoutingValidationError(f"Argument '{spec.name}' is too short.")
                    if spec.validation.max_length and len(value) > spec.validation.max_length:
                        raise RoutingValidationError(f"Argument '{spec.name}' is too long.")
            elif spec.type == InputType.ENUM:
                value = str(value).strip().lower()
                if spec.values and value not in spec.values:
                    raise RoutingValidationError(f"Argument '{spec.name}' value '{value}' is not allowed.")
            elif spec.type == InputType.NUMBER:
                if not isinstance(value, (int, float)):
                    raise RoutingValidationError(f"Argument '{spec.name}' must be numeric.")
            elif spec.type == InputType.BOOLEAN:
                if not isinstance(value, bool):
                    raise RoutingValidationError(f"Argument '{spec.name}' must be boolean.")
            normalized[spec.name] = value
        return normalized

    def _question_for_missing(self, missing: list[str], cap: CapabilityRegistryEntry) -> str:
        if missing == ["account_type"]:
            spec = next((inp for inp in cap.inputs if inp.name == "account_type"), None)
            if spec and spec.values:
                return f"Would you like the {' or '.join(spec.values)} balance?"
        if missing == ["member_id"]:
            return "What member ID would you like me to look up?"
        return f"Please provide: {', '.join(missing)}."
