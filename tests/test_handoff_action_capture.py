"""Tests for Phase 7 human action capture."""

from handoff.action_capture import HumanActionCapture


def test_action_capture_records_operator_action():
    capture = HumanActionCapture()
    capture.record("run_1", "op1", "note", {"value": "[REDACTED]"})

    assert capture.records[0]["run_id"] == "run_1"
    assert capture.records[0]["operator_id"] == "op1"
    assert capture.records[0]["details"]["value"] == "[REDACTED]"

