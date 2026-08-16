"""Parameterizer for Phase 4 Capability Artifact Schema.

Replaces concrete runtime literals (e.g. member IDs, account types) with typed
ValueSource references (e.g. source="input", name="member_id" or source="input_map").
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from capability.models import InputSpec, ValueSource


class Parameterizer:
    """Replaces concrete discovery run values with typed input and mapping references."""

    def __init__(self, inputs: List[InputSpec]):
        self.inputs = {inp.name: inp for inp in inputs}

    def parameterize_fill_value(
        self,
        step_action: str,
        target_name: Optional[str],
        concrete_value: Optional[str],
    ) -> Optional[ValueSource]:
        """Convert a concrete filled value to an InputReference."""
        if concrete_value is None:
            return None

        # Member number input field
        if target_name and ("member" in target_name.lower() or "number" in target_name.lower()):
            if "member_id" in self.inputs:
                return ValueSource(source="input", name="member_id")

        # Generic numeric string matching member_id pattern
        if concrete_value.isdigit() and len(concrete_value) >= 5 and "member_id" in self.inputs:
            return ValueSource(source="input", name="member_id")

        # Fallback to literal if no parameter mapping matches
        return ValueSource(source="literal", value=concrete_value)

    def parameterize_account_mapping(
        self,
        input_name: str = "account_type",
        mapping: Optional[Dict[str, str]] = None,
    ) -> ValueSource:
        """Create an input_map ValueSource for account selection (savings -> SAV, checking -> DDA)."""
        mapping = mapping or {
            "savings": "SAV",
            "checking": "DDA",
        }
        return ValueSource(
            source="input_map",
            input=input_name,
            mapping=mapping,
        )
