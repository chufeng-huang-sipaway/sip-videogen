"""Output models for brand management agents.

This module defines the structured output types for each agent in the
brand management orchestration pipeline. These models are used with
OpenAI Agents SDK's `output_type` parameter for structured responses.

Agent Team:
- Brand Strategist: Develops core identity, audience, and positioning
- Visual Identity Designer: Creates the visual design system
- Brand Voice Writer: Establishes voice and messaging guidelines
- Brand Guardian: Validates consistency before generation
- Brand Director: Orchestrates the team and produces final identity
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from sip_videogen.brands.models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIdentityFull,
    CompetitivePositioning,
    VisualIdentity,
    VoiceGuidelines,
)


class BrandStrategyOutput(BaseModel):
    """Output from Brand Strategist agent.

    Contains the strategic foundation: core identity, target audience,
    and market positioning. This forms the basis for all other brand work.
    """

    core_identity: BrandCoreIdentity = Field(
        description="Core brand identity: name, mission, story, values"
    )
    audience_profile: AudienceProfile = Field(
        description="Target audience definition with demographics and psychographics"
    )
    positioning: CompetitivePositioning = Field(
        description="Market positioning and competitive differentiation"
    )
    strategy_notes: str = Field(
        default="",
        description="Additional strategic considerations and rationale",
    )


class VisualIdentityOutput(BaseModel):
    """Output from Visual Identity Designer agent.

    Contains the complete visual design system including colors,
    typography, imagery guidelines, and logo brief.
    """

    visual_identity: VisualIdentity = Field(description="Complete visual design system")
    design_rationale: str = Field(
        default="",
        description="Explanation of design choices and how they connect to brand strategy",
    )
    logo_brief: str = Field(
        default="",
        description="Detailed brief for logo generation, including style and symbolism",
    )


class BrandVoiceOutput(BaseModel):
    """Output from Brand Voice Writer agent.

    Contains voice and messaging guidelines with example copy
    demonstrating the brand voice in action.
    """

    voice_guidelines: VoiceGuidelines = Field(
        description="Voice and messaging guidelines with do's and don'ts"
    )
    sample_copy: List[str] = Field(
        default_factory=list,
        description="Example copy demonstrating the brand voice (3-5 samples)",
    )
    voice_rationale: str = Field(
        default="",
        description="Explanation of voice choices and how they serve the audience",
    )


class BrandValidationIssue(BaseModel):
    """Single validation issue identified by Brand Guardian.

    Represents a consistency or quality concern that should be
    addressed before finalizing the brand identity.
    """

    category: str = Field(
        description="Issue category: 'visual', 'voice', 'strategy', 'consistency'"
    )
    severity: str = Field(description="Issue severity: 'error', 'warning', 'suggestion'")
    description: str = Field(description="Clear description of what the issue is")
    recommendation: str = Field(
        description="Actionable recommendation for how to resolve the issue"
    )


class BrandGuardianOutput(BaseModel):
    """Output from Brand Guardian agent.

    Contains the validation results including pass/fail status,
    specific issues found, and an overall consistency score.
    """

    is_valid: bool = Field(description="Whether the brand identity passes validation (no errors)")
    issues: List[BrandValidationIssue] = Field(
        default_factory=list,
        description="List of issues found during validation",
    )
    consistency_score: float = Field(
        default=1.0,
        description="Overall brand consistency score from 0.0 to 1.0",
    )
    validation_notes: str = Field(
        default="",
        description="Summary of validation findings and overall assessment",
    )


class BrandDirectorOutput(BaseModel):
    """Output from Brand Director orchestrator agent.

    Contains the complete brand identity after coordination with
    all specialist agents and validation by Brand Guardian.
    """

    brand_identity: BrandIdentityFull = Field(description="Complete brand identity ready for use")
    creative_rationale: str = Field(
        default="",
        description="Summary of key creative decisions made during development",
    )
    validation_passed: bool = Field(
        default=True,
        description="Whether Brand Guardian validation passed",
    )
    next_steps: List[str] = Field(
        default_factory=list,
        description="Recommended next steps for brand development (2-4 items)",
    )
