"""Models for Phase 7 human-in-the-loop handoff."""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ControlOwner(str, Enum):
    AUTOMATION = "automation"
    HUMAN = "human"
    NONE = "none"


class RunState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSING = "pausing"
    WAITING_FOR_HUMAN = "waiting_for_human"
    HUMAN_CONTROL = "human_control"
    RESUMING = "resuming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InterventionSource(str, Enum):
    DISCOVERY = "discovery"
    REPLAY = "replay"
    POLICY = "policy"


class InterventionStatus(str, Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ResumeMode(str, Enum):
    RECHECK_CURRENT_STEP = "recheck_current_step"
    RETRY_CURRENT_STEP = "retry_current_step"
    CONTINUE_NEXT_STEP = "continue_next_step"


class InterventionRequest(BaseModel):
    intervention_id: str
    run_id: str
    source: InterventionSource
    capability: Optional[str] = None
    capability_version: Optional[str] = None
    step_id: Optional[str] = None
    step_index: Optional[int] = None
    reason_code: str
    reason: str
    expected_state: Optional[str] = None
    observed_state: Optional[str] = None
    screenshot_path: Optional[str] = None
    observation_path: Optional[str] = None
    browser_session_id: str
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    status: InterventionStatus = InterventionStatus.OPEN
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime.datetime] = None
    resumed_at: Optional[datetime.datetime] = None


class ReplayContinuation(BaseModel):
    run_id: str
    artifact_name: str
    artifact_version: str
    current_step_index: int = 0
    current_step_id: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    collected_outputs: Dict[str, Any] = Field(default_factory=dict)
    resume_mode: ResumeMode = ResumeMode.RECHECK_CURRENT_STEP


class RunHandle(BaseModel):
    run_id: str
    capability: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    state: RunState = RunState.CREATED
    owner: ControlOwner = ControlOwner.NONE
    browser_session_id: str
    intervention_id: Optional[str] = None
    replay_run_id: Optional[str] = None
    capability_version: Optional[str] = None
    evidence_dir: Optional[str] = None
    continuation: Optional[ReplayContinuation] = None

    model_config = {"arbitrary_types_allowed": True}

