"""Core script models for video generation.

This module defines the data structures that represent the video script,
including shared visual elements and scene actions.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from .music import MusicBrief


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


class SceneAction(BaseModel):
    """What happens in a single scene.

    Each scene represents a segment of the final video with its own
    action, setting, and optional dialogue.

    Note: All fields use empty strings instead of None for OpenAI structured output compatibility.
    """

    scene_number: int = Field(ge=1, description="Sequential scene number starting at 1")
    duration_seconds: int = Field(
        default=6,
        ge=4,
        le=8,
        description="Target clip duration (4, 6, or 8s). VEO generates 8s, clips are trimmed to this duration.",
    )
    setting_description: str = Field(description="Description of the scene's location/environment")
    action_description: str = Field(
        description="What happens in the scene, suitable for AI video generation"
    )
    dialogue: str = Field(default="", description="Spoken dialogue (empty string if none)")
    camera_direction: str = Field(
        default="", description="Camera movement or framing instructions (empty string if none)"
    )
    shared_element_ids: list[str] = Field(
        default_factory=list,
        description="IDs of shared elements appearing in this scene",
    )


class VideoScript(BaseModel):
    """Complete script for video generation.

    This is the final output of the agent team, containing all information
    needed to generate reference images and video clips.
    """

    title: str = Field(description="Title of the video")
    logline: str = Field(description="One-sentence summary of the video")
    tone: str = Field(description="Overall mood/style of the video")
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
