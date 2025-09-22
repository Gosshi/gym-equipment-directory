"""Domain-level exception hierarchy for service and repository layers."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-specific failures."""


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist."""


class ConflictError(DomainError):
    """Raised when a state conflict occurs (e.g. duplicate entries)."""


class ValidationError(DomainError):
    """Raised when input validation fails at the domain/service layer."""


class InfrastructureError(DomainError):
    """Raised when infrastructure (DB or external service) is unavailable."""
