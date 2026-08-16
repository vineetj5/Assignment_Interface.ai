"""Tests for Phase 5 Output Collector."""

from capability.bindings import LOOKUP_BALANCE_OUTPUTS
from capability.models import ExtractionSpec, ExtractionTransformSpec
from replay.output_collector import OutputCollector


def test_parse_currency_transform():
    collector = OutputCollector()
    spec = ExtractionSpec(
        output="current_balance",
        transform=ExtractionTransformSpec(type="parse_currency", default_currency="USD"),
    )

    transformed = collector.transform_value("$8,241.32", spec)
    assert isinstance(transformed, dict)
    assert transformed["amount"] == "8241.32"
    assert transformed["currency"] == "USD"


def test_finalize_outputs():
    collector = OutputCollector()
    runtime_inputs = {"member_id": "76821", "account_type": "checking"}
    extracted = {"current_balance": {"amount": "8241.32", "currency": "USD"}}

    final_outputs = collector.finalize_outputs(LOOKUP_BALANCE_OUTPUTS, runtime_inputs, extracted)
    assert final_outputs["member_id"] == "76821"
    assert final_outputs["account_type"] == "checking"
    assert final_outputs["current_balance"]["amount"] == "8241.32"
