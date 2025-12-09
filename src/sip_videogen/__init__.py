"""SIP VideoGen - Transform vague video ideas into complete videos using an AI agent team."""

from sip_videogen.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    PipelineError,
    QuotaExceededError,
    RateLimitError,
    SipVideoGenError,
    ValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "SipVideoGenError",
    "ConfigurationError",
    "AuthenticationError",
    "APIError",
    "RateLimitError",
    "QuotaExceededError",
    "ValidationError",
    "PipelineError",
]
