"""Replay evidence recorder for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from automation.evidence import EvidenceStore
from capability.models import CapabilityArtifact
from replay.models import ReplayResult


class ReplayRecorder:
    """Persists structured evidence logs, traces, screenshots, and result JSON for replay runs."""

    def __init__(self, evidence_dir: Optional[Path] = None, run_id: Optional[str] = None):
        project_root = Path(__file__).resolve().parent.parent
        root_dir = evidence_dir or project_root / "evidence"
        self.run_id = run_id or f"replay_{int(Path(__file__).stat().st_mtime)}"
        self.evidence_store = EvidenceStore(base_dir=root_dir, run_id=self.run_id)
        self.trace_file = self.evidence_store.run_dir / "replay_trace.jsonl"
        self.result_file = self.evidence_store.run_dir / "result.json"

    def record_step_execution(
        self,
        step_id: str,
        action: str,
        target: Optional[Dict[str, Any]],
        bound_value: Optional[Any],
        action_result: Optional[Dict[str, Any]],
        observation_ref: Optional[str],
        extracted: Optional[Dict[str, Any]] = None,
        redact_sensitive: bool = True,
    ) -> None:
        """Record an executed step to replay_trace.jsonl."""
        safe_value = "[REDACTED]" if (redact_sensitive and bound_value is not None) else bound_value

        record = {
            "step_id": step_id,
            "action": action,
            "target": target,
            "value": safe_value,
            "action_result": action_result,
            "observation_ref": observation_ref,
            "extracted": extracted,
        }

        with open(self.trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def record_final_result(self, result: ReplayResult) -> None:
        """Write final ReplayResult object to result.json."""
        content = result.model_dump_json(indent=2, exclude_none=True)
        self.result_file.write_text(content, encoding="utf-8")
