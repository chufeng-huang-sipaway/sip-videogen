"""Models for image review and quality control.

This module defines data structures for the image review process,
including review decisions and feedback for prompt improvement.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ReviewDecision(str, Enum):
    """Decision outcome of an image review."""

    ACCEPT = "accept"
    REJECT = "reject"


class ImageReviewResult(BaseModel):
    """Result of reviewing a generated reference image.

    This model captures the outcome of the Image Reviewer agent's
    evaluation of a generated reference image.
    """

    decision: ReviewDecision = Field(description="Whether to accept or reject the image")
    element_id: str = Field(description="ID of the shared element being reviewed")
    reasoning: str = Field(description="Explanation for the accept/reject decision")
    improvement_suggestions: str = Field(
        default="",
        description="If rejected, specific suggestions to improve the generation prompt",
    )


class ImageGenerationAttempt(BaseModel):
    """Record of a single image generation attempt.

    Tracks the prompt used and the outcome (success or rejection reason).
    """

    attempt_number: int = Field(ge=1, description="Attempt number (1-indexed)")
    prompt_used: str = Field(description="The prompt/description used for generation")
    outcome: Literal["success", "rejected", "error"] = Field(description="Outcome of this attempt")
    rejection_reason: str = Field(
        default="", description="If rejected, the reason from the reviewer"
    )
    error_message: str = Field(default="", description="If error, the error message")


class ImageGenerationResult(BaseModel):
    """Final result of generating a reference image with review loop.

    Captures the complete generation process including all attempts
    and the final outcome.
    """

    element_id: str = Field(description="ID of the shared element")
    status: Literal["success", "fallback", "failed"] = Field(
        description="Final status: success, fallback (kept despite rejection), or failed"
    )
    local_path: str = Field(
        default="", description="Path to the generated image (if success or fallback)"
    )
    attempts: list[ImageGenerationAttempt] = Field(
        default_factory=list, description="Record of all generation attempts"
    )
    final_prompt: str = Field(
        default="", description="The prompt that produced the final accepted image"
    )

    @property
    def total_attempts(self) -> int:
        """Return the total number of generation attempts."""
        return len(self.attempts)
