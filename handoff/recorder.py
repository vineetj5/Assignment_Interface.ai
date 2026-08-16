"""Evidence recorder for handoff events."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, Optional


class HandoffRecorder:
    def __init__(self, evidence_dir: Optional[Path] = None):
        self.root = evidence_dir or Path(__file__).resolve().parent.parent / "evidence"
        self.root.mkdir(parents=True, exist_ok=True)

    def record_event(self, run_id: str, event: str, payload: Dict[str, Any]) -> None:
        run_dir = self.root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": event,
            **payload,
        }
        with (run_dir / "handoff_trace.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

