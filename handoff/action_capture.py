"""Human action capture placeholders for Phase 7 auditability."""

from __future__ import annotations

import datetime
from typing import Any, Dict, List


class HumanActionCapture:
    """Captures operator-supplied notes/actions without modifying artifacts."""

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def record(self, run_id: str, operator_id: str, action: str, details: Dict[str, Any] | None = None) -> None:
        self.records.append({
            "run_id": run_id,
            "operator_id": operator_id,
            "action": action,
            "details": details or {},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

