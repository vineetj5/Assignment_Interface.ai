from __future__ import annotations

import re
from typing import Any, Dict, List, Pattern, Union
from automation.models import Observation, InteractiveElement, DetectedMessage, StructuredTable


class EvidenceSanitizer:
    """Sanitizes observations, logs, and evidence to prevent accidental exposure of sensitive data."""

    def __init__(self, patterns: List[Pattern] = None, replacement: str = "[REDACTED]"):
        self.replacement = replacement
        # Common sensitive patterns: SSNs, credit card numbers, token headers, passwords
        self.patterns = patterns or [
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN
            re.compile(r"\b(?:\d[ -]*?){13,16}\b"),  # Credit Card numbers (approx)
            re.compile(r"(?i)(password|secret|token|api[_-]?key)\s*[:=]\s*['\"]?([^'\"\s]+)"),
        ]

    def sanitize_text(self, text: str) -> str:
        if not text:
            return text
        sanitized = text
        for pat in self.patterns:
            sanitized = pat.sub(self.replacement, sanitized)
        return sanitized

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = self.sanitize_text(v)
            elif isinstance(v, dict):
                result[k] = self.sanitize_dict(v)
            elif isinstance(v, list):
                result[k] = self.sanitize_list(v)
            else:
                result[k] = v
        return result

    def sanitize_list(self, data: List[Any]) -> List[Any]:
        result = []
        for item in data:
            if isinstance(item, str):
                result.append(self.sanitize_text(item))
            elif isinstance(item, dict):
                result.append(self.sanitize_dict(item))
            elif isinstance(item, list):
                result.append(self.sanitize_list(item))
            else:
                result.append(item)
        return result

    def sanitize_observation(self, obs: Observation) -> Observation:
        """Create a sanitized copy of an observation."""
        obs_dict = obs.model_dump()
        sanitized_dict = self.sanitize_dict(obs_dict)
        return Observation.model_validate(sanitized_dict)
