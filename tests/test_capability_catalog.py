"""Tests for Phase 6 CapabilityCatalog."""

from routing.catalog import CapabilityCatalog


def test_catalog_lists_approved_capabilities():
    catalog = CapabilityCatalog()
    caps = catalog.list_capabilities()

    assert any(cap.name == "lookup_balance" for cap in caps)
    lookup = catalog.get("lookup_balance")
    assert lookup is not None
    assert lookup.approved_version == "1.0.0"
    assert {spec.name for spec in lookup.inputs} == {"member_id", "account_type"}


def test_catalog_rejects_unknown_capability():
    catalog = CapabilityCatalog()
    assert catalog.get("wire_transfer") is None

