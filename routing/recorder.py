"""Phase 6 routing evidence recorder."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, Optional
from routing.models import ChatResponse, RoutingDecision


class RoutingRecorder:
    """Writes small sanitized routing records and references Phase 5 evidence."""

    def __init__(self, evidence_dir: Optional[Path] = None, run_id: Optional[str] = None):
        root = evidence_dir or Path(__file__).resolve().parent.parent / "evidence"
        self.run_id = run_id or f"chat_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        self.run_dir = root / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def record_decision(self, decision: RoutingDecision, sensitive_args: set[str]) -> None:
        data = decision.model_dump(mode="json")
        args = data.get("arguments") or {}
        for name in sensitive_args:
            if name in args:
                args[name] = "[REDACTED]"
        data["arguments"] = args
        self._write_json("routing_decision.json", data)

    def record_result(self, response: ChatResponse, replay_evidence: Optional[str] = None) -> None:
        self._write_json("result.json", response.model_dump(mode="json", exclude_none=True))
        if response.replay_run_id:
            self._write_json(
                "replay_reference.json",
                {"replay_run_id": response.replay_run_id, "replay_evidence": replay_evidence},
            )

    def record_metadata(self, data: Dict[str, Any]) -> None:
        payload = {
            "run_id": self.run_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            **data,
        }
        self._write_json("metadata.json", payload)

    def _write_json(self, filename: str, data: Dict[str, Any]) -> None:
        (self.run_dir / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")

