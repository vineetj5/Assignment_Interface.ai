from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from agent.models import DiscoveryGoal, RecordedDiscoveryStep


class DiscoveryRunStatus(str, Enum):
    SUCCESS = "success"
    BUSINESS_OUTCOME = "business_outcome"
    ESCALATED = "escalated"
    STOPPED = "stopped"
    FAILED = "failed"


class DiscoveryRunResult(BaseModel):
    status: DiscoveryRunStatus
    run_id: str
    goal: DiscoveryGoal
    steps_count: int
    duration_seconds: float
    outputs: Optional[Dict[str, Any]] = None
    stop_reason: Optional[str] = None
    error_message: Optional[str] = None
    evidence_dir: Optional[str] = None
    steps: List[RecordedDiscoveryStep] = Field(default_factory=list)
