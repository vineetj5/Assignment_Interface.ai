"""In-memory stores for Phase 7 handoff runs and interventions."""

from __future__ import annotations

from typing import Dict, List, Optional
from handoff.models import InterventionRequest, RunHandle


class HandoffStore:
    def __init__(self):
        self.runs: Dict[str, RunHandle] = {}
        self.interventions: Dict[str, InterventionRequest] = {}

    def save_run(self, handle: RunHandle) -> None:
        self.runs[handle.run_id] = handle

    def get_run(self, run_id: str) -> Optional[RunHandle]:
        return self.runs.get(run_id)

    def save_intervention(self, intervention: InterventionRequest) -> None:
        self.interventions[intervention.intervention_id] = intervention

    def get_intervention(self, intervention_id: str) -> Optional[InterventionRequest]:
        return self.interventions.get(intervention_id)

    def intervention_for_run(self, run_id: str) -> Optional[InterventionRequest]:
        for intervention in self.interventions.values():
            if intervention.run_id == run_id:
                return intervention
        return None

    def list_open(self) -> List[InterventionRequest]:
        return [item for item in self.interventions.values() if item.status.value in {"open", "claimed"}]


store = HandoffStore()

