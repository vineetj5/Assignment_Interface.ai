"""FastAPI endpoints for Phase 6 chat routing."""

from __future__ import annotations

from fastapi import APIRouter
from routing.models import ChatReplayRequest, ChatRequest, ChatResponse
from routing.router import CapabilityRouter
from routing.service import ChatService


router = APIRouter(prefix="/api/chat", tags=["chat"])
chat_service = ChatService(router=CapabilityRouter(use_llm=True))


@router.post("/message", response_model=ChatResponse)
async def post_chat_message(request: ChatRequest) -> ChatResponse:
    return await chat_service.handle_message(session_id=request.session_id, message=request.message)


@router.post("/prepare", response_model=ChatResponse)
async def prepare_chat_message(request: ChatRequest) -> ChatResponse:
    return await chat_service.prepare_message(session_id=request.session_id, message=request.message)


@router.post("/replay", response_model=ChatResponse)
async def replay_prepared_message(request: ChatReplayRequest) -> ChatResponse:
    return await chat_service.execute_prepared(
        session_id=request.session_id,
        capability=request.capability,
        arguments=request.arguments,
    )
