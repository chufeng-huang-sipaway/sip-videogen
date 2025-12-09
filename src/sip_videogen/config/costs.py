"""Cost estimation for video generation.

This module provides cost estimates for various AI services used in the pipeline.
Costs are approximate and may change over time based on provider pricing.
"""

from dataclasses import dataclass

from ..models import VideoScript


@dataclass
class CostEstimate:
    """Estimated costs for video generation."""

    # Image generation costs
    image_count: int
    image_cost_per_unit: float
    image_total: float

    # Video generation costs
    video_count: int
    video_duration_seconds: int
    video_cost_per_second: float
    video_total: float

    # Total
    total_min: float
    total_max: float

    def format_summary(self) -> str:
        """Format cost estimate as a human-readable summary."""
        lines = [
            f"Image Generation ({self.image_count} images):",
            f"  ~${self.image_total:.2f}",
            f"",
            f"Video Generation ({self.video_count} clips, {self.video_duration_seconds}s total):",
            f"  ~${self.video_total:.2f}",
            f"",
            f"Estimated Total: ${self.total_min:.2f} - ${self.total_max:.2f}",
        ]
        return "\n".join(lines)


# Pricing constants (as of Dec 2024)
# These are approximate and may change
GEMINI_IMAGE_COST_MIN = 0.02  # Gemini 2.0 Flash image generation
GEMINI_IMAGE_COST_MAX = 0.13  # Higher quality models

# VEO 3.1 pricing via Vertex AI (approximate)
# https://cloud.google.com/vertex-ai/generative-ai/pricing
VEO_COST_PER_SECOND_MIN = 0.08  # Lower estimate
VEO_COST_PER_SECOND_MAX = 0.15  # Higher estimate

# OpenAI API costs for agent orchestration (negligible compared to media generation)
OPENAI_AGENT_COST_ESTIMATE = 0.10  # Rough estimate for script development


def estimate_costs(
    script: VideoScript | None = None,
    num_scenes: int | None = None,
    num_shared_elements: int | None = None,
    video_duration_per_scene: int = 8,
) -> CostEstimate:
    """Estimate the cost of generating a video.

    Can be called with either a VideoScript or with explicit counts.

    Args:
        script: Optional VideoScript to calculate costs from.
        num_scenes: Number of scenes (used if script not provided).
        num_shared_elements: Number of shared elements (used if script not provided).
        video_duration_per_scene: Duration per scene in seconds.

    Returns:
        CostEstimate with breakdown and totals.
    """
    if script:
        image_count = len(script.shared_elements)
        video_count = len(script.scenes)
        total_video_duration = script.total_duration
    else:
        image_count = num_shared_elements or 3  # Default estimate
        video_count = num_scenes or 3
        total_video_duration = video_count * video_duration_per_scene

    # Calculate image costs
    # Using average between min and max for display
    image_cost_per_unit = (GEMINI_IMAGE_COST_MIN + GEMINI_IMAGE_COST_MAX) / 2
    image_total = image_count * image_cost_per_unit

    # Calculate video costs
    video_cost_per_second = (VEO_COST_PER_SECOND_MIN + VEO_COST_PER_SECOND_MAX) / 2
    video_total = total_video_duration * video_cost_per_second

    # Calculate total range
    total_min = (
        image_count * GEMINI_IMAGE_COST_MIN
        + total_video_duration * VEO_COST_PER_SECOND_MIN
        + OPENAI_AGENT_COST_ESTIMATE
    )
    total_max = (
        image_count * GEMINI_IMAGE_COST_MAX
        + total_video_duration * VEO_COST_PER_SECOND_MAX
        + OPENAI_AGENT_COST_ESTIMATE
    )

    return CostEstimate(
        image_count=image_count,
        image_cost_per_unit=image_cost_per_unit,
        image_total=image_total,
        video_count=video_count,
        video_duration_seconds=total_video_duration,
        video_cost_per_second=video_cost_per_second,
        video_total=video_total,
        total_min=total_min,
        total_max=total_max,
    )


def estimate_pre_generation_costs(
    num_scenes: int,
    estimated_shared_elements: int = 3,
    video_duration_per_scene: int = 8,
) -> CostEstimate:
    """Estimate costs before script generation.

    This provides a rough estimate before the AI agents run,
    based on the number of scenes requested.

    Args:
        num_scenes: Number of scenes to generate.
        estimated_shared_elements: Estimated number of shared elements.
        video_duration_per_scene: Expected duration per scene.

    Returns:
        CostEstimate with breakdown and totals.
    """
    return estimate_costs(
        num_scenes=num_scenes,
        num_shared_elements=estimated_shared_elements,
        video_duration_per_scene=video_duration_per_scene,
    )
