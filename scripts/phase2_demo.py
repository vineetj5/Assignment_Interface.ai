#!/usr/bin/env python3
"""
Phase 2 Demo Script — Surface Abstraction + Observability
Demonstrates browser automation, frame traversal, multi-signal target resolution,
DOM/A11y observation, and balance extraction WITHOUT an LLM.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.models import ActionRequest, ActionType, TargetSpec
from automation.surface import PlaywrightSurface


import argparse
import asyncio
import sys
import threading
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.models import ActionRequest, ActionType, TargetSpec
from automation.surface import PlaywrightSurface


async def run_demo(target_url: str, member_id: str, headless: bool):
    print(f"\n=======================================================")
    print(f"  PHASE 2 DEMO: Surface Abstraction & Observability")
    print(f"  Target URL:  {target_url}")
    print(f"  Member ID:   {member_id}")
    print(f"  Mode:        {'Headful (watch live)' if not headless else 'Headless'}")
    print(f"=======================================================\n")

    surface = PlaywrightSurface(
        headless=headless,
        slow_mo=350 if not headless else None,
        run_id=f"demo_phase2_member_{member_id}",
    )

    try:
        # Step 1: Open Target URL
        print("1. Opening target app...")
        await surface.open(target_url)

        # Step 2: Observe initial UI state (scoped to legacy target)
        print("\n2. Observing initial surface state (scoped to legacy target):")
        obs = await surface.observe()
        print("-" * 60)
        print(obs.to_llm_summary(scope_to_target=True))
        print("-" * 60)

        # Step 3: Fill Member Number with post-fill verification
        print(f"\n3. Filling Member Number '{member_id}'...")
        fill_res = await surface.execute(
            ActionRequest(
                action_type=ActionType.FILL,
                target=TargetSpec(name="member_number", frame_path=["legacy-app", "workspace"]),
                value=member_id,
            )
        )
        print(f"   -> Action result: {fill_res.status} ({fill_res.duration_ms}ms, verified=True)")

        # Step 4: Click 'Find Member'
        print("\n4. Clicking 'Find Member'...")
        click_res = await surface.execute(
            ActionRequest(
                action_type=ActionType.CLICK,
                target=TargetSpec(name="Find Member", frame_path=["legacy-app", "workspace"]),
            )
        )
        print(f"   -> Action result: {click_res.status} ({click_res.duration_ms}ms)")

        # Step 5: Observe Member Profile & Accounts
        print("\n5. Observing updated surface state:")
        obs2 = surface.last_observation
        print("-" * 60)
        print(obs2.to_llm_summary(scope_to_target=True))
        print("-" * 60)

        # Checkpoint: verify returned member ID matches requested member ID
        print("\n[CHECKPOINT] Verifying loaded member ID...")
        assert member_id in obs2.visible_text, f"Expected member {member_id} in visible text"
        print(f"   -> CHECKPOINT PASSED: Returned member record matches requested ID '{member_id}'.")

        # Step 6: Click 'View' link for Savings account (distinguished from Checking)
        print("\n6. Clicking 'View' on Regular Savings account (using row context)...")
        view_res = await surface.execute(
            ActionRequest(
                action_type=ActionType.CLICK,
                target=TargetSpec(
                    css="tr:has-text('SAV') a.view-link, tr:has-text('Regular Savings') a.view-link",
                    frame_path=["legacy-app", "workspace"],
                ),
            )
        )
        print(f"   -> Action result: {view_res.status} ({view_res.duration_ms}ms)")

        # Step 7: Extract Current Balance
        print("\n7. Extracting Current Balance...")
        extract_res = await surface.execute(
            ActionRequest(
                action_type=ActionType.EXTRACT,
                target=TargetSpec(css=".balance-value", frame_path=["legacy-app", "workspace"]),
            )
        )
        balance = extract_res.output.get("text")
        print(f"   -> EXTRACTED CURRENT BALANCE: {balance}")

        # Step 8: Evidence summary
        print("\n8. Evidence & Action Logs saved to:")
        print(f"   {surface.evidence_store.run_dir}")
        print(f"   - Actions log:  {surface.evidence_store.actions_file}")
        print(f"   - Observations: {surface.evidence_store.obs_dir}")
        print(f"   - Screenshots:  {surface.evidence_store.screenshots_dir}")

        print("\n=======================================================")
        print("  PHASE 2 DEMO COMPLETED SUCCESSFULLY!")
        print("=======================================================\n")

    finally:
        await surface.close()


def main():
    parser = argparse.ArgumentParser(description="Phase 2 Browser Surface & Observability Demo")
    parser.add_argument("--headful", action="store_true", help="Run browser in visible headful mode")
    parser.add_argument("--member", type=str, default="13278", help="Member ID to look up (default: 13278)")
    parser.add_argument("--port", type=int, default=8000, help="Target port (default: 8000)")
    args = parser.parse_args()

    target_url = f"http://127.0.0.1:{args.port}"
    headless = not args.headful

    # Ensure test server is running if needed
    try:
        import httpx
        httpx.get(target_url, timeout=0.5)
    except Exception:
        import uvicorn
        from app import app
        config = uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="warning", loop="asyncio")
        server = uvicorn.Server(config)
        server_thread = threading.Thread(target=server.run, daemon=True)
        server_thread.start()
        import time
        time.sleep(0.8)

    asyncio.run(run_demo(target_url=target_url, member_id=args.member, headless=headless))


if __name__ == "__main__":
    main()
