"""Runtime input validator for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

import re
from typing import Any, Dict, List
from capability.models import InputSpec, InputType
from replay.exceptions import ReplayInputValidationError


class ReplayInputValidator:
    """Validates runtime input arguments against the capability artifact contract before Playwright runs."""

    def validate(self, input_specs: List[InputSpec], runtime_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and return sanitized runtime inputs."""
        validated: Dict[str, Any] = {}

        for spec in input_specs:
            val = runtime_inputs.get(spec.name)

            if val is None:
                if spec.required:
                    raise ReplayInputValidationError(
                        f"Missing required runtime input parameter '{spec.name}' for capability invocation."
                    )
                continue

            # Type validations
            if spec.type == InputType.STRING:
                if not isinstance(val, str):
                    val = str(val)
                val = val.strip()
                if not val and spec.required:
                    raise ReplayInputValidationError(
                        f"Input parameter '{spec.name}' cannot be empty."
                    )

                if spec.validation:
                    if spec.validation.pattern:
                        if not re.match(spec.validation.pattern, val):
                            raise ReplayInputValidationError(
                                f"Input parameter '{spec.name}' value '{val}' does not match required pattern '{spec.validation.pattern}'."
                            )
                    if spec.validation.min_length and len(val) < spec.validation.min_length:
                        raise ReplayInputValidationError(
                            f"Input parameter '{spec.name}' length ({len(val)}) is shorter than min_length {spec.validation.min_length}."
                        )
                    if spec.validation.max_length and len(val) > spec.validation.max_length:
                        raise ReplayInputValidationError(
                            f"Input parameter '{spec.name}' length ({len(val)}) is longer than max_length {spec.validation.max_length}."
                        )

            elif spec.type == InputType.ENUM:
                val_str = str(val).strip()
                if spec.values and val_str not in spec.values:
                    raise ReplayInputValidationError(
                        f"Input parameter '{spec.name}' value '{val_str}' is invalid. Allowed values: {spec.values}"
                    )
                val = val_str

            elif spec.type == InputType.NUMBER:
                if not isinstance(val, (int, float)):
                    try:
                        val = float(val)
                    except ValueError:
                        raise ReplayInputValidationError(
                            f"Input parameter '{spec.name}' value '{val}' is not a valid number."
                        )

            elif spec.type == InputType.BOOLEAN:
                if isinstance(val, str):
                    val = val.lower() in ["true", "1", "yes"]
                else:
                    val = bool(val)

            validated[spec.name] = val

        return validated
