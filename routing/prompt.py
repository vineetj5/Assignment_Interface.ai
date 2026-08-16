"""Prompt builder for optional LLM-backed capability routing."""

from __future__ import annotations

from typing import Iterable, Optional
from capability.models import CapabilityRegistryEntry
from routing.session import ChatSessionState


SYSTEM_PROMPT = """You are a capability router.

Your only job is to:
1. Select one available capability when it clearly matches the request.
2. Extract arguments explicitly provided by the user.
3. Report missing required arguments.
4. Ask for clarification when required information is absent.
5. Return unsupported if no available capability matches.

Never invent a capability.
Never generate browser actions.
Never generate selectors.
Never generate Playwright code.
Never choose an artifact version.
Never guess required business arguments.
When pending session context is provided, you may reuse already collected arguments from that pending request for short follow-up replies.
Never execute UI actions.

Return exactly one JSON object matching:
{
  "status": "invoke" | "clarify" | "unsupported",
  "capability": string | null,
  "arguments": object,
  "missing_arguments": array,
  "clarification_question": string | null,
  "reason_code": string | null
}
"""


def build_router_prompt(
    message: str,
    capabilities: Iterable[CapabilityRegistryEntry],
    session_state: Optional[ChatSessionState] = None,
) -> str:
    lines = ["AVAILABLE CAPABILITIES"]
    for index, cap in enumerate(capabilities, start=1):
        lines.append(f"\n{index}. {cap.name}")
        lines.append(f"Description: {cap.description}")
        lines.append("Required arguments:")
        for spec in cap.inputs:
            if spec.type.value == "enum" and spec.values:
                type_desc = " | ".join(spec.values)
            else:
                type_desc = spec.type.value
            required = "required" if spec.required else "optional"
            lines.append(f"- {spec.name}: {type_desc} ({required})")
        if cap.examples:
            lines.append("Examples:")
            for example in cap.examples:
                lines.append(f"- {example}")

    if session_state and session_state.pending_capability:
        lines.append("\nPENDING SESSION CONTEXT")
        lines.append(f"Pending capability: {session_state.pending_capability}")
        lines.append("Already collected arguments:")
        for name, value in session_state.collected_arguments.items():
            safe_value = "[REDACTED]" if name == "member_id" else value
            lines.append(f"- {name}: {safe_value}")
        if session_state.missing_arguments:
            lines.append("Missing arguments:")
            for name in session_state.missing_arguments:
                lines.append(f"- {name}")
        lines.append(
            "If the user reply supplies missing information for this pending request, return invoke with the pending capability and all collected arguments."
        )

    lines.append("\nUSER REQUEST")
    lines.append(message)
    return "\n".join(lines)
