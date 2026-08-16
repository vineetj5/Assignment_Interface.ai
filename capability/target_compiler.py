"""Target compiler for Phase 4 Capability Artifact Schema.

Compiles resolved runtime targets into durable, multi-signal TargetSpec locator bundles
while stripping ephemeral discovery observation IDs (e.g. 'e_06').
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from capability.models import (
    FrameTarget,
    LocatorStrategy,
    TargetSpec,
    ValueSource,
)


class TargetCompiler:
    """Compiles resolved step targets into robust, multi-strategy TargetSpecs."""

    def compile_target(
        self,
        resolved_target: Optional[Dict[str, Any]],
        action: str,
        step_index: int,
        account_type_value_source: Optional[ValueSource] = None,
    ) -> Optional[TargetSpec]:
        """Convert a resolved target into a durable TargetSpec."""
        if not resolved_target:
            return None

        raw_frame_path = resolved_target.get("frame_path") or []
        frame_targets = [
            FrameTarget(name=f) if isinstance(f, str) else FrameTarget(**f)
            for f in raw_frame_path
        ]

        role = resolved_target.get("role")
        name = resolved_target.get("name")
        tag = resolved_target.get("tag")
        text = resolved_target.get("text")
        attrs = resolved_target.get("attributes") or {}

        # 1. Special Case: Account Table Row Action (View link)
        if action == "click" and (name == "View" or text == "View" or "View" in str(name)):
            primary = LocatorStrategy(
                strategy="table_row_action",
                table="SHARE / DRAFT ACCOUNTS",
                row_match={
                    "column": "Type",
                    "value": account_type_value_source.model_dump()
                    if account_type_value_source
                    else {"source": "input_map", "input": "account_type", "mapping": {"savings": "SAV", "checking": "DDA"}},
                },
                action_control={
                    "role": "link",
                    "name": "View",
                },
            )
            fallbacks = [
                LocatorStrategy(strategy="role_name", role="link", name="View"),
                LocatorStrategy(strategy="text", text="View"),
            ]
            return TargetSpec(
                frame_path=frame_targets,
                primary=primary,
                fallbacks=fallbacks,
            )

        # 2. Special Case: Extract Balance Field
        if action == "extract" or name == "Current Balance" or "balance" in str(name).lower():
            primary = LocatorStrategy(
                strategy="field_by_label",
                label="Current Balance",
            )
            fallbacks = [
                LocatorStrategy(strategy="css", css=".balance-value"),
                LocatorStrategy(strategy="attributes", attributes={"class": "balance-value"}),
            ]
            return TargetSpec(
                frame_path=frame_targets,
                primary=primary,
                fallbacks=fallbacks,
            )

        # 3. Standard Textbox / Input (e.g. Member Number)
        if role == "textbox" or tag in ["input", "textarea"]:
            primary = LocatorStrategy(
                strategy="role_name",
                role=role or "textbox",
                name=name or attrs.get("name") or "Member Number",
            )
            fallbacks: List[LocatorStrategy] = []
            if name:
                fallbacks.append(LocatorStrategy(strategy="label", value=name))
            if "name" in attrs:
                fallbacks.append(LocatorStrategy(strategy="attributes", attributes={"name": attrs["name"]}))
            if "id" in attrs:
                fallbacks.append(LocatorStrategy(strategy="attributes", attributes={"id": attrs["id"]}))

            return TargetSpec(
                frame_path=frame_targets,
                primary=primary,
                fallbacks=fallbacks,
            )

        # 4. Standard Button / Submit
        if role == "button" or attrs.get("type") == "submit" or tag == "button":
            btn_name = name or attrs.get("value") or "Find Member"
            primary = LocatorStrategy(
                strategy="role_name",
                role="button",
                name=btn_name,
            )
            fallbacks = [
                LocatorStrategy(
                    strategy="attributes",
                    tag=tag or "input",
                    type=attrs.get("type") or "submit",
                    value=btn_name,
                )
            ]
            return TargetSpec(
                frame_path=frame_targets,
                primary=primary,
                fallbacks=fallbacks,
            )

        # 5. Generic Fallback
        primary = LocatorStrategy(
            strategy="role_name" if role and name else ("text" if text else "attributes"),
            role=role,
            name=name,
            text=text,
            attributes=attrs if attrs else None,
        )
        return TargetSpec(
            frame_path=frame_targets,
            primary=primary,
            fallbacks=[],
        )
