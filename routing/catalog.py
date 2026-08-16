"""Capability catalog exposed to the Phase 6 router."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from capability.models import ArtifactStatus, CapabilityRegistryEntry
from capability.registry import CapabilityRegistry


class CapabilityCatalog:
    """Reads public, approved capability contracts from artifacts/registry.json."""

    def __init__(self, registry_file: Optional[Path] = None):
        self.registry = CapabilityRegistry(registry_file=registry_file)

    def list_capabilities(self) -> List[CapabilityRegistryEntry]:
        return [
            cap
            for cap in self.registry.list_capabilities()
            if cap.status == ArtifactStatus.APPROVED and cap.approved_version
        ]

    def get(self, name: str) -> Optional[CapabilityRegistryEntry]:
        cap = self.registry.get(name)
        if not cap or cap.status != ArtifactStatus.APPROVED or not cap.approved_version:
            return None
        return cap

