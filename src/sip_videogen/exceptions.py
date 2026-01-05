"""Centralized exception classes for sip-videogen.

This module provides a hierarchy of exceptions for better error handling
and user-friendly error messages throughout the application.
"""


class SipVideoGenError(Exception):
    """Base exception for all sip-videogen errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(self, message: str, details: str | None = None):
        """Initialize the exception.

        Args:
            message: User-friendly error message.
            details: Additional technical details for debugging.
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\n  Details: {self.details}"
        return self.message


class ConfigurationError(SipVideoGenError):
    """Raised when configuration is missing or invalid."""

    pass


class AuthenticationError(SipVideoGenError):
    """Raised when API authentication fails."""

    pass


class APIError(SipVideoGenError):
    """Base class for API-related errors."""

    pass


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded."""

    pass


class QuotaExceededError(APIError):
    """Raised when API quota is exhausted."""

    pass


class ValidationError(SipVideoGenError):
    """Raised when input validation fails."""

    pass


class PipelineError(SipVideoGenError):
    """Raised when the video generation pipeline fails."""

    pass


class BrandNotFoundError(SipVideoGenError, ValueError):
    """Raised when a brand doesn't exist."""

    pass


class ProductNotFoundError(SipVideoGenError, ValueError):
    """Raised when a product doesn't exist."""

    pass


class ProjectNotFoundError(SipVideoGenError, ValueError):
    """Raised when a project doesn't exist."""

    pass


class StyleReferenceNotFoundError(SipVideoGenError, ValueError):
    """Raised when a style reference doesn't exist."""

    pass


class StorageError(SipVideoGenError, ValueError):
    """Raised when storage operations fail."""

    pass


class DuplicateEntityError(SipVideoGenError, ValueError):
    """Raised when creating an entity that already exists."""

    pass
