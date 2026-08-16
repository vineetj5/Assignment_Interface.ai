#!/usr/bin/env python3
"""
Phase 3 Demo Script — LLM-Driven Autonomous Discovery Loop
Demonstrates natural-language goal interpretation, observation -> decision -> validation -> action cycle
using Groq LLM (or MockLLM fallback), structured traces, and evidence persistence.
"""

import argparse
import asyncio
import os
import sys
import threading
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env automatically if present (provides GROQ_API_KEY, GROQ_MODEL, TARGET_URL)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
        print(f"  Loaded env from {_env_path}")
except ImportError:
    pass  # python-dotenv not installed, rely on shell environment

from agent.config import AgentSettings
from agent.llm_client import GroqLLMClient, MockLLMClient
from agent.loop import run_discovery
from agent.models import DiscoveryGoal
from agent.recorder import DiscoveryRecorder
from agent.results import DiscoveryRunStatus
from automation.surface import PlaywrightSurface


async def run_demo(
    goal_text: str,
    target_url: str,
    headless: bool,
    use_mock: bool,
    model_name: str,
    max_steps: int,
):
    print("\n=======================================================")
    print("  PHASE 3 DEMO: LLM-Driven Discovery Agent")
    print(f"  Target URL:  {target_url}")
    print(f"  Goal:        {goal_text}")
    print(f"  Engine:      {'MockLLMClient (Simulated)' if use_mock else f'GroqLLMClient ({model_name})'}")
    print(f"  Mode:        {'Headful (watch live)' if not headless else 'Headless'}")
    print("=======================================================\n")

    # 1. Initialize LLM Client
    if use_mock:
        llm = MockLLMClient(rule_based=True)
    else:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            print("⚠️ GROQ_API_KEY not found in environment. Falling back to MockLLMClient.")
            print("   (To use real Groq models, set GROQ_API_KEY in your .env file)\n")
            llm = MockLLMClient(rule_based=True)
        else:
            llm = GroqLLMClient(api_key=api_key, model=model_name)

    # 2. Setup SurfaceAdapter and DiscoveryRecorder
    run_id = f"demo_phase3_{int(time.time())}"
    evidence_dir = Path.cwd() / "evidence"

    surface = PlaywrightSurface(
        headless=headless,
        slow_mo=350 if not headless else None,
        run_id=run_id,
        evidence_dir=evidence_dir,
    )
    recorder = DiscoveryRecorder(
        evidence_dir=evidence_dir,
        run_id=run_id,
    )

    goal = DiscoveryGoal(
        goal=goal_text,
        target_url=target_url,
        max_steps=max_steps,
        timeout_seconds=120,
    )
    settings = AgentSettings(
        groq_model=model_name,
        target_url=target_url,
        max_steps=max_steps,
    )

    try:
        print("Starting autonomous discovery loop...\n")
        result = await run_discovery(
            goal=goal,
            surface=surface,
            llm=llm,
            settings=settings,
            recorder=recorder,
        )

        print("\n" + "=" * 60)
        print("  DISCOVERY RUN COMPLETED")
        print("=" * 60)
        print(f"  Status:       {result.status.value.upper()}")
        print(f"  Total Steps:  {result.steps_count}")
        print(f"  Duration:     {result.duration_seconds}s")
        if result.outputs:
            print(f"  Extracted:    {result.outputs}")
        if result.stop_reason:
            print(f"  Stop Reason:  {result.stop_reason}")
        if result.error_message:
            print(f"  Message:      {result.error_message}")

        print("\n  Recorded Steps Trace:")
        for step in result.steps:
            dec = step.model_decision
            target_str = f" [target: {dec.target_id}]" if dec.target_id else ""
            val_str = f" [value: {dec.value}]" if dec.value else ""
            status_str = step.action_result.get("status", "ok") if step.action_result else "ok"
            print(f"    Step {step.step}: {dec.action.value.upper()}{target_str}{val_str} -> {status_str}")
            if dec.reasoning_summary:
                print(f"            Reasoning: {dec.reasoning_summary}")

        print(f"\n  Evidence & Discovery Logs:")
        print(f"    - Trace log:   {recorder.trace_file}")
        print(f"    - Decisions:   {recorder.decisions_dir}")
        print(f"    - Final JSON:  {recorder.result_file}")
        print("=" * 60 + "\n")

    finally:
        await surface.close()


def main():
    parser = argparse.ArgumentParser(description="Phase 3 LLM-Driven Autonomous Discovery Loop")
    parser.add_argument("--goal", type=str, default=None, help="Natural-language discovery goal")
    parser.add_argument("--member", type=str, default="13278", help="Member ID (default: 13278)")
    parser.add_argument("--account-type", type=str, default="savings", help="Account type (savings or checking)")
    parser.add_argument("--headful", action="store_true", help="Run browser in visible headful mode")
    parser.add_argument("--mock", action="store_true", help="Force MockLLMClient instead of live Groq API")
    parser.add_argument("--model", type=str, default=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), help="Groq model name")
    parser.add_argument("--max-steps", type=int, default=15, help="Maximum steps allowed (default: 15)")
    parser.add_argument("--port", type=int, default=8000, help="Target port (default: 8000)")
    args = parser.parse_args()

    goal_text = args.goal
    if not goal_text:
        goal_text = f"Look up member {args.member} and read their current {args.account_type} balance."

    target_url = f"http://127.0.0.1:{args.port}"
    headless = not args.headful

    # Ensure test server is running
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
        time.sleep(0.8)

    asyncio.run(run_demo(
        goal_text=goal_text,
        target_url=target_url,
        headless=headless,
        use_mock=args.mock,
        model_name=args.model,
        max_steps=args.max_steps,
    ))


if __name__ == "__main__":
    main()
