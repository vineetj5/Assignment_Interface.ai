"""Runtime value source binder for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
from capability.models import ValueSource
from replay.exceptions import ReplayInputValidationError


class ValueBinder:
    """Binds ValueSource declarations in artifacts to concrete runtime values."""

    def resolve(
        self,
        value_source: Optional[ValueSource],
        runtime_inputs: Dict[str, Any],
        step_outputs: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Resolve a ValueSource to its runtime concrete string or object value."""
        if value_source is None:
            return None

        source_type = value_source.source

        if source_type == "input":
            name = value_source.name
            if not name or name not in runtime_inputs:
                raise ReplayInputValidationError(
                    f"ValueSource references runtime input '{name}', but it was not provided."
                )
            return runtime_inputs[name]

        elif source_type == "input_map":
            input_name = value_source.input
            if not input_name or input_name not in runtime_inputs:
                raise ReplayInputValidationError(
                    f"ValueSource references mapped input '{input_name}', but it was not provided."
                )
            raw_val = str(runtime_inputs[input_name])
            mapping = value_source.mapping or {}
            if raw_val not in mapping:
                raise ReplayInputValidationError(
                    f"Mapped input '{input_name}' value '{raw_val}' not found in artifact mapping keys: {list(mapping.keys())}"
                )
            return mapping[raw_val]

        elif source_type == "literal":
            return value_source.value

        elif source_type == "env":
            env_name = value_source.name or ""
            return os.environ.get(env_name, value_source.value)

        elif source_type == "previous_step":
            outputs = step_outputs or {}
            output_name = value_source.name or ""
            return outputs.get(output_name, value_source.value)

        return value_source.value
