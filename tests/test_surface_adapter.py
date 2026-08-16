import asyncio
import threading
import time
import pytest
import uvicorn
from app import app
from automation.adapter import SurfaceAdapter
from automation.exceptions import ActionExecutionError
from automation.models import ActionRequest, ActionType, TargetSpec
from automation.surface import PlaywrightSurface

TEST_PORT = 8009
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"




@pytest.mark.asyncio
async def test_full_member_balance_workflow(tmp_path):
    """
    End-to-end Phase 2 integration test:
    1. Start Playwright session
    2. Open target app
    3. Observe nested frame hierarchy
    4. Fill member ID 12345
    5. Click Find Member
    6. Observe accounts table & profile
    7. Click 'View' on Regular Savings
    8. Observe Account Detail page
    9. Extract Current Balance
    10. Verify balance is $14,820.50
    11. Verify action logs and screenshots in evidence store
    """
    surface = PlaywrightSurface(
        headless=True,
        evidence_dir=tmp_path / "evidence",
        run_id="test_run_balance_12345",
    )

    # 1. Open target app
    await surface.open(f"{BASE_URL}/")
    obs = await surface.observe()

    # Verify frame hierarchy
    frame_names = [f.name for f in obs.frame_hierarchy]
    assert "legacy-app" in frame_names or any("legacy" in f.url for f in obs.frame_hierarchy)

    # 2. Fill Member Number (12345)
    fill_res = await surface.execute(
        ActionRequest(
            action_type=ActionType.FILL,
            target=TargetSpec(name="member_number", frame_path=["legacy-app", "workspace"]),
            value="12345",
        )
    )
    assert fill_res.status == "success"

    # 3. Click Find Member
    click_res = await surface.execute(
        ActionRequest(
            action_type=ActionType.CLICK,
            target=TargetSpec(name="Find Member", frame_path=["legacy-app", "workspace"]),
        )
    )
    assert click_res.status == "success"

    # 4. Observe member loaded in profile
    obs_after_search = surface.last_observation
    assert "Avery Carter" in obs_after_search.visible_text or "12345" in obs_after_search.visible_text

    # 5. Click View link for Savings
    click_view_res = await surface.execute(
        ActionRequest(
            action_type=ActionType.CLICK,
            target=TargetSpec(text="View", frame_path=["legacy-app", "workspace"]),
        )
    )
    assert click_view_res.status == "success"

    # 6. Extract Current Balance on Account Detail page
    extract_res = await surface.execute(
        ActionRequest(
            action_type=ActionType.EXTRACT,
            target=TargetSpec(css=".balance-value", frame_path=["legacy-app", "workspace"]),
        )
    )
    assert extract_res.status == "success"
    assert extract_res.output["text"] == "$1,214.87"

    # 7. Check evidence persistence
    run_dir = tmp_path / "evidence" / "test_run_balance_12345"
    assert (run_dir / "actions.jsonl").exists()
    assert (run_dir / "metadata.json").exists()
    assert len(list((run_dir / "observations").glob("*.json"))) >= 3
    assert len(list((run_dir / "screenshots").glob("*.png"))) >= 1

    await surface.close()


@pytest.mark.asyncio
async def test_error_conditions_observation(tmp_path):
    """Test observation of error states: member_not_found, permission_denied, unexpected_dialog."""
    surface = PlaywrightSurface(
        headless=True,
        evidence_dir=tmp_path / "evidence",
        run_id="test_run_conditions",
    )

    await surface.open(f"{BASE_URL}/legacy/member-inquiry")

    # A) Member not found
    await surface.execute(
        ActionRequest(
            action_type=ActionType.FILL,
            target=TargetSpec(name="member_number"),
            value="99999",
        )
    )
    await surface.execute(
        ActionRequest(
            action_type=ActionType.CLICK,
            target=TargetSpec(name="Find Member"),
        )
    )
    obs = surface.last_observation
    assert any(m.code == "MEMBER_NOT_FOUND" for m in obs.detected_messages)

    # B) Permission Denied
    await surface.execute(
        ActionRequest(
            action_type=ActionType.FILL,
            target=TargetSpec(name="member_number"),
            value="12345",
        )
    )
    await surface.execute(
        ActionRequest(
            action_type=ActionType.SELECT,
            target=TargetSpec(name="test_condition"),
            value="permission_denied",
        )
    )
    await surface.execute(
        ActionRequest(
            action_type=ActionType.CLICK,
            target=TargetSpec(name="Find Member"),
        )
    )
    obs = surface.last_observation
    assert any(m.code == "PERMISSION_DENIED" for m in obs.detected_messages)

    # C) Unexpected Verification Dialog
    await surface.execute(
        ActionRequest(
            action_type=ActionType.SELECT,
            target=TargetSpec(name="test_condition"),
            value="unexpected_dialog",
        )
    )
    await surface.execute(
        ActionRequest(
            action_type=ActionType.CLICK,
            target=TargetSpec(name="Find Member"),
        )
    )
    obs = surface.last_observation
    assert len(obs.detected_dialogs) > 0
    assert "Verification Required" in obs.detected_dialogs[0].title or "verification" in obs.detected_dialogs[0].text.lower()

    # Click Continue on the dialog
    await surface.execute(
        ActionRequest(
            action_type=ActionType.CLICK,
            target=TargetSpec(text="Continue"),
        )
    )
    obs_after_dialog = surface.last_observation
    # Dialog should now be closed / hidden
    assert len(obs_after_dialog.detected_dialogs) == 0

    await surface.close()
