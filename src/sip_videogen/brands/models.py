"""Data models for brand identity and memory.

This module defines the hierarchical brand identity models:
- BrandSummary: L0 layer, always in agent context (~500 tokens)
- BrandIdentityFull: L1 layer, loaded on demand
- Supporting models for visual identity, voice, audience, positioning
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class BrandSummary(BaseModel):
    """Compact brand summary - always present in agent context.

    This is the L0 layer of brand memory. Keep it under ~500 tokens.
    Includes pointers to deeper layers so agents know what else exists.
    """

    # Core Identity (required)
    slug: str = Field(description="URL-safe identifier, e.g., 'summit-coffee'")
    name: str = Field(description="Official brand name, e.g., 'Summit Coffee Co.'")
    tagline: str = Field(description="One-line positioning statement")
    category: str = Field(description="Product category, e.g., 'Coffee', 'Skincare'")
    tone: str = Field(description="2-3 adjectives describing brand personality")

    # Visual Essence (condensed)
    primary_colors: List[str] = Field(
        default_factory=list,
        description="Up to 3 hex color codes, e.g., ['#2C3E50', '#8B7355']",
    )
    visual_style: str = Field(
        default="",
        description="One sentence describing visual direction",
    )
    logo_path: str = Field(
        default="",
        description="Path to primary logo file (empty string if none)",
    )

    # Audience Essence
    audience_summary: str = Field(
        default="",
        description="One sentence describing target audience",
    )

    # Memory Pointers (tells agents what details exist)
    available_details: List[str] = Field(
        default_factory=lambda: [
            "visual_identity",
            "voice_guidelines",
            "audience_profile",
            "positioning",
        ],
        description="List of detail types available via fetch_brand_detail()",
    )
    asset_count: int = Field(
        default=0,
        description="Total number of generated assets",
    )
    last_generation: str = Field(
        default="",
        description="ISO timestamp of last asset generation (empty if never)",
    )

    # Instruction for agents
    exploration_hint: str = Field(
        default=(
            "Use fetch_brand_detail() to access full visual identity, "
            "voice guidelines, audience profile, or positioning before making "
            "creative decisions."
        ),
        description="Hint text included in agent context",
    )


# =============================================================================
# Supporting Models for BrandIdentityFull (L1 Layer)
# =============================================================================


class ColorDefinition(BaseModel):
    """Single color in the brand palette."""

    hex: str = Field(description="Hex color code, e.g., '#2C3E50'")
    name: str = Field(description="Human-readable name, e.g., 'Ocean Blue'")
    usage: str = Field(
        default="",
        description="When to use this color, e.g., 'Primary backgrounds'",
    )


class TypographyRule(BaseModel):
    """Typography specification for a specific use case."""

    role: str = Field(description="Where used: 'headings', 'body', 'accent'")
    family: str = Field(description="Font family name, e.g., 'Inter'")
    weight: str = Field(default="regular", description="Font weight")
    style_notes: str = Field(
        default="",
        description="Additional guidance, e.g., 'Use for emphasis only'",
    )


class VisualIdentity(BaseModel):
    """Complete visual design system for the brand."""

    # Colors
    primary_colors: List[ColorDefinition] = Field(
        default_factory=list,
        description="Main brand colors (1-3)",
    )
    secondary_colors: List[ColorDefinition] = Field(
        default_factory=list,
        description="Supporting colors",
    )
    accent_colors: List[ColorDefinition] = Field(
        default_factory=list,
        description="Highlight/accent colors",
    )

    # Typography
    typography: List[TypographyRule] = Field(
        default_factory=list,
        description="Typography rules by use case",
    )

    # Imagery
    imagery_style: str = Field(
        default="",
        description="Photography/illustration style description",
    )
    imagery_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords for image generation, e.g., ['warm', 'natural light']",
    )
    imagery_avoid: List[str] = Field(
        default_factory=list,
        description="What to avoid in imagery",
    )

    # Materials & Textures
    materials: List[str] = Field(
        default_factory=list,
        description="Materials to feature, e.g., ['matte paper', 'brushed metal']",
    )

    # Logo
    logo_description: str = Field(
        default="",
        description="Description of the logo design",
    )
    logo_usage_rules: str = Field(
        default="",
        description="Rules for logo usage, e.g., minimum size, clear space",
    )

    # Overall
    overall_aesthetic: str = Field(
        default="",
        description="One paragraph describing the unified visual language",
    )
    style_keywords: List[str] = Field(
        default_factory=list,
        description="Style anchors, e.g., ['minimalist', 'premium', 'organic']",
    )


class VoiceGuidelines(BaseModel):
    """Brand voice and messaging guidelines."""

    personality: str = Field(
        default="",
        description="How the brand 'speaks' - personality description",
    )
    tone_attributes: List[str] = Field(
        default_factory=list,
        description="3-5 adjectives defining voice, e.g., ['warm', 'professional']",
    )

    # Messaging
    key_messages: List[str] = Field(
        default_factory=list,
        description="Core talking points",
    )
    messaging_do: List[str] = Field(
        default_factory=list,
        description="Messaging guidelines - what TO do",
    )
    messaging_dont: List[str] = Field(
        default_factory=list,
        description="Messaging guidelines - what NOT to do",
    )

    # Examples
    example_headlines: List[str] = Field(
        default_factory=list,
        description="Sample headlines in brand voice",
    )
    example_taglines: List[str] = Field(
        default_factory=list,
        description="Sample taglines in brand voice",
    )


class AudienceProfile(BaseModel):
    """Target audience definition."""

    primary_summary: str = Field(
        default="",
        description="One sentence audience description",
    )

    # Demographics
    age_range: str = Field(default="", description="Target age range")
    gender: str = Field(default="", description="Target gender if relevant")
    income_level: str = Field(default="", description="Income bracket if relevant")
    location: str = Field(default="", description="Geographic focus if relevant")

    # Psychographics
    interests: List[str] = Field(
        default_factory=list,
        description="Hobbies and interests",
    )
    values: List[str] = Field(
        default_factory=list,
        description="What they value",
    )
    lifestyle: str = Field(default="", description="Lifestyle description")

    # Pain Points & Desires
    pain_points: List[str] = Field(
        default_factory=list,
        description="Problems they face",
    )
    desires: List[str] = Field(
        default_factory=list,
        description="What they want to achieve",
    )


class CompetitivePositioning(BaseModel):
    """Market positioning and differentiation."""

    market_category: str = Field(
        default="",
        description="Market category the brand operates in",
    )
    unique_value_proposition: str = Field(
        default="",
        description="What makes this brand uniquely valuable",
    )

    # Competitors
    primary_competitors: List[str] = Field(
        default_factory=list,
        description="Main competitor names",
    )
    differentiation: str = Field(
        default="",
        description="How we're different from competitors",
    )

    # Positioning Statement
    positioning_statement: str = Field(
        default="",
        description="Formal positioning: '[Brand] is the [category] for [audience] who [need] because [reason]'",
    )
