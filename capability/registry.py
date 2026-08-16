"""Capability registry manager for Phase 4 Capability Artifact Schema.

Maintains metadata in artifacts/registry.json about all available capabilities, their
input/output signatures, versions, statuses, and example user prompts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional
from capability.exceptions import ArtifactRegistryError
from capability.models import (
    ArtifactStatus,
    CapabilityArtifact,
    CapabilityRegistryEntry,
    CapabilityRegistryFile,
)


class CapabilityRegistry:
    """Manages artifacts/registry.json for capability discovery and routing."""

    def __init__(self, registry_file: Optional[Path] = None):
        if registry_file is None:
            self.registry_file = Path(__file__).resolve().parent.parent / "artifacts" / "registry.json"
        else:
            self.registry_file = Path(registry_file)

        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            self._save_file(CapabilityRegistryFile(schema_version="1", capabilities=[]))

    def _load_file(self) -> CapabilityRegistryFile:
        if not self.registry_file.exists():
            return CapabilityRegistryFile(schema_version="1", capabilities=[])
        data = json.loads(self.registry_file.read_text(encoding="utf-8"))
        return CapabilityRegistryFile.model_validate(data)

    def _save_file(self, reg_file: CapabilityRegistryFile) -> None:
        content = reg_file.model_dump_json(indent=2, exclude_none=True)
        self.registry_file.write_text(content, encoding="utf-8")

    def register(
        self,
        artifact: CapabilityArtifact,
        relative_path: Optional[str] = None,
        examples: Optional[List[str]] = None,
    ) -> CapabilityRegistryEntry:
        """Register or update a capability in registry.json."""
        reg_file = self._load_file()
        name = artifact.identity.name
        version = artifact.identity.version
        path_str = relative_path or f"{name}/{version}.json"

        default_examples = [
            f"What is member 12345's savings balance?",
            f"Check the checking balance for member 76821.",
            f"Look up balance for member 13278.",
        ]

        existing_entry: Optional[CapabilityRegistryEntry] = None
        for cap in reg_file.capabilities:
            if cap.name == name:
                existing_entry = cap
                break

        if existing_entry:
            existing_entry.latest_version = version
            existing_entry.artifact_path = path_str
            existing_entry.description = artifact.identity.description
            existing_entry.status = artifact.identity.status
            existing_entry.inputs = artifact.inputs
            existing_entry.outputs = artifact.outputs
            if examples:
                existing_entry.examples = examples
            result_entry = existing_entry
        else:
            new_entry = CapabilityRegistryEntry(
                name=name,
                description=artifact.identity.description,
                latest_version=version,
                approved_version=version if artifact.identity.status == ArtifactStatus.APPROVED else None,
                status=artifact.identity.status,
                artifact_path=path_str,
                inputs=artifact.inputs,
                outputs=artifact.outputs,
                examples=examples or default_examples,
            )
            reg_file.capabilities.append(new_entry)
            result_entry = new_entry

        self._save_file(reg_file)
        return result_entry

    def get(self, name: str) -> Optional[CapabilityRegistryEntry]:
        """Look up a capability entry by name."""
        reg_file = self._load_file()
        for cap in reg_file.capabilities:
            if cap.name == name:
                return cap
        return None

    def list_capabilities(self) -> List[CapabilityRegistryEntry]:
        """List all capabilities in the registry."""
        return self._load_file().capabilities

    def set_approved_version(self, name: str, version: str) -> None:
        """Set the approved production version for a capability."""
        reg_file = self._load_file()
        for cap in reg_file.capabilities:
            if cap.name == name:
                cap.approved_version = version
                self._save_file(reg_file)
                return
        raise ArtifactRegistryError(f"Cannot set approved version: Capability '{name}' not found in registry.")
