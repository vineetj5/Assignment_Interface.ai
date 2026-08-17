"""Chat service integrating Phase 6 routing with Phase 5 replay."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from capability.repository import ArtifactRepository
from replay.engine import ReplayEngine
from routing.catalog import CapabilityCatalog
from routing.exceptions import RouterClientError, RoutingValidationError
from routing.models import ChatResponse, ChatResponseStatus, RoutingDecision, RoutingStatus
from routing.recorder import RoutingRecorder
from routing.response_formatter import ResponseFormatter
from routing.router import CapabilityRouter
from routing.session import ChatSessionStore, sessions
from routing.validator import CapabilityCallValidator


class ChatService:
    """Coordinates catalog routing, validation, deterministic replay, and response formatting."""

    def __init__(
        self,
        catalog: Optional[CapabilityCatalog] = None,
        router: Optional[CapabilityRouter] = None,
        validator: Optional[CapabilityCallValidator] = None,
        replay_engine: Optional[ReplayEngine] = None,
        repository: Optional[ArtifactRepository] = None,
        session_store: Optional[ChatSessionStore] = None,
        formatter: Optional[ResponseFormatter] = None,
        evidence_dir: Optional[Path] = None,
        replay_target_url: Optional[str] = None,
    ):
        self.catalog = catalog or CapabilityCatalog()
        self.router = router or CapabilityRouter()
        self.validator = validator or CapabilityCallValidator(self.catalog)
        self.repository = repository or ArtifactRepository()
        self.replay_engine = replay_engine or ReplayEngine(repository=self.repository, evidence_dir=evidence_dir)
        self.sessions = session_store or sessions
        self.formatter = formatter or ResponseFormatter()
        self.evidence_dir = evidence_dir
        self.replay_target_url = replay_target_url

    async def handle_message(self, session_id: str, message: str) -> ChatResponse:
        prepared = await self.prepare_message(session_id=session_id, message=message)
        if prepared.status != ChatResponseStatus.READY:
            return prepared
        return await self.execute_prepared(
            session_id=session_id,
            capability=prepared.capability,
            arguments=prepared.data or {},
        )

    async def prepare_message(self, session_id: str, message: str) -> ChatResponse:
        state = self.sessions.get(session_id)
        recorder = RoutingRecorder(evidence_dir=self.evidence_dir)
        capabilities = self.catalog.list_capabilities()
        recorder.record_metadata({
            "available_capabilities": [cap.name for cap in capabilities],
            "session_id": session_id,
        })

        try:
            decision = None
            if self.router.client is None:
                decision = self._short_pending_follow_up_decision(state, message)
            if decision is None:
                decision = await self.router.route(message=message, capabilities=capabilities, session_state=state)
            decision = self._merge_pending_arguments(decision, state, message)
            validated = self.validator.validate(decision)
        except RouterClientError:
            response = ChatResponse(
                status=ChatResponseStatus.ERROR,
                message="I couldn't understand the request right now.",
                reason_code="ROUTING_ERROR",
            )
            recorder.record_result(response)
            return response
        except RoutingValidationError:
            response = ChatResponse(
                status=ChatResponseStatus.ERROR,
                message="I couldn't safely route that request.",
                reason_code="ROUTING_VALIDATION_ERROR",
            )
            recorder.record_result(response)
            return response

        self._record_decision(recorder, validated)

        if validated.status == RoutingStatus.UNSUPPORTED:
            self.sessions.clear_pending(session_id)
            response = ChatResponse(
                status=ChatResponseStatus.UNSUPPORTED,
                message="That operation isn't available as an approved capability.",
                reason_code=validated.reason_code or "NO_MATCHING_CAPABILITY",
            )
            recorder.record_result(response)
            return response

        if validated.status == RoutingStatus.CLARIFY:
            state.pending_capability = validated.capability
            state.collected_arguments = dict(validated.arguments)
            state.missing_arguments = list(validated.missing_arguments)
            self.sessions.save(state)
            response = ChatResponse(
                status=ChatResponseStatus.NEEDS_INPUT,
                message=validated.clarification_question or "I need one more detail.",
                pending_capability=validated.capability,
                missing_arguments=validated.missing_arguments,
            )
            recorder.record_result(response)
            return response

        state.pending_capability = None
        state.collected_arguments = {}
        state.missing_arguments = []
        self.sessions.save(state)
        response = ChatResponse(
            status=ChatResponseStatus.READY,
            message=f"Running {validated.capability}.",
            capability=validated.capability,
            data=validated.arguments,
        )
        recorder.record_result(response)
        return response

    async def execute_prepared(self, session_id: str, capability: str, arguments: dict) -> ChatResponse:
        decision = RoutingDecision(
            status=RoutingStatus.INVOKE,
            capability=capability,
            arguments=arguments,
        )
        try:
            validated = self.validator.validate(decision)
        except RoutingValidationError:
            return ChatResponse(
                status=ChatResponseStatus.ERROR,
                message="I couldn't safely route that request.",
                reason_code="ROUTING_VALIDATION_ERROR",
            )

        result = await self._execute_replay(validated)
        response = self.formatter.format_replay(result)
        state = self.sessions.get(session_id)
        state.last_replay_run_id = result.run_id
        self.sessions.clear_pending(session_id)
        self.sessions.save(state)
        recorder = RoutingRecorder(evidence_dir=self.evidence_dir)
        recorder.record_result(response, replay_evidence=result.evidence_dir)
        return response

    async def _execute_replay(self, decision: RoutingDecision):
        if self.replay_target_url:
            artifact = self.repository.get_approved(decision.capability)
            if artifact is None:
                raise RoutingValidationError(f"No approved artifact for {decision.capability}.")
            artifact.entrypoint.url = self.replay_target_url
            if self.replay_target_url not in artifact.safety.allowed_origins:
                artifact.safety.allowed_origins.append(self.replay_target_url)
            return await self.replay_engine.execute(artifact, inputs=decision.arguments)
        return await self.replay_engine.execute_capability(name=decision.capability, inputs=decision.arguments)

    def _short_pending_follow_up_decision(self, state, message: str) -> Optional[RoutingDecision]:
        """Complete a pending clarification when the user gives a short answer."""
        if not state.pending_capability or not state.missing_arguments:
            return None

        cap = self.catalog.get(state.pending_capability)
        if not cap:
            return None

        normalized = message.lower().strip()
        tokens = re.findall(r"[a-z0-9_]+", normalized)
        if not tokens or len(tokens) > 4:
            return None
        if self._looks_like_new_query(normalized, tokens):
            return None

        extracted = self._extract_capability_arguments(normalized, cap)
        if not any(name in extracted for name in state.missing_arguments):
            return None

        merged = dict(state.collected_arguments)
        merged.update(extracted)
        still_missing = [
            spec.name for spec in cap.inputs
            if spec.required and spec.name not in merged
        ]
        return RoutingDecision(
            status=RoutingStatus.CLARIFY if still_missing else RoutingStatus.INVOKE,
            capability=state.pending_capability,
            arguments=merged,
            missing_arguments=still_missing,
            clarification_question=None,
            reason_code=None,
        )

    def _merge_pending_arguments(self, decision: RoutingDecision, state, message: str) -> RoutingDecision:
        """Merge collected pending args into a follow-up routing decision before validation."""
        if not state.pending_capability:
            return decision

        cap = self.catalog.get(state.pending_capability)
        if not cap:
            return decision

        extracted = self._extract_capability_arguments(message.lower(), cap)
        declared = {spec.name for spec in cap.inputs}
        cleaned_decision_args = {
            name: value for name, value in decision.arguments.items() if name in declared
        }

        fills_pending_slot = any(name in extracted or name in cleaned_decision_args for name in state.missing_arguments)
        capability = decision.capability or state.pending_capability
        short_follow_up = len(message.split()) <= 4
        if capability != state.pending_capability:
            if not (short_follow_up and fills_pending_slot):
                return decision

        if decision.status == RoutingStatus.UNSUPPORTED and not fills_pending_slot:
            return decision

        merged = dict(state.collected_arguments)
        merged.update(cleaned_decision_args)
        merged.update(extracted)

        still_missing = [
            spec.name for spec in cap.inputs
            if spec.required and spec.name not in merged
        ]
        status = RoutingStatus.CLARIFY if still_missing else RoutingStatus.INVOKE
        return RoutingDecision(
            status=status,
            capability=state.pending_capability,
            arguments=merged,
            missing_arguments=still_missing,
            clarification_question=decision.clarification_question,
            reason_code=decision.reason_code,
        )

    def _extract_capability_arguments(self, normalized_message: str, capability) -> dict:
        if hasattr(self.router, "_extract_arguments"):
            return self.router._extract_arguments(normalized_message, capability)
        return {}

    def _looks_like_new_query(self, normalized_message: str, tokens: list[str]) -> bool:
        account_answer_tokens = {"checking", "saving", "savings", "account", "acct", "type"}
        if tokens and all(token in account_answer_tokens for token in tokens):
            return False

        new_query_tokens = {
            "what",
            "which",
            "who",
            "lookup",
            "look",
            "find",
            "member",
            "balance",
            "transfer",
            "wire",
            "freeze",
            "open",
            "close",
        }
        return "?" in normalized_message or any(token in new_query_tokens for token in tokens)

    def _record_decision(self, recorder: RoutingRecorder, decision: RoutingDecision) -> None:
        sensitive = set()
        if decision.capability:
            cap = self.catalog.get(decision.capability)
            if cap:
                sensitive = {spec.name for spec in cap.inputs if spec.sensitive}
        recorder.record_decision(decision, sensitive_args=sensitive)
