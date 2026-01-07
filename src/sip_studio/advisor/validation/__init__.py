"""Validation module - backward compatible re-exports."""

from .generator import generate_with_multi_validation, generate_with_validation
from .metrics import GenerationMetrics, ProductMetric
from .models import (
    MultiProductValidationResult,
    MultiValidationAttempt,
    MultiValidationGenerationResult,
    ProductValidationResult,
    ReferenceValidationResult,
    ValidationAttempt,
    ValidationGenerationResult,
)
from .prompts import _improve_prompt_for_identity  # Used by tests
from .validator import validate_multi_product_identity, validate_reference_identity

__all__ = [
    # Public async functions
    "generate_with_validation",
    "generate_with_multi_validation",
    "validate_reference_identity",
    "validate_multi_product_identity",
    # Public models
    "GenerationMetrics",
    "ProductMetric",
    "MultiProductValidationResult",
    "MultiValidationAttempt",
    "MultiValidationGenerationResult",
    "ProductValidationResult",
    "ReferenceValidationResult",
    "ValidationAttempt",
    "ValidationGenerationResult",
    # Test compatibility (private but imported by tests)
    "_improve_prompt_for_identity",
]
