"""In-memory chat session state for Phase 6."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatSessionState(BaseModel):
    session_id: str
    pending_capability: Optional[str] = None
    collected_arguments: Dict[str, Any] = Field(default_factory=dict)
    missing_arguments: List[str] = Field(default_factory=list)
    last_replay_run_id: Optional[str] = None


class ChatSessionStore:
    """Small in-memory store suitable for the Phase 6 take-home demo."""

    def __init__(self):
        self._sessions: Dict[str, ChatSessionState] = {}

    def get(self, session_id: str) -> ChatSessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = ChatSessionState(session_id=session_id)
        return self._sessions[session_id]

    def save(self, state: ChatSessionState) -> None:
        self._sessions[state.session_id] = state

    def clear_pending(self, session_id: str) -> ChatSessionState:
        state = self.get(session_id)
        state.pending_capability = None
        state.collected_arguments = {}
        state.missing_arguments = []
        self.save(state)
        return state


sessions = ChatSessionStore()

