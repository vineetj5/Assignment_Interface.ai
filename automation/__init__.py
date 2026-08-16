from __future__ import annotations

from automation.adapter import SurfaceAdapter
from automation.evidence import EvidenceStore
from automation.exceptions import (
    ActionExecutionError,
    ConditionTimeoutError,
    ControlOwnershipError,
    ElementNotFoundError,
    SessionError,
    SurfaceError,
)
from automation.logger import ActionLogger
from automation.models import (
    ActionRequest,
    ActionResult,
    ActionType,
    BoundingBox,
    ControlOwner,
    DetectedDialog,
    DetectedMessage,
    FrameInfo,
    InteractiveElement,
    Observation,
    SessionState,
    SessionStatus,
    StructuredTable,
    TargetSpec,
)
from automation.observer import SurfaceObserver
from automation.redaction import EvidenceSanitizer
from automation.session import SessionManager
from automation.surface import PlaywrightSurface

__all__ = [
    "SurfaceAdapter",
    "PlaywrightSurface",
    "SessionManager",
    "SurfaceObserver",
    "ActionLogger",
    "EvidenceStore",
    "EvidenceSanitizer",
    "Observation",
    "InteractiveElement",
    "BoundingBox",
    "FrameInfo",
    "DetectedDialog",
    "DetectedMessage",
    "StructuredTable",
    "ActionType",
    "TargetSpec",
    "ActionRequest",
    "ActionResult",
    "SessionStatus",
    "ControlOwner",
    "SessionState",
    "SurfaceError",
    "SessionError",
    "ActionExecutionError",
    "ElementNotFoundError",
    "ConditionTimeoutError",
    "ControlOwnershipError",
]
