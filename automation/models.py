from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class ControlOwner(str, Enum):
    AUTOMATION = "automation"
    HUMAN = "human"


class SessionState(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    control_owner: ControlOwner = ControlOwner.AUTOMATION
    started_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    current_url: Optional[str] = None


class FrameInfo(BaseModel):
    frame_id: str
    name: str = ""
    url: str = ""
    parent_frame_id: Optional[str] = None
    depth: int = 0


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class InteractiveElement(BaseModel):
    observation_id: str
    tag: str
    role: str = ""
    name: str = ""
    label: str = ""
    text: str = ""
    value: Optional[str] = None
    attributes: Dict[str, str] = Field(default_factory=dict)
    disabled: bool = False
    visible: bool = True
    editable: bool = False
    frame_path: List[str] = Field(default_factory=list)
    bounding_box: Optional[BoundingBox] = None


class DetectedDialog(BaseModel):
    title: str = ""
    text: str = ""
    buttons: List[str] = Field(default_factory=list)
    frame_path: List[str] = Field(default_factory=list)


class DetectedMessage(BaseModel):
    title: str = ""
    message: str = ""
    code: str = ""
    level: str = "info"  # "info", "business", "failure", "warning"
    frame_path: List[str] = Field(default_factory=list)


class StructuredTable(BaseModel):
    caption: str = ""
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    frame_path: List[str] = Field(default_factory=list)


class Observation(BaseModel):
    observation_id: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    page_url: str = ""
    page_title: str = ""
    frame_hierarchy: List[FrameInfo] = Field(default_factory=list)
    interactive_elements: List[InteractiveElement] = Field(default_factory=list)
    visible_text: str = ""
    detected_messages: List[DetectedMessage] = Field(default_factory=list)
    detected_dialogs: List[DetectedDialog] = Field(default_factory=list)
    structured_tables: List[StructuredTable] = Field(default_factory=list)
    active_element: Optional[str] = None
    screenshot_ref: Optional[str] = None

    def get_element(self, observation_id: str) -> Optional[InteractiveElement]:
        for el in self.interactive_elements:
            if el.observation_id == observation_id:
                return el
        return None

    def to_llm_summary(self, scope_to_target: bool = True) -> str:
        """Format a concise representation of the current observation suitable for LLMs, scoped to the target app."""
        lines = [
            f"=== Page: {self.page_title} ({self.page_url}) ===",
        ]

        # Determine if target frames exist (e.g. host shell embedding legacy-app / workspace)
        target_elements = self.interactive_elements
        target_tables = self.structured_tables
        target_messages = self.detected_messages
        target_dialogs = self.detected_dialogs

        if scope_to_target:
            has_nested_target = any(
                any("legacy" in fp or "workspace" in fp for fp in el.frame_path)
                for el in self.interactive_elements
            )
            if has_nested_target:
                # Filter out host shell controls (e.g. assistant conversation panel, sample buttons)
                target_elements = [
                    el for el in self.interactive_elements
                    if any("legacy" in fp or "workspace" in fp for fp in el.frame_path)
                ]
                target_tables = [
                    t for t in self.structured_tables
                    if any("legacy" in fp or "workspace" in fp for fp in t.frame_path)
                ]
                target_messages = [
                    m for m in self.detected_messages
                    if not m.frame_path or any("legacy" in fp or "workspace" in fp for fp in m.frame_path)
                ]
                target_dialogs = [
                    d for d in self.detected_dialogs
                    if not d.frame_path or any("legacy" in fp or "workspace" in fp for fp in d.frame_path)
                ]

        if target_dialogs:
            lines.append("\n[ACTIVE DIALOGS]")
            for d in target_dialogs:
                btn_str = ", ".join(d.buttons) if d.buttons else "none"
                frame_desc = " > ".join(d.frame_path) if d.frame_path else "target"
                lines.append(f"  * Dialog: '{d.title}' - Text: '{d.text}' - Buttons: [{btn_str}] (Frame: {frame_desc})")

        if target_messages:
            lines.append("\n[MESSAGES / OUTCOMES]")
            for m in target_messages:
                code_str = f" [Code: {m.code}]" if m.code else ""
                lines.append(f"  * [{m.level.upper()}] {m.title}: {m.message}{code_str}")

        lines.append("\n[INTERACTIVE CONTROLS]")
        if not target_elements:
            lines.append("  (No interactive controls found in target application)")
        else:
            for el in target_elements:
                parts = [f"id={el.observation_id}", f"tag=<{el.tag}>"]
                if el.role:
                    parts.append(f"role={el.role}")
                if el.name:
                    parts.append(f"name='{el.name}'")
                elif el.label:
                    parts.append(f"label='{el.label}'")
                elif el.text:
                    parts.append(f"text='{el.text}'")

                if el.value is not None and el.value != "":
                    parts.append(f"value='{el.value}'")
                if el.disabled:
                    parts.append("[DISABLED]")
                if el.frame_path:
                    parts.append(f"frame={' > '.join(el.frame_path)}")
                lines.append("  - " + " ".join(parts))

        if target_tables:
            lines.append("\n[TABLES]")
            for t in target_tables:
                if t.caption:
                    lines.append(f"  Table: {t.caption}")
                if t.headers:
                    lines.append("  | " + " | ".join(t.headers) + " |")
                    lines.append("  |-" + "-|-".join(["---"] * len(t.headers)) + "-|")
                for r in t.rows:
                    lines.append("  | " + " | ".join(r) + " |")

        return "\n".join(lines)


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    EXTRACT = "extract"
    WAIT = "wait"
    SCREENSHOT = "screenshot"


class TargetSpec(BaseModel):
    observation_id: Optional[str] = None
    role: Optional[str] = None
    name: Optional[str] = None
    text: Optional[str] = None
    tag: Optional[str] = None
    attributes: Dict[str, str] = Field(default_factory=dict)
    frame_path: List[str] = Field(default_factory=list)
    css: Optional[str] = None


class ActionRequest(BaseModel):
    action_type: ActionType
    target: Optional[Union[str, TargetSpec, Dict[str, Any]]] = None
    value: Optional[str] = None
    timeout_ms: int = 5000
    condition: Optional[str] = None  # e.g. "visible", "hidden", "networkidle"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    action_id: str
    action_type: ActionType
    status: str = "success"  # "success" or "failed"
    started_at: str
    completed_at: str
    duration_ms: float
    output: Any = None
    error: Optional[str] = None
    before_observation_ref: Optional[str] = None
    after_observation_ref: Optional[str] = None
    screenshot_ref: Optional[str] = None
