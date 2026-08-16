"""Data models for Phase 6 chat routing."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RoutingStatus(str, Enum):
    INVOKE = "invoke"
    CLARIFY = "clarify"
    UNSUPPORTED = "unsupported"


class RoutingDecision(BaseModel):
    status: RoutingStatus
    capability: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    missing_arguments: List[str] = Field(default_factory=list)
    clarification_question: Optional[str] = None
    reason_code: Optional[str] = None


class ChatResponseStatus(str, Enum):
    READY = "ready"
    SUCCESS = "success"
    NEEDS_INPUT = "needs_input"
    UNSUPPORTED = "unsupported"
    BUSINESS_OUTCOME = "business_outcome"
    ESCALATED = "escalated"
    FAILED = "failed"
    ERROR = "error"


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    status: ChatResponseStatus
    message: str
    capability: Optional[str] = None
    pending_capability: Optional[str] = None
    missing_arguments: List[str] = Field(default_factory=list)
    replay_run_id: Optional[str] = None
    run_id: Optional[str] = None
    intervention_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    reason_code: Optional[str] = None


class ChatReplayRequest(BaseModel):
    session_id: str
    capability: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
