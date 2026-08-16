"""Runtime policy guard for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

import urllib.parse
from capability.models import ArtifactStatus, CapabilityArtifact
from replay.exceptions import ReplayPolicyViolationError


class ReplayRuntimePolicy:
    """Enforces runtime safety allowlists and artifact compatibility rules."""

    def validate_artifact(self, artifact: CapabilityArtifact) -> None:
        """Validate artifact safety declarations before invocation."""
        if artifact.schema_version != "1":
            raise ReplayPolicyViolationError(
                f"Unsupported artifact schema_version '{artifact.schema_version}'. Only '1' is supported."
            )

        if artifact.identity.status != ArtifactStatus.APPROVED:
            raise ReplayPolicyViolationError(
                f"Artifact '{artifact.identity.name}' version '{artifact.identity.version}' is not approved for replay."
            )

        safety = artifact.safety
        if not safety.allowed_actions:
            raise ReplayPolicyViolationError("Safety policy requires a non-empty allowed_actions list.")

        for step in artifact.steps:
            if step.action.value not in safety.allowed_actions:
                raise ReplayPolicyViolationError(
                    f"Step '{step.id}' uses action '{step.action.value}' which is not in allowed actions: {safety.allowed_actions}"
                )

        if artifact.compatibility.surface_type != "web":
            raise ReplayPolicyViolationError(
                f"Unsupported surface type '{artifact.compatibility.surface_type}'. Only 'web' is supported."
            )

    def validate_origin(self, url: str, allowed_origins: list[str]) -> None:
        """Enforce that navigation target stays strictly inside allowed origins."""
        parsed_url = urllib.parse.urlparse(url)
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if not any(origin.startswith(ao) or url.startswith(ao) for ao in allowed_origins):
            raise ReplayPolicyViolationError(
                f"Target URL '{url}' (origin: '{origin}') violates allowed origins: {allowed_origins}"
            )
