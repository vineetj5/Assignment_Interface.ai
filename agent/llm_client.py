from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Callable, Dict, List, Optional, Protocol, Union, runtime_checkable
from agent.context import DiscoveryContext
from agent.exceptions import LLMClientError
from agent.models import AgentActionType, AgentDecision, DiscoveryGoal
from agent.prompt import build_step_prompt, build_system_prompt


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM reasoning clients."""

    async def decide(
        self,
        goal: DiscoveryGoal,
        observation_summary: str,
        context: DiscoveryContext,
        validation_error: Optional[str] = None,
    ) -> AgentDecision:
        ...


class GroqLLMClient:
    """Production LLM client powered by Groq API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self._client = None

        if not self.api_key:
            import os
            self.api_key = os.getenv("GROQ_API_KEY", "")

        if not self.api_key:
            raise LLMClientError(
                "Missing GROQ_API_KEY. Copy .env.example to .env and provide your local API key."
            )

        try:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=self.api_key)
        except Exception as e:
            raise LLMClientError(f"Failed to initialize Groq client: {e}")

    async def decide(
        self,
        goal: DiscoveryGoal,
        observation_summary: str,
        context: DiscoveryContext,
        validation_error: Optional[str] = None,
    ) -> AgentDecision:
        system_prompt = build_system_prompt()
        user_prompt = build_step_prompt(
            goal=goal,
            context=context,
            observation_summary=observation_summary,
            validation_error=validation_error,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_err = None
        for attempt in range(2):
            try:
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                content = response.choices[0].message.content
                data = json.loads(content)
                return AgentDecision.model_validate(data)
            except Exception as e:
                last_err = e
                await asyncio.sleep(0.5)

        raise LLMClientError(f"Groq API call or decision parsing failed: {last_err}")


class MockLLMClient:
    """Programmable / rule-based Mock LLM client for deterministic testing and simulated demos."""

    def __init__(
        self,
        scripted_decisions: Optional[List[AgentDecision]] = None,
        rule_based: bool = True,
    ):
        self.scripted_decisions = list(scripted_decisions) if scripted_decisions else []
        self.rule_based = rule_based
        self.call_count = 0

    async def decide(
        self,
        goal: DiscoveryGoal,
        observation_summary: str,
        context: DiscoveryContext,
        validation_error: Optional[str] = None,
    ) -> AgentDecision:
        self.call_count += 1

        # 1. Return scripted decision if available
        if self.scripted_decisions:
            return self.scripted_decisions.pop(0)

        # 2. Rule-based autonomous discovery matching typical bank flow
        member_match = re.search(r"\b\d{5}\b", goal.goal)
        member_id = member_match.group(0) if member_match else "13278"
        account_type = "savings" if "saving" in goal.goal.lower() else "checking"

        # Check for verification dialog
        if "[ACTIVE DIALOGS]" in observation_summary:
            return AgentDecision(
                action=AgentActionType.ESCALATE,
                reasoning_summary="Observed an active verification dialog that requires operator escalation.",
                escalation_reason="Unexpected verification dialog detected.",
            )

        # Check for member not found / error messages
        if "MEMBER_NOT_FOUND" in observation_summary or "Member Not Found" in observation_summary:
            return AgentDecision(
                action=AgentActionType.FINISH,
                reasoning_summary="Target member was not found in the servicing system.",
                extracted_output={"status": "member_not_found", "member_id": member_id},
            )

        # On Account Detail page: extract balance
        if "Account Detail" in observation_summary or "BALANCE INFORMATION" in observation_summary:
            if "current_balance" not in context.extracted_values:
                target_id = None
                for line in observation_summary.splitlines():
                    if ("balance" in line.lower() or "$" in line or "tag=<td>" in line) and "id=" in line:
                        m = re.search(r"id=(e_\d+)", line)
                        if m:
                            target_id = m.group(1)
                            break
                if not target_id:
                    m = re.search(r"id=(e_\d+)", observation_summary)
                    target_id = m.group(1) if m else "e_06"

                return AgentDecision(
                    action=AgentActionType.EXTRACT,
                    target_id=target_id,
                    reasoning_summary="On Account Detail page, reading Current Balance.",
                    expected_result="Current balance amount extracted.",
                )
            else:
                return AgentDecision(
                    action=AgentActionType.FINISH,
                    reasoning_summary=f"Successfully extracted balance for member {member_id}.",
                    extracted_output={
                        "member_id": member_id,
                        "account_type": account_type,
                        "current_balance": context.extracted_values.get("current_balance", "$5,521.10"),
                    },
                )

        # On Member Inquiry page with loaded member accounts (has View links)
        has_account_links = ("tag=<a>" in observation_summary or "role=link" in observation_summary) and "View" in observation_summary
        if has_account_links:
            target_id = None
            for line in observation_summary.splitlines():
                if "tag=<a>" in line or "role=link" in line or "View" in line:
                    if account_type == "savings" and ("SAV" in line or "Savings" in line):
                        m = re.search(r"id=(e_\d+)", line)
                        if m:
                            target_id = m.group(1)
                            break
                    elif account_type == "checking" and ("DDA" in line or "Checking" in line):
                        m = re.search(r"id=(e_\d+)", line)
                        if m:
                            target_id = m.group(1)
                            break
            if not target_id:
                for line in observation_summary.splitlines():
                    if "tag=<a>" in line or "role=link" in line:
                        m = re.search(r"id=(e_\d+)", line)
                        if m:
                            target_id = m.group(1)
                            break

            if target_id:
                return AgentDecision(
                    action=AgentActionType.CLICK,
                    target_id=target_id,
                    reasoning_summary=f"Member profile loaded; clicking View for {account_type} account.",
                    expected_result="Account Detail screen opened.",
                )

        # On initial Member Inquiry form:
        # If previous step was FILL, next step is CLICK Find Member
        if context.previous_action and context.previous_action.action == AgentActionType.FILL:
            target_id = None
            for line in observation_summary.splitlines():
                if "Find Member" in line and "id=" in line:
                    m = re.search(r"id=(e_\d+)", line)
                    if m:
                        target_id = m.group(1)
                        break
            if not target_id:
                for line in observation_summary.splitlines():
                    if "type=submit" in line and "id=" in line:
                        m = re.search(r"id=(e_\d+)", line)
                        if m:
                            target_id = m.group(1)
                            break
            if not target_id:
                target_id = "e_07"

            return AgentDecision(
                action=AgentActionType.CLICK,
                target_id=target_id,
                reasoning_summary="Member number entered; clicking Find Member to load profile.",
                expected_result="Profile and account tables displayed.",
            )

        # Otherwise fill member number into search textbox
        target_id = None
        for line in observation_summary.splitlines():
            if ("Member Number" in line or "member_number" in line or "role=textbox" in line or ("tag=<input>" in line and "button" not in line and "submit" not in line)) and "id=" in line:
                m = re.search(r"id=(e_\d+)", line)
                if m:
                    target_id = m.group(1)
                    break

        if not target_id:
            return AgentDecision(
                action=AgentActionType.WAIT,
                value="500",
                reasoning_summary="Waiting for search input control to load in target workspace.",
                expected_result="Search inputs become visible.",
            )

        return AgentDecision(
            action=AgentActionType.FILL,
            target_id=target_id,
            value=member_id,
            reasoning_summary=f"Entering member number {member_id} into search textbox.",
            expected_result=f"Member number {member_id} entered.",
        )
