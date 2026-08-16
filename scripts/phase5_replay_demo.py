#!/usr/bin/env python3
"""
Phase 5 Demo Script — Deterministic Capability Replay
Executes an approved capability artifact without Groq or any LLM UI decisions.
"""

import argparse
import asyncio
import json
import os
import sys
import threading
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from app import app
from capability.repository import ArtifactRepository
from replay.engine import ReplayEngine
from replay.models import ReplayStatus


def ensure_server_running(host: str = "127.0.0.1", port: int = 8000) -> bool:
    """Ensure mock banking server is running on target port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex((host, port))
        if result == 0:
            return False  # Server already running

    print(f"  Starting local test server on http://{host}:{port}...")
    config = uvicorn.Config(app, host=host, port=port, log_level="error", loop="asyncio")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(0.8)
    return True


async def run_demo(
    capability: str,
    version: str,
    member_id: str,
    account_type: str,
    headful: bool,
    evidence_dir: str = None,
):
    project_root = Path(__file__).resolve().parent.parent
    ensure_server_running(port=8000)

    print("========================================================")
    print(" PHASE 5: DETERMINISTIC CAPABILITY REPLAY")
    print("========================================================")
    print(f"\nCapability:\n  {capability}")
    print(f"\nVersion:\n  {version}")
    print(f"\nLLM Decision Calls:\n  DISABLED (0 API calls)")
    print(f"\nRuntime Inputs:\n  member_id    = [REDACTED]\n  account_type = {account_type}")
    print(f"\nMode:\n  {'Headful (watch live)' if headful else 'Headless'}\n")
    print("Starting deterministic replay engine...\n")

    repo = ArtifactRepository(root_dir=project_root / "artifacts")
    try:
        artifact = repo.load(capability, version)
    except Exception as e:
        print(f"❌ Error loading artifact: {e}")
        sys.exit(1)

    ev_root = Path(evidence_dir) if evidence_dir else (project_root / "evidence")
    engine = ReplayEngine(repository=repo, evidence_dir=ev_root)

    runtime_inputs = {
        "member_id": member_id,
        "account_type": account_type,
    }

    result = await engine.execute(
        artifact=artifact,
        inputs=runtime_inputs,
        headful=headful,
    )

    print("============================================================")
    print("  REPLAY EXECUTION COMPLETED")
    print("============================================================")
    print(f"  Status:          {result.status.value.upper()}")
    print(f"  Total Steps:     {result.steps_completed}")
    print(f"  Duration:        {result.duration_seconds}s")

    if result.status == ReplayStatus.SUCCESS:
        print(f"  Extracted Outputs:\n    {json.dumps(result.outputs, indent=4)}")
    elif result.status == ReplayStatus.BUSINESS_OUTCOME:
        print(f"  Business Outcome: {result.outcome.code} (Step: {result.outcome.step_id})")
    elif result.status == ReplayStatus.ESCALATED:
        print(f"  Escalation:       {result.escalation.code} - {result.escalation.reason}")
    else:
        print(f"  Failure Category: {result.failure.category.value} (Step: {result.failure.step_id})")
        print(f"  Failure Message:  {result.failure.message}")

    if result.evidence_dir:
        print(f"\n  Evidence & Replay Logs:")
        print(f"    - Trace log:   {result.evidence_dir}/replay_trace.jsonl")
        print(f"    - Final JSON:  {result.evidence_dir}/result.json")
    print("============================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Phase 5: Deterministic Capability Replay Demo")
    parser.add_argument("--capability", type=str, default="lookup_balance", help="Capability name (default: lookup_balance)")
    parser.add_argument("--version", type=str, default="1.0.0", help="Capability version (default: 1.0.0)")
    parser.add_argument("--member", type=str, default="76821", help="Runtime member ID (default: 76821)")
    parser.add_argument("--account-type", type=str, default="checking", help="Runtime account type: savings or checking (default: checking)")
    parser.add_argument("--headful", action="store_true", help="Watch browser actions live")
    parser.add_argument("--evidence-dir", type=str, default=None, help="Evidence directory root")
    args = parser.parse_args()

    asyncio.run(run_demo(
        capability=args.capability,
        version=args.version,
        member_id=args.member,
        account_type=args.account_type,
        headful=args.headful,
        evidence_dir=args.evidence_dir,
    ))


if __name__ == "__main__":
    main()
