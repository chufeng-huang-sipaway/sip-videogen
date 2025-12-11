"""Agent output models for structured responses.

This module defines the structured output types for each agent in the
orchestration pipeline. These models are used with OpenAI Agents SDK's
`output_type` parameter for structured responses.
"""

from pydantic import BaseModel, Field

from sip_videogen.models.music import MusicBrief
from sip_videogen.models.script import SceneAction, SharedElement, VideoScript


class ScreenwriterOutput(BaseModel):
    """Output from the Screenwriter agent.

    Contains the scene breakdown with narrative arc, action descriptions,
    dialogue, and timing information.
    """

    scenes: list[SceneAction] = Field(
        description="Ordered list of scenes with action descriptions and timing"
    )
    narrative_notes: str | None = Field(
        default=None,
        description="Notes about the narrative arc and creative choices",
    )


class ProductionDesignerOutput(BaseModel):
    """Output from the Production Designer agent.

    Contains the shared visual elements that need consistency across scenes,
    with detailed descriptions for image generation.
    """

    shared_elements: list[SharedElement] = Field(
        description="Visual elements requiring consistency across scenes"
    )
    design_notes: str | None = Field(
        default=None,
        description="Notes about the visual style and design choices",
    )


class ContinuityIssue(BaseModel):
    """A continuity issue found during validation."""

    scene_number: int = Field(description="Scene where the issue occurs")
    element_id: str | None = Field(
        default=None, description="Related shared element ID, if applicable"
    )
    issue_description: str = Field(description="Description of the continuity issue")
    resolution: str = Field(description="How the issue was resolved or should be resolved")


class ContinuitySupervisorOutput(BaseModel):
    """Output from the Continuity Supervisor agent.

    Contains the validated and optimized script, along with any issues
    found and resolutions applied.
    """

    validated_script: VideoScript = Field(
        description="The complete validated script with optimized prompts"
    )
    issues_found: list[ContinuityIssue] = Field(
        default_factory=list,
        description="Continuity issues identified during validation",
    )
    optimization_notes: str | None = Field(
        default=None,
        description="Notes about prompt optimizations made for AI generation",
    )


class ShowrunnerOutput(BaseModel):
    """Output from the Showrunner orchestrator agent.

    This is the final output containing the complete VideoScript
    ready for image and video generation.
    """

    script: VideoScript = Field(description="The complete video script ready for production")
    music_brief: MusicBrief | None = Field(
        default=None,
        description="Background music style from Music Director agent",
    )
    creative_brief: str | None = Field(
        default=None,
        description="Summary of the creative vision and key decisions",
    )
    production_ready: bool = Field(
        default=True,
        description="Whether the script is ready for production",
    )


class PromptRepairOutput(BaseModel):
    """Output from the Prompt Repair agent.

    Contains the revised scene description that avoids policy violations
    while maintaining the narrative intent.
    """

    revised_action_description: str = Field(
        description="The revised action description that avoids policy violations"
    )
    revised_setting_description: str = Field(
        description="The revised setting description if changes were needed"
    )
    changes_made: str = Field(
        description="Brief explanation of what was changed and why"
    )


class DirectorsPitch(BaseModel):
    """Quick pitch proposal from Showrunner before full generation.

    This lightweight output is used for user approval before committing
    to full script development. It captures the creative vision without
    the detailed scene breakdown.
    """

    title: str = Field(
        description="Proposed title for the video (2-5 words)"
    )
    logline: str = Field(
        description="One-sentence hook that sells the concept"
    )
    tone: str = Field(
        description="Overall mood and style (2-3 adjectives)"
    )
    scene_count: int = Field(
        description="Planned number of scenes based on target duration"
    )
    estimated_duration: int = Field(
        description="Estimated total duration in seconds"
    )
    brief_description: str = Field(
        description="2-3 sentence overview of the planned narrative"
    )
    key_elements: list[str] = Field(
        default_factory=list,
        description="Main visual elements/characters planned (3-5 items)"
    )
