#!/usr/bin/env python3
"""Phase 6 demo: natural-language routing into deterministic replay."""

from __future__ import annotations

import argparse
import asyncio
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from app import app
from routing.catalog import CapabilityCatalog
from routing.router import CapabilityRouter
from routing.service import ChatService


def ensure_server_running(host: str = "127.0.0.1", port: int = 8000) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex((host, port)) == 0:
            return False

    config = uvicorn.Config(app, host=host, port=port, log_level="error", loop="asyncio")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(0.8)
    return True


async def run_demo(message: str, target_url: str):
    ensure_server_running()
    catalog = CapabilityCatalog()
    service = ChatService(router=CapabilityRouter(use_llm=True), replay_target_url=target_url)
    capabilities = catalog.list_capabilities()

    print("========================================================")
    print(" PHASE 6: NATURAL LANGUAGE CAPABILITY ROUTING")
    print("========================================================")
    print("\nUser:")
    print(f"  {message}")
    print("\nAvailable Capabilities:")
    for cap in capabilities:
        print(f"  {cap.name}")

    response = await service.handle_message(session_id="phase6_demo", message=message)

    print("\nAssistant:")
    print(f"  {response.message}")
    print("\nResult:")
    print(f"  status        = {response.status.value}")
    if response.capability or response.pending_capability:
        print(f"  capability    = {response.capability or response.pending_capability}")
    if response.missing_arguments:
        print(f"  missing       = {', '.join(response.missing_arguments)}")
    if response.replay_run_id:
        print(f"  replay_run_id = {response.replay_run_id}")
        print("  LLM UI Decisions = 0")
    print("========================================================")


def main():
    parser = argparse.ArgumentParser(description="Phase 6 natural-language chat routing demo")
    parser.add_argument("--message", default="What is member 12345's checking balance?")
    parser.add_argument("--target-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    asyncio.run(run_demo(message=args.message, target_url=args.target_url))


if __name__ == "__main__":
    main()
