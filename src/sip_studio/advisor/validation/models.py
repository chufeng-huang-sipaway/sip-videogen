"""Result models for validation."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


class ReferenceValidationResult(BaseModel):
    """Result of validating generated image against reference."""

    is_identical: bool = Field(
        description="Whether the object in generated image is identical to reference"
    )
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Similarity score from 0.0 (completely different) to 1.0 (identical)",
    )
    reasoning: str = Field(description="Explanation of the assessment")
    improvement_suggestions: str = Field(
        default="", description="If not identical, suggestions to improve the generation prompt"
    )
    # Phase 3: Proportion validation
    proportions_match: bool = Field(
        default=True,
        description="Whether the object proportions match the reference (height:width ratio)",
    )
    proportions_notes: str = Field(
        default="", description="Notes about proportion accuracy - squashed, stretched, or correct"
    )


class ProductValidationResult(BaseModel):
    """Result of validating a single product within a multi-product image."""

    product_name: str = Field(description="Name of the product being validated")
    is_present: bool = Field(description="Whether this product is visible in the generated image")
    is_accurate: bool = Field(description="Whether this product's appearance matches the reference")
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Similarity score from 0.0 (completely different) to 1.0 (identical)",
    )
    issues: str = Field(
        default="", description="Specific issues found (wrong material, color mismatch, etc.)"
    )
    # Phase 3: Proportion validation
    proportions_match: bool = Field(
        default=True, description="Whether this product's proportions match the reference"
    )
    proportions_notes: str = Field(
        default="", description="Notes about proportion accuracy for this product"
    )


class MultiProductValidationResult(BaseModel):
    """Result of validating multiple products in a single generated image."""

    product_results: list[ProductValidationResult] = Field(
        description="Validation results for each individual product"
    )
    all_products_present: bool = Field(
        description="Whether ALL products are visible in the generated image"
    )
    all_products_accurate: bool = Field(
        description="Whether ALL products accurately match their references"
    )
    overall_score: float = Field(
        ge=0.0, le=1.0, description="Average similarity score across all products"
    )
    suggestions: str = Field(
        default="", description="Overall improvement suggestions for the generation prompt"
    )
    # Phase 3: Proportion validation
    all_proportions_match: bool = Field(
        default=True, description="Whether ALL products have correct proportions"
    )


@dataclass
class ValidationAttempt:
    """Record of a single generation + validation attempt."""

    attempt_number: int
    prompt_used: str
    image_path: str
    similarity_score: float
    is_identical: bool
    improvement_suggestions: str


@dataclass
class ValidationGenerationResult:
    """Result of a reference-validated image generation run."""

    path: str
    attempts: list[dict]
    final_prompt: str
    final_attempt_number: int
    validation_passed: bool
    warning: str | None = None


@dataclass
class MultiValidationAttempt:
    """Record of a single multi-product generation + validation attempt."""

    attempt_number: int
    prompt_used: str
    image_path: str
    overall_score: float
    all_accurate: bool
    product_scores: dict[str, float]  # product_name -> score
    suggestions: str


@dataclass
class MultiValidationGenerationResult:
    """Result of a multi-product validated image generation run."""

    path: str
    attempts: list[dict]
    final_prompt: str
    final_attempt_number: int
    validation_passed: bool
    warning: str | None = None


def _validation_model_dump(model: BaseModel) -> dict:
    """Return a JSON-serializable dict from a pydantic model."""
    return model.model_dump()
