"""Core script models for video generation.

This module defines the data structures that represent the video script,
including shared visual elements and scene actions.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .music import MusicBrief

# Valid shot durations in seconds (2-second increments only)
ShotDuration = Literal[2, 4, 6, 8]

# Type alias for clip patterns (tuple of shot durations summing to 8)
ClipPattern = tuple[ShotDuration, ...]

# Exhaustive list of valid 8-second clip patterns
# These are the only patterns agents can use - guarantees math always works
VALID_CLIP_PATTERNS: list[ClipPattern] = [
    (8,),  # Single continuous shot
    (6, 2),  # Long + quick
    (2, 6),  # Quick + long
    (4, 4),  # Two equal
    (4, 2, 2),  # Medium + two quick
    (2, 4, 2),  # Quick + medium + quick
    (2, 2, 4),  # Two quick + medium
    (2, 2, 2, 2),  # Four quick shots
]

# Pattern name mapping for agent communication
PATTERN_NAMES: dict[ClipPattern, str] = {
    (8,): "single_continuous",
    (6, 2): "long_quick",
    (2, 6): "quick_long",
    (4, 4): "two_equal",
    (4, 2, 2): "medium_two_quick",
    (2, 4, 2): "quick_medium_quick",
    (2, 2, 4): "two_quick_medium",
    (2, 2, 2, 2): "four_quick",
}


class ElementType(str, Enum):
    """Type of visual element that needs consistency across scenes."""

    CHARACTER = "character"
    ENVIRONMENT = "environment"
    PROP = "prop"


class SharedElement(BaseModel):
    """An element that must be visually consistent across scenes.

    Shared elements are recurring visual components (characters, props, environments)
    that appear in multiple scenes and need reference images for consistency.

    Note: All fields use empty strings instead of None for OpenAI structured output compatibility.
    """

    id: str = Field(description="Unique identifier, e.g., 'char_protagonist'")
    element_type: ElementType = Field(description="Type of visual element")
    name: str = Field(description="Human-readable name for the element")
    visual_description: str = Field(description="Detailed description for image generation")
    role_descriptor: str = Field(
        default="",
        description="Short role-based label for video prompts (e.g., 'the vendor'). "
        "Links characters to reference images without repeating appearance details.",
    )
    appears_in_scenes: list[int] = Field(
        description="List of scene numbers where this element appears"
    )
    reference_image_path: str = Field(
        default="",
        description="Local path to generated reference image (empty if not yet generated)",
    )
    reference_image_gcs_uri: str = Field(
        default="", description="GCS URI of uploaded reference image (empty if not yet uploaded)"
    )


class SubShot(BaseModel):
    """A single shot within a timestamp-prompted scene.

    SubShots allow multiple camera angles/shots within a single 8-second VEO clip
    using timestamp prompting. This is the recommended way to create rhythm and
    shot variety since VEO forces 8-second clips when using reference images.

    Example timestamp prompt output:
    [00:00-00:02] Wide establishing shot of food truck
    [00:02-00:04] Medium shot, vendor prepares ingredients
    [00:04-00:06] Close-up of sizzling grill
    [00:06-00:08] Medium shot, vendor plates the food
    """

    start_second: int = Field(ge=0, le=6, description="Start time in seconds (0, 2, 4, or 6)")
    end_second: int = Field(ge=2, le=8, description="End time in seconds (2, 4, 6, or 8)")
    camera_direction: str = Field(description="Shot composition and camera movement")
    action_description: str = Field(description="What happens during this sub-shot")
    dialogue: str = Field(default="", description="Dialogue during this sub-shot (if any)")


class SceneAction(BaseModel):
    """What happens in a single scene.

    Each scene represents a segment of the final video with its own
    action, setting, and optional dialogue.

    Note: All fields use empty strings instead of None for OpenAI structured output compatibility.
    """

    scene_number: int = Field(ge=1, description="Sequential scene number starting at 1")
    duration_seconds: int = Field(
        default=8,
        ge=4,
        le=8,
        description="Clip duration in seconds. VEO forces 8s with reference images.",
    )
    clip_pattern: list[int] = Field(
        default_factory=lambda: [8],
        description="Shot duration pattern for this clip. Must be a valid pattern "
        "from VALID_CLIP_PATTERNS (e.g., [8], [4, 4], [2, 2, 2, 2]). "
        "Durations must sum to 8 and use only 2, 4, 6, or 8 second increments.",
    )
    setting_description: str = Field(description="Description of the scene's location/environment")
    action_description: str = Field(
        description="What happens in the scene, suitable for AI video generation"
    )
    dialogue: str = Field(default="", description="Spoken dialogue (empty string if none)")
    camera_direction: str = Field(
        default="", description="Camera movement or framing instructions (empty string if none)"
    )
    visual_notes: str = Field(
        default="",
        description="Scene-specific visual notes that adjust the global visual style",
    )
    shared_element_ids: list[str] = Field(
        default_factory=list,
        description="IDs of shared elements appearing in this scene",
    )
    sub_shots: list[SubShot] = Field(
        default_factory=list,
        description="Optional list of sub-shots for timestamp prompting. "
        "Creates multi-shot sequences within the 8-second clip for rhythm/variety.",
    )

    @model_validator(mode="after")
    def validate_clip_pattern_and_sub_shots(self) -> "SceneAction":
        """Validate that clip_pattern is valid and sub_shots match the pattern."""
        pattern = tuple(self.clip_pattern)

        # Validate pattern is in allowed list
        if pattern not in VALID_CLIP_PATTERNS:
            raise ValueError(
                f"Invalid clip pattern {self.clip_pattern}. "
                f"Must be one of: {[list(p) for p in VALID_CLIP_PATTERNS]}"
            )

        # Validate pattern sums to 8 (should always be true for valid patterns)
        if sum(self.clip_pattern) != 8:
            raise ValueError(
                f"Clip pattern durations must sum to 8, got {sum(self.clip_pattern)}"
            )

        # If sub_shots are provided, validate they match the pattern
        if self.sub_shots:
            if len(self.sub_shots) != len(self.clip_pattern):
                raise ValueError(
                    f"Number of sub_shots ({len(self.sub_shots)}) must match "
                    f"clip_pattern length ({len(self.clip_pattern)})"
                )

            # Validate each sub_shot duration matches pattern
            expected_start = 0
            for i, (sub_shot, expected_duration) in enumerate(
                zip(self.sub_shots, self.clip_pattern)
            ):
                actual_duration = sub_shot.end_second - sub_shot.start_second
                if actual_duration != expected_duration:
                    raise ValueError(
                        f"Sub-shot {i + 1} duration ({actual_duration}s) doesn't match "
                        f"pattern ({expected_duration}s)"
                    )
                if sub_shot.start_second != expected_start:
                    raise ValueError(
                        f"Sub-shot {i + 1} start ({sub_shot.start_second}s) should be "
                        f"{expected_start}s based on pattern"
                    )
                expected_start += expected_duration

        return self


class VideoScript(BaseModel):
    """Complete script for video generation.

    This is the final output of the agent team, containing all information
    needed to generate reference images and video clips.
    """

    title: str = Field(description="Title of the video")
    logline: str = Field(description="One-sentence summary of the video")
    tone: str = Field(description="Overall mood/style of the video")
    visual_style: str = Field(
        default="",
        description="Global visual aesthetic: color palette, lighting, camera, treatment.",
    )
    shared_elements: list[SharedElement] = Field(
        default_factory=list, description="Visual elements needing consistency"
    )
    scenes: list[SceneAction] = Field(description="Ordered list of scenes")
    music_brief: MusicBrief = Field(description="Background music style from Music Director agent")

    @property
    def total_duration(self) -> int:
        """Calculate the total duration of all scenes in seconds."""
        return sum(scene.duration_seconds for scene in self.scenes)

    def get_element_by_id(self, element_id: str) -> SharedElement | None:
        """Find a shared element by its ID.

        Args:
            element_id: The unique identifier of the element.

        Returns:
            The SharedElement if found, None otherwise.
        """
        for element in self.shared_elements:
            if element.id == element_id:
                return element
        return None

    def get_elements_for_scene(self, scene_number: int) -> list[SharedElement]:
        """Get all shared elements that appear in a specific scene.

        Args:
            scene_number: The scene number to look up.

        Returns:
            List of SharedElements appearing in that scene.
        """
        return [
            element for element in self.shared_elements if scene_number in element.appears_in_scenes
        ]
