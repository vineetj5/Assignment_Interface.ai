"""Artifact repository for Phase 4 Capability Artifact Schema.

Stores, loads, and manages versioned capability artifacts in the filesystem under artifacts/<capability>/<version>.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional
from capability.exceptions import ArtifactNotFoundError
from capability.models import ArtifactStatus, CapabilityArtifact


class ArtifactRepository:
    """Filesystem repository for managing versioned capability artifacts."""

    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir is None:
            # Default to <repo_root>/artifacts
            self.root_dir = Path(__file__).resolve().parent.parent / "artifacts"
        else:
            self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _get_capability_dir(self, name: str) -> Path:
        return self.root_dir / name

    def _get_artifact_path(self, name: str, version: str) -> Path:
        return self._get_capability_dir(name) / f"{version}.json"

    def save(self, artifact: CapabilityArtifact) -> Path:
        """Save a CapabilityArtifact to artifacts/<name>/<version>.json."""
        cap_dir = self._get_capability_dir(artifact.identity.name)
        cap_dir.mkdir(parents=True, exist_ok=True)

        file_path = self._get_artifact_path(artifact.identity.name, artifact.identity.version)
        content = artifact.model_dump_json(indent=2, exclude_none=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def load(self, name: str, version: str) -> CapabilityArtifact:
        """Load a specific version of a capability artifact."""
        file_path = self._get_artifact_path(name, version)
        if not file_path.exists():
            raise ArtifactNotFoundError(
                f"Capability artifact '{name}' version '{version}' not found at {file_path}"
            )
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return CapabilityArtifact.model_validate(data)

    def list_versions(self, name: str) -> List[str]:
        """List all available versions for a capability."""
        cap_dir = self._get_capability_dir(name)
        if not cap_dir.exists():
            return []
        versions = []
        for file in sorted(cap_dir.glob("*.json")):
            versions.append(file.stem)
        return versions

    def get_latest(self, name: str) -> CapabilityArtifact:
        """Load the latest version of a capability."""
        versions = self.list_versions(name)
        if not versions:
            raise ArtifactNotFoundError(f"No versions found for capability '{name}' in repository.")
        # Return the highest semantic version
        latest_ver = versions[-1]
        return self.load(name, latest_ver)

    def get_approved(self, name: str) -> Optional[CapabilityArtifact]:
        """Load the approved version of a capability, or None if no approved version exists."""
        versions = self.list_versions(name)
        for ver in reversed(versions):
            art = self.load(name, ver)
            if art.identity.status == ArtifactStatus.APPROVED:
                return art
        return None
