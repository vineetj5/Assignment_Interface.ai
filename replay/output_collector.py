"""Output collector and transform engine for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Dict, List, Optional
from capability.models import ExtractionSpec, OutputSpec


class OutputCollector:
    """Collects and normalizes extracted UI outputs into structured dictionary objects."""

    def transform_value(self, raw_value: Any, extraction_spec: Optional[ExtractionSpec]) -> Any:
        """Apply transformation rules (e.g. parse_currency) to raw extracted values."""
        if raw_value is None:
            return None

        val_str = str(raw_value).strip()
        if not extraction_spec or not extraction_spec.transform:
            return val_str

        trans_type = extraction_spec.transform.type

        if trans_type == "parse_currency":
            # Extract digits, commas, decimals from strings like '$8,241.32'
            clean_str = re.sub(r"[^\d.]", "", val_str)
            currency = extraction_spec.transform.default_currency or "USD"
            try:
                dec = Decimal(clean_str)
                return {
                    "amount": f"{dec:.2f}",
                    "currency": currency,
                }
            except Exception:
                return {
                    "amount": clean_str,
                    "currency": currency,
                }

        elif trans_type == "trim":
            return val_str

        elif trans_type == "to_lower":
            return val_str.lower()

        elif trans_type == "regex" and extraction_spec.transform.regex_pattern:
            m = re.search(extraction_spec.transform.regex_pattern, val_str)
            return m.group(1) if m and m.groups() else (m.group(0) if m else val_str)

        return val_str

    def finalize_outputs(
        self,
        output_specs: List[OutputSpec],
        runtime_inputs: Dict[str, Any],
        extracted_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assemble final outputs dict combining inputs pass-through and extracted variables."""
        final_outputs: Dict[str, Any] = {}

        for spec in output_specs:
            name = spec.name
            if name in extracted_outputs:
                final_outputs[name] = extracted_outputs[name]
            elif name in runtime_inputs:
                final_outputs[name] = runtime_inputs[name]

        return final_outputs
