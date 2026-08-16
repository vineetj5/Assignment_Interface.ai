"""Tests for Phase 5 Condition Engine."""

from automation.models import Observation, StructuredTable
from capability.models import ConditionSpec, ValueSource
from replay.condition_engine import ConditionEngine


def test_condition_engine_field_equals():
    engine = ConditionEngine()
    obs = Observation(
        observation_id="obs_01",
        timestamp="2026-08-15T20:00:00Z",
        page_url="http://127.0.0.1:8000",
        visible_text="MEMBER PROFILE\nMember Number: 76821\nName: Jane Doe",
    )
    cond = ConditionSpec(
        type="field_equals",
        field={"table": "MEMBER PROFILE"},
        expected=ValueSource(source="input", name="member_id"),
    )

    res = engine.evaluate(cond, runtime_inputs={"member_id": "76821"}, step_outputs={}, observation=obs)
    assert res.matched is True


def test_condition_engine_text_visible():
    engine = ConditionEngine()
    obs = Observation(
        observation_id="obs_02",
        timestamp="2026-08-15T20:00:00Z",
        page_url="http://127.0.0.1:8000",
        visible_text="Member not found in database.",
    )
    cond = ConditionSpec(type="text_visible", pattern="Member not found")
    res = engine.evaluate(cond, runtime_inputs={}, step_outputs={}, observation=obs)
    assert res.matched is True


def test_condition_engine_table_row_missing_false_for_existing_account():
    engine = ConditionEngine()
    obs = Observation(
        observation_id="obs_03",
        timestamp="2026-08-15T20:00:00Z",
        page_url="http://127.0.0.1:8000",
        structured_tables=[
            StructuredTable(
                caption="SHARE / DRAFT ACCOUNTS",
                headers=["Type", "Account", "Balance"],
                rows=[["SAV", "0001", "$5,521.10"], ["DDA", "0002", "$1,214.87"]],
            )
        ],
    )
    cond = ConditionSpec(type="table_row_missing", table="SHARE / DRAFT ACCOUNTS", column="Type")

    res = engine.evaluate(cond, runtime_inputs={"account_type": "checking"}, step_outputs={}, observation=obs)

    assert res.matched is False


def test_condition_engine_table_row_missing_true_for_absent_account():
    engine = ConditionEngine()
    obs = Observation(
        observation_id="obs_04",
        timestamp="2026-08-15T20:00:00Z",
        page_url="http://127.0.0.1:8000",
        structured_tables=[
            StructuredTable(
                caption="SHARE / DRAFT ACCOUNTS",
                headers=["Type", "Account", "Balance"],
                rows=[["SAV", "0001", "$5,521.10"]],
            )
        ],
    )
    cond = ConditionSpec(type="table_row_missing", table="SHARE / DRAFT ACCOUNTS", column="Type")

    res = engine.evaluate(cond, runtime_inputs={"account_type": "checking"}, step_outputs={}, observation=obs)

    assert res.matched is True


def test_condition_engine_unknown_condition_fails_closed():
    engine = ConditionEngine()
    cond = ConditionSpec(type="unknown_condition")

    res = engine.evaluate(cond, runtime_inputs={}, step_outputs={}, observation=None)

    assert res.matched is False
