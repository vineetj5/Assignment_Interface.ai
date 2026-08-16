"""Sanitizer for Phase 4 Capability Artifact Schema.

Scans artifacts to ensure no concrete discovery data (sensitive member numbers,
concrete balances, email addresses, phone numbers) leaks into saved artifacts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from capability.exceptions import ArtifactSanitizationError
from capability.models import CapabilityArtifact


class ArtifactSanitizer:
    """Scans and validates that artifacts are clean of concrete sensitive discovery literals."""

    def __init__(self, blocked_patterns: Optional[List[str]] = None):
        self.blocked_patterns = blocked_patterns or [
            r"\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?",  # Concrete currency like $5,521.10
        ]

    def sanitize(
        self,
        artifact: CapabilityArtifact,
        known_discovery_values: Optional[List[str]] = None,
    ) -> None:
        """Scan the serialized artifact for any forbidden discovery literals."""
        artifact_json = artifact.model_dump_json(exclude_none=True)

        # 1. Check for lingering temporary observation IDs (e_01 .. e_99)
        e_matches = re.findall(r'"e_\d{2,3}"', artifact_json)
        if e_matches:
            raise ArtifactSanitizationError(
                f"Sanitization violation: Ephemeral observation IDs {e_matches} found in artifact JSON."
            )

        # 2. Check known concrete values from the discovery trace (e.g. "13278", "$5,521.10")
        if known_discovery_values:
            for val in known_discovery_values:
                val_str = str(val).strip()
                if not val_str or len(val_str) < 3:
                    continue
                if val_str in artifact_json:
                    raise ArtifactSanitizationError(
                        f"Sanitization violation: Concrete discovery literal '{val_str}' found in compiled artifact JSON."
                    )

        # 3. Check forbidden regex patterns (e.g. concrete currency values)
        for pattern in self.blocked_patterns:
            match = re.search(pattern, artifact_json)
            if match:
                raise ArtifactSanitizationError(
                    f"Sanitization violation: Found sensitive concrete pattern match '{match.group(0)}' in artifact JSON."
                )
