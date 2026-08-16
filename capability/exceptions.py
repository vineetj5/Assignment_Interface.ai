"""Exceptions for Phase 4 Capability Artifact Schema."""


class CapabilityError(Exception):
    """Base exception for capability artifact errors."""
    pass


class ArtifactCompilationError(CapabilityError):
    """Raised when a discovery run cannot be compiled into a valid capability artifact."""
    pass


class ArtifactValidationError(CapabilityError):
    """Raised when a capability artifact violates structural or semantic rules."""
    pass


class ArtifactSanitizationError(CapabilityError):
    """Raised when an artifact contains unsanitized sensitive concrete data."""
    pass


class ArtifactNotFoundError(CapabilityError):
    """Raised when a requested capability artifact or version is not found."""
    pass


class ArtifactRegistryError(CapabilityError):
    """Raised when registry operations fail."""
    pass
