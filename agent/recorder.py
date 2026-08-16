from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from agent.models import DiscoveryGoal, RecordedDiscoveryStep
from agent.results import DiscoveryRunResult


class DiscoveryRecorder:
    """Records LLM decisions, resolved targets, action results, and discovery traces."""

    def __init__(self, evidence_dir: Path | str, run_id: str):
        self.run_id = run_id
        self.evidence_dir = Path(evidence_dir)
        self.run_dir = self.evidence_dir / run_id
        self.decisions_dir = self.run_dir / "decisions"
        self.trace_file = self.run_dir / "discovery_trace.jsonl"
        self.result_file = self.run_dir / "result.json"

        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)

    def record_step(self, step: RecordedDiscoveryStep) -> None:
        step_dict = step.model_dump()
        # 1. Append to discovery_trace.jsonl
        with self.trace_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(step_dict) + "\n")

        # 2. Save individual decision JSON
        decision_file = self.decisions_dir / f"step_{step.step:03d}.json"
        with decision_file.open("w", encoding="utf-8") as f:
            json.dump(step_dict, f, indent=2)

    def record_result(self, result: DiscoveryRunResult) -> None:
        with self.result_file.open("w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2)
