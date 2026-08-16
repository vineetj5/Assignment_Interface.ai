"""Condition engine for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from automation.models import Observation
from capability.models import ConditionSpec, ValueSource
from replay.binder import ValueBinder
from replay.models import ConditionResult


class ConditionEngine:
    """Evaluates checkpoints, outcome detectors, and success conditions."""

    def __init__(self, binder: Optional[ValueBinder] = None):
        self.binder = binder or ValueBinder()

    def evaluate(
        self,
        condition: ConditionSpec,
        runtime_inputs: Dict[str, Any],
        step_outputs: Dict[str, Any],
        observation: Optional[Observation] = None,
    ) -> ConditionResult:
        """Evaluate a ConditionSpec against runtime state and observation."""
        ctype = condition.type

        if ctype == "all_of":
            sub_conds = condition.conditions or []
            results = [self.evaluate(sc, runtime_inputs, step_outputs, observation) for sc in sub_conds]
            all_matched = all(r.matched for r in results)
            return ConditionResult(matched=all_matched, details=f"Evaluated all_of ({len(sub_conds)} conditions)")

        elif ctype == "any_of":
            sub_conds = condition.conditions or []
            results = [self.evaluate(sc, runtime_inputs, step_outputs, observation) for sc in sub_conds]
            any_matched = any(r.matched for r in results)
            return ConditionResult(matched=any_matched, details=f"Evaluated any_of ({len(sub_conds)} conditions)")

        elif ctype == "text_visible" or ctype == "text_matches":
            text = observation.visible_text if observation else ""
            pattern = condition.pattern or (str(condition.expected.value) if condition.expected and hasattr(condition.expected, "value") else str(condition.expected or ""))
            if ctype == "text_matches" and observation:
                message_text = "\n".join(
                    f"{m.title}\n{m.message}\n{m.code}" for m in observation.detected_messages
                )
                dialog_text = "\n".join(
                    f"{d.title}\n{d.text}" for d in observation.detected_dialogs
                )
                scoped_text = "\n".join(part for part in [message_text, dialog_text] if part.strip())
                if scoped_text:
                    matched = bool(re.search(pattern, scoped_text, re.IGNORECASE))
                    return ConditionResult(matched=matched, expected=pattern, observed=scoped_text[:100])

            matched = bool(re.search(re.escape(pattern) if ctype == "text_visible" else pattern, text, re.IGNORECASE))
            return ConditionResult(matched=matched, expected=pattern, observed=text[:100])

        elif ctype == "not_text":
            text = observation.visible_text if observation else ""
            pattern = condition.pattern or ""
            matched = not bool(re.search(re.escape(pattern), text, re.IGNORECASE))
            return ConditionResult(matched=matched, expected=f"NOT '{pattern}'")

        elif ctype == "not_of":
            sub_conds = condition.conditions or []
            results = [self.evaluate(sc, runtime_inputs, step_outputs, observation) for sc in sub_conds]
            none_matched = not any(r.matched for r in results)
            return ConditionResult(matched=none_matched, details="Evaluated not_of")

        elif ctype == "dialog_matches":
            dialogs = observation.detected_dialogs if observation else []
            pattern = condition.pattern or ""
            matched = any(re.search(pattern, f"{d.title} {d.text}", re.IGNORECASE) for d in dialogs)
            return ConditionResult(matched=matched, expected=pattern)

        elif ctype == "input_value_equals":
            # Postfill input value check
            expected_vs = condition.expected
            bound_val = self.binder.resolve(expected_vs, runtime_inputs, step_outputs) if isinstance(expected_vs, ValueSource) else expected_vs
            # Observation elements check
            elements = observation.interactive_elements if observation else []
            matched = any(el.value == str(bound_val) for el in elements if el.value)
            # If observation check did not fail explicitly, assume verified by Playwright fill verification
            return ConditionResult(matched=matched, expected=bound_val)

        elif ctype == "field_equals":
            field_spec = condition.field or {}
            table_name = field_spec.get("table", "MEMBER PROFILE")
            expected_vs = condition.expected
            bound_val = self.binder.resolve(expected_vs, runtime_inputs, step_outputs) if isinstance(expected_vs, ValueSource) else expected_vs

            tables = observation.structured_tables if observation else []
            obs_text = observation.visible_text if observation else ""

            matched = str(bound_val) in obs_text
            return ConditionResult(matched=matched, expected=bound_val, observed=table_name)

        elif ctype == "member_matches_input":
            input_name = condition.input or "member_id"
            requested_id = str(runtime_inputs.get(input_name, ""))
            obs_text = observation.visible_text if observation else ""
            matched = requested_id in obs_text if requested_id else True
            return ConditionResult(matched=matched, expected=requested_id)

        elif ctype == "account_matches_input":
            input_name = condition.input or "account_type"
            requested_acc = str(runtime_inputs.get(input_name, "")).lower()
            obs_text = observation.visible_text if observation else ""
            keyword = "savings" if "saving" in requested_acc else "checking"
            matched = keyword in obs_text.lower() or "account detail" in obs_text.lower()
            return ConditionResult(matched=matched, expected=requested_acc)

        elif ctype == "output_present":
            output_name = condition.output or ""
            matched = output_name in step_outputs and step_outputs[output_name] is not None
            return ConditionResult(matched=matched, expected=output_name, observed=list(step_outputs.keys()))

        elif ctype in {"table_row_exists", "table_row_missing"}:
            table_name = condition.table or ""
            column_name = condition.column or ""
            expected_vs = condition.expected
            expected_val = self.binder.resolve(expected_vs, runtime_inputs, step_outputs) if isinstance(expected_vs, ValueSource) else expected_vs

            if expected_val is None and column_name.lower() == "type":
                account_type = str(runtime_inputs.get("account_type", "")).lower()
                expected_val = {"savings": "SAV", "checking": "DDA"}.get(account_type, account_type)

            table_present, row_exists = self._table_row_state(
                observation=observation,
                table_name=table_name,
                column_name=column_name,
                expected_value=str(expected_val) if expected_val is not None else None,
            )
            matched = row_exists if ctype == "table_row_exists" else table_present and not row_exists
            return ConditionResult(
                matched=matched,
                expected={
                    "table": table_name,
                    "column": column_name,
                    "value": expected_val,
                },
                observed="row_exists" if row_exists else ("row_missing" if table_present else "table_missing"),
            )

        return ConditionResult(matched=False, details=f"Unsupported condition type: {ctype}")

    def _table_row_state(
        self,
        observation: Optional[Observation],
        table_name: str,
        column_name: str,
        expected_value: Optional[str],
    ) -> tuple[bool, bool]:
        """Return whether the declared table exists and contains a matching row."""
        if not observation:
            return False, False

        normalized_table = table_name.strip().lower()
        normalized_column = column_name.strip().lower()
        normalized_expected = expected_value.strip().lower() if expected_value else None
        table_present = False

        for table in observation.structured_tables:
            if normalized_table and normalized_table not in table.caption.strip().lower():
                continue
            table_present = True

            headers = [h.strip().lower() for h in table.headers]
            column_index = headers.index(normalized_column) if normalized_column in headers else None

            for row in table.rows:
                cells = [str(cell).strip() for cell in row]
                if column_index is not None and column_index < len(cells):
                    candidate_values = [cells[column_index]]
                else:
                    candidate_values = cells

                if normalized_expected is None:
                    return table_present, True
                if any(normalized_expected == value.lower() for value in candidate_values):
                    return table_present, True

        return table_present, False
