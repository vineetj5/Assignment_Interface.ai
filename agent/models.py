from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DiscoveryGoal(BaseModel):
    goal: str
    target_url: str = "http://127.0.0.1:8000"
    max_steps: int = 15
    timeout_seconds: int = 120


class AgentActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    EXTRACT = "extract"
    WAIT = "wait"
    FINISH = "finish"
    ESCALATE = "escalate"


class AgentDecision(BaseModel):
    action: AgentActionType
    target_id: Optional[str] = None
    value: Optional[str] = None
    reasoning_summary: str
    expected_result: Optional[str] = None
    extracted_output: Optional[Dict[str, Any]] = None
    escalation_reason: Optional[str] = None


class RecordedDiscoveryStep(BaseModel):
    step: int
    observation_ref: Optional[str] = None
    model_decision: AgentDecision
    resolved_target: Optional[Dict[str, Any]] = None
    action_result: Optional[Dict[str, Any]] = None
    extracted_output: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
