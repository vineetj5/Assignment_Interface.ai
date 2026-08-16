"""Capability router for Phase 6."""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Protocol, runtime_checkable
from capability.models import CapabilityRegistryEntry, InputType
from dotenv import load_dotenv
from routing.exceptions import RouterClientError
from routing.models import RoutingDecision, RoutingStatus
from routing.prompt import SYSTEM_PROMPT, build_router_prompt
from routing.session import ChatSessionState

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@runtime_checkable
class RoutingClient(Protocol):
    async def route_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        ...


class GroqRoutingClient:
    """Optional production router using Groq structured JSON output."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        if not self.api_key:
            raise RouterClientError("Missing GROQ_API_KEY for routing.")
        try:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=self.api_key)
        except Exception as exc:
            raise RouterClientError(f"Failed to initialize Groq routing client: {exc}") from exc

    async def route_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        last_err: Optional[Exception] = None
        for _ in range(2):
            try:
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                return json.loads(response.choices[0].message.content)
            except Exception as exc:
                last_err = exc
                await asyncio.sleep(0.25)
        raise RouterClientError(f"Routing model failed: {last_err}")


class CapabilityRouter:
    """Routes user messages to approved capability calls or clarification."""

    def __init__(self, client: Optional[RoutingClient] = None, use_llm: bool = False):
        self.client = client
        self.use_llm = use_llm
        self.routing_llm_calls = 0

    async def route(
        self,
        message: str,
        capabilities: Iterable[CapabilityRegistryEntry],
        session_state: Optional[ChatSessionState] = None,
    ) -> RoutingDecision:
        caps = list(capabilities)
        if self.client or self.use_llm:
            client = self.client or GroqRoutingClient()
            prompt = build_router_prompt(message, caps, session_state=session_state)
            self.routing_llm_calls += 1
            data = await client.route_json(SYSTEM_PROMPT, prompt)
            return RoutingDecision.model_validate(data)
        return self._route_deterministically(message, caps, session_state)

    def _route_deterministically(
        self,
        message: str,
        capabilities: list[CapabilityRegistryEntry],
        session_state: Optional[ChatSessionState],
    ) -> RoutingDecision:
        normalized = message.lower()
        selected = self._select_capability(normalized, capabilities, session_state)
        if not selected:
            return RoutingDecision(
                status=RoutingStatus.UNSUPPORTED,
                reason_code="NO_MATCHING_CAPABILITY",
            )

        extracted = self._extract_arguments(normalized, selected)

        if session_state and session_state.pending_capability == selected.name:
            explicit_required = {
                spec.name
                for spec in selected.inputs
                if spec.required and spec.name in extracted
            }
            if explicit_required and not self._looks_like_new_query(normalized, selected):
                merged = dict(session_state.collected_arguments)
                merged.update(extracted)
                extracted = merged

        missing = [spec.name for spec in selected.inputs if spec.required and spec.name not in extracted]
        if missing:
            return RoutingDecision(
                status=RoutingStatus.CLARIFY,
                capability=selected.name,
                arguments=extracted,
                missing_arguments=missing,
                clarification_question=self._clarification_question(missing, selected),
            )

        return RoutingDecision(
            status=RoutingStatus.INVOKE,
            capability=selected.name,
            arguments=extracted,
        )

    def _select_capability(
        self,
        normalized_message: str,
        capabilities: list[CapabilityRegistryEntry],
        session_state: Optional[ChatSessionState],
    ) -> Optional[CapabilityRegistryEntry]:
        if session_state and session_state.pending_capability:
            pending = next((cap for cap in capabilities if cap.name == session_state.pending_capability), None)
            if pending and not self._looks_like_unsafe_or_different_intent(normalized_message):
                extracted = self._extract_arguments(normalized_message, pending)
                if any(name in extracted for name in session_state.missing_arguments):
                    return pending

        best: Optional[CapabilityRegistryEntry] = None
        best_score = 0
        for cap in capabilities:
            corpus = " ".join([cap.name, cap.description, *cap.examples]).lower()
            score = sum(1 for token in self._tokens(normalized_message) if len(token) > 2 and token in corpus)
            # Stronger signal when user provided values matching capability inputs.
            extracted = self._extract_arguments(normalized_message, cap)
            score += len(extracted) * 2
            if score > best_score:
                best = cap
                best_score = score
        return best if best_score >= 2 and not self._looks_like_unsafe_or_different_intent(normalized_message) else None

    def _extract_arguments(self, normalized_message: str, capability: CapabilityRegistryEntry) -> Dict[str, Any]:
        args: Dict[str, Any] = {}
        for spec in capability.inputs:
            if spec.type == InputType.STRING:
                if spec.validation and spec.validation.pattern:
                    match = re.search(spec.validation.pattern.replace("^", r"\b").replace("$", r"\b"), normalized_message)
                    if match:
                        args[spec.name] = match.group(0)
                elif spec.name.endswith("_id"):
                    match = re.search(r"\b\d{4,10}\b", normalized_message)
                    if match:
                        args[spec.name] = match.group(0)
            elif spec.type == InputType.ENUM and spec.values:
                for value in spec.values:
                    stems = {value.lower(), value.lower().rstrip("s")}
                    if any(re.search(rf"\b{re.escape(stem)}s?\b", normalized_message) for stem in stems if stem):
                        args[spec.name] = value
                        break
        return args

    def _clarification_question(self, missing: list[str], capability: CapabilityRegistryEntry) -> str:
        if missing == ["account_type"]:
            account_spec = next((spec for spec in capability.inputs if spec.name == "account_type"), None)
            if account_spec and account_spec.values:
                return f"Would you like the {' or '.join(account_spec.values)} balance?"
        if missing == ["member_id"]:
            return "What member ID would you like me to look up?"
        return f"Please provide: {', '.join(missing)}."

    def _looks_like_new_query(self, normalized_message: str, capability: CapabilityRegistryEntry) -> bool:
        extracted = self._extract_arguments(normalized_message, capability)
        return len(extracted) > 1

    def _looks_like_unsafe_or_different_intent(self, normalized_message: str) -> bool:
        blocked_terms = {
            "transfer",
            "wire",
            "freeze",
            "debit card",
            "credit card",
            "click",
            "selector",
            "playwright",
            "ignore",
            "admin",
        }
        return any(term in normalized_message for term in blocked_terms)

    def _tokens(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9_]+", text)
