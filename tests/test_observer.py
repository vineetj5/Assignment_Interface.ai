import pytest
from automation.models import (
    DetectedDialog,
    DetectedMessage,
    InteractiveElement,
    Observation,
    StructuredTable,
)


def test_observation_models_and_llm_summary():
    obs = Observation(
        observation_id="obs_001",
        page_url="http://127.0.0.1:8000/legacy/member-inquiry",
        page_title="Member Inquiry",
        interactive_elements=[
            InteractiveElement(
                observation_id="e_01",
                tag="input",
                role="textbox",
                name="Member Number",
                label="Member Number",
                value="12345",
                editable=True,
                frame_path=["legacy-app", "workspace"],
            ),
            InteractiveElement(
                observation_id="e_02",
                tag="input",
                role="button",
                name="Find Member",
                frame_path=["legacy-app", "workspace"],
            ),
        ],
        detected_messages=[
            DetectedMessage(
                title="Member Not Found",
                message="No record found for 99999",
                code="MEMBER_NOT_FOUND",
                level="business",
            )
        ],
        detected_dialogs=[
            DetectedDialog(
                title="Verification Required",
                text="Please confirm identity",
                buttons=["Continue", "Cancel"],
                frame_path=["legacy-app", "workspace"],
            )
        ],
        structured_tables=[
            StructuredTable(
                caption="SHARE / DRAFT ACCOUNTS",
                headers=["Type", "Suffix", "Description"],
                rows=[["SAV", "01", "Regular Savings"]],
                frame_path=["legacy-app", "workspace"],
            )
        ],
    )

    summary = obs.to_llm_summary()
    assert "Member Inquiry" in summary
    assert "id=e_01" in summary
    assert "Member Number" in summary
    assert "Find Member" in summary
    assert "[BUSINESS] Member Not Found" in summary
    assert "MEMBER_NOT_FOUND" in summary
    assert "Verification Required" in summary
    assert "SHARE / DRAFT ACCOUNTS" in summary
    assert "Regular Savings" in summary

    # Verify lookup by observation_id
    el = obs.get_element("e_01")
    assert el is not None
    assert el.name == "Member Number"
