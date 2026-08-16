"""Data models for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReplayStatus(str, Enum):
    SUCCESS = "success"
    BUSINESS_OUTCOME = "business_outcome"
    ESCALATED = "escalated"
    FAILED = "failed"


class FailureCategory(str, Enum):
    INPUT_VALIDATION = "input_validation"
    UNSUPPORTED_ARTIFACT = "unsupported_artifact"
    POLICY_VIOLATION = "policy_violation"
    TARGET_NOT_FOUND = "target_not_found"
    TARGET_AMBIGUOUS = "target_ambiguous"
    ACTION_FAILED = "action_failed"
    CHECKPOINT_FAILED = "checkpoint_failed"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    SESSION_EXPIRED = "session_expired"
    APPLICATION_ERROR = "application_error"


class ReplayRequest(BaseModel):
    capability: str = Field(..., description="Capability name to replay (e.g. lookup_balance)")
    version: Optional[str] = Field(default=None, description="Capability version (defaults to latest approved/available)")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Runtime argument values matching InputSpecs")
    run_id: Optional[str] = Field(default=None, description="Optional custom run ID")
    headful: bool = Field(default=False, description="Run browser headful for visual demo")


class BusinessOutcomeResult(BaseModel):
    code: str
    step_id: Optional[str] = None
    description: Optional[str] = None


class ReplayFailure(BaseModel):
    category: FailureCategory
    step_id: Optional[str] = None
    expected: Optional[str] = None
    observed: Optional[str] = None
    message: Optional[str] = None
    recoverable: bool = False


class EscalationResult(BaseModel):
    code: str
    step_id: Optional[str] = None
    reason: str


class RecoveryRecord(BaseModel):
    code: str
    attempt: int
    action: str
    status: str


class ReplayResult(BaseModel):
    status: ReplayStatus
    run_id: str
    capability: str
    version: str
    intervention_id: Optional[str] = None
    outputs: Optional[Dict[str, Any]] = None
    outcome: Optional[BusinessOutcomeResult] = None
    failure: Optional[ReplayFailure] = None
    escalation: Optional[EscalationResult] = None
    steps_completed: int = 0
    duration_seconds: float = 0.0
    evidence_dir: Optional[str] = None


class ConditionResult(BaseModel):
    matched: bool
    expected: Optional[Any] = None
    observed: Optional[Any] = None
    details: Optional[str] = None


class ReplayContext(BaseModel):
    run_id: str
    capability: str
    version: str
    started_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    current_step_id: Optional[str] = None
    current_step_index: int = 0
    outputs: Dict[str, Any] = Field(default_factory=dict)
    checkpoints: Dict[str, Any] = Field(default_factory=dict)
    recoveries: List[RecoveryRecord] = Field(default_factory=list)
    evidence_dir: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}
