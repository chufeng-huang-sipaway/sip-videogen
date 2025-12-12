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
