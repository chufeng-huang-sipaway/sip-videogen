"""Visual Directive Generator - translates brand identity into visual rules."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

from agents import Agent, Runner
from pydantic import BaseModel, Field

from .models import (
    BrandIdentityFull,
    ColorGuidelines,
    MoodGuidelines,
    PhotographyStyle,
    TargetRepresentation,
    VisualDirective,
)
from .storage import load_visual_directive, save_visual_directive

logger = logging.getLogger(__name__)


# Intermediate output model for the agent
class VisualDirectiveOutput(BaseModel):
    """Output model for the Visual Directive Generator agent."""

    target_representation: TargetRepresentation = Field(
        description="Who should appear in lifestyle/marketing images"
    )
    color_guidelines: ColorGuidelines = Field(description="Color direction for image generation")
    mood_guidelines: MoodGuidelines = Field(description="Emotional atmosphere for images")
    photography_style: PhotographyStyle = Field(description="Photography/visual style guidelines")
    always_include: list[str] = Field(
        default_factory=list, description="Elements to always include"
    )
    never_include: list[str] = Field(default_factory=list, description="Elements to never include")


# noqa: E501 - Long lines in multiline strings are acceptable for prompts
GENERATOR_INSTRUCTIONS = """\
You are a Visual Directive Generator. Your job is to analyze a brand identity \
and extract visual rules specifically for image generation.

## Your Task
Given a brand identity, extract and translate it into concrete visual rules \
that an image generation AI can follow.

## Key Extractions

### 1. Target Representation
From the audience profile, extract:
- WHO should appear in lifestyle/marketing images (age, style, appearance)
- What to AVOID in subject representation

### 2. Color Guidelines
From the visual identity, extract:
- Primary colors to emphasize (use the brand's hex codes)
- Color temperature preference (warm/cool/neutral)
- Saturation level (vibrant/muted/natural)
- Colors to explicitly avoid

### 3. Mood Guidelines
From the brand personality and voice:
- Primary emotional quality the images should convey
- Lighting preferences that match the brand mood
- Environmental atmosphere

### 4. Photography Style
From imagery style and keywords:
- Overall photography style description
- Composition preferences
- Materials/textures to feature
- Depth of field preferences

### 5. Hard Rules
- always_include: Things that MUST appear or be true in every image
- never_include: Things that should NEVER appear (hard constraints)

## Important Guidelines
- Be SPECIFIC and ACTIONABLE - vague rules don't help image generation
- Focus on VISUAL elements, not messaging or voice
- Translate abstract brand values into concrete visual direction
- Consider the target audience when defining who should appear in images
- Keep lists concise (3-7 items max per list)
"""

_generator_agent = Agent(
    name="Visual Directive Generator",
    instructions=GENERATOR_INSTRUCTIONS,
    output_type=VisualDirectiveOutput,
    model="gpt-4.1-mini",
)


def _fmt(items: list, fallback: str = "Not specified") -> str:
    """Format list items or return fallback."""
    return ", ".join(items) if items else fallback


def _fmt_colors(colors: list) -> str:
    """Format color definitions."""
    if not colors:
        return "Not specified"
    return ", ".join([f"{c.name} ({c.hex})" for c in colors])


def _build_prompt(brand_identity: BrandIdentityFull) -> str:
    """Build the generation prompt from brand identity."""
    bi = brand_identity
    return f"""\
Analyze this brand identity and generate visual rules for image generation.

## Brand Identity

### Core Identity
- Name: {bi.core.name}
- Tagline: {bi.core.tagline}
- Mission: {bi.core.mission}
- Values: {_fmt(bi.core.values)}

### Visual Identity
- Overall Aesthetic: {bi.visual.overall_aesthetic}
- Style Keywords: {_fmt(bi.visual.style_keywords)}
- Imagery Style: {bi.visual.imagery_style}
- Imagery Keywords: {_fmt(bi.visual.imagery_keywords)}
- Imagery to Avoid: {_fmt(bi.visual.imagery_avoid)}
- Primary Colors: {_fmt_colors(bi.visual.primary_colors)}
- Secondary Colors: {_fmt_colors(bi.visual.secondary_colors)}
- Materials: {_fmt(bi.visual.materials)}

### Audience Profile
- Primary Summary: {bi.audience.primary_summary}
- Age Range: {bi.audience.age_range}
- Gender: {bi.audience.gender}
- Lifestyle: {bi.audience.lifestyle}
- Values: {_fmt(bi.audience.values)}
- Interests: {_fmt(bi.audience.interests)}

### Voice & Personality
- Personality: {bi.voice.personality}
- Tone Attributes: {_fmt(bi.voice.tone_attributes)}

### Positioning
- Market Category: {bi.positioning.market_category}
- Unique Value Proposition: {bi.positioning.unique_value_proposition}
- Differentiation: {bi.positioning.differentiation}

### Constraints
- Must-haves: {_fmt(bi.constraints, "None specified")}
- Avoid: {_fmt(bi.avoid, "None specified")}

---

Based on this brand identity, generate visual rules that will guide image \
generation to be consistent with the brand. Focus on:
1. Who should appear in images (based on target audience)
2. Color direction (from visual identity)
3. Mood and atmosphere (from personality and values)
4. Photography style (from imagery guidelines)
5. Hard rules (things to always/never include)
"""


async def generate_visual_directive(
    brand_identity: BrandIdentityFull,
    progress_callback: Callable[[str], None] | None = None,
) -> VisualDirective:
    """Generate a VisualDirective from a BrandIdentityFull.

    Args:
        brand_identity: The full brand identity to analyze.
        progress_callback: Optional callback for progress updates.

    Returns:
        A new VisualDirective populated with extracted visual rules.
    """
    if progress_callback:
        progress_callback("Analyzing brand identity for visual rules...")
    prompt = _build_prompt(brand_identity)
    if progress_callback:
        progress_callback("Running visual directive generation...")
    result = await Runner.run(_generator_agent, prompt)
    output: VisualDirectiveOutput = result.final_output
    if progress_callback:
        progress_callback("Building visual directive...")
    directive = VisualDirective(
        version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        generated_from_identity_at=datetime.utcnow(),
        target_representation=output.target_representation,
        color_guidelines=output.color_guidelines,
        mood_guidelines=output.mood_guidelines,
        photography_style=output.photography_style,
        always_include=output.always_include,
        never_include=output.never_include,
        learned_rules=[],
    )
    logger.info("Generated visual directive for brand: %s", brand_identity.slug)
    return directive


async def generate_and_save_visual_directive(
    brand_slug: str,
    brand_identity: BrandIdentityFull,
    progress_callback: Callable[[str], None] | None = None,
) -> VisualDirective:
    """Generate and save a VisualDirective for a brand.

    Args:
        brand_slug: The brand slug.
        brand_identity: The full brand identity.
        progress_callback: Optional callback for progress updates.

    Returns:
        The saved VisualDirective.
    """
    directive = await generate_visual_directive(brand_identity, progress_callback)
    save_visual_directive(brand_slug, directive)
    if progress_callback:
        progress_callback("Visual directive saved.")
    return directive


async def regenerate_visual_directive(
    brand_slug: str,
    brand_identity: BrandIdentityFull,
    preserve_learned_rules: bool = True,
    progress_callback: Callable[[str], None] | None = None,
) -> VisualDirective:
    """Regenerate visual directive, optionally preserving learned rules.

    Args:
        brand_slug: The brand slug.
        brand_identity: The full brand identity.
        preserve_learned_rules: If True, copy learned rules from existing directive.
        progress_callback: Optional callback for progress updates.

    Returns:
        The new VisualDirective.
    """
    existing = load_visual_directive(brand_slug)
    new_directive = await generate_visual_directive(brand_identity, progress_callback)
    if preserve_learned_rules and existing and existing.learned_rules:
        new_directive.learned_rules = existing.learned_rules
        new_directive.version = existing.version + 1
        if progress_callback:
            n = len(existing.learned_rules)
            v = existing.version
            progress_callback(f"Preserved {n} learned rules from v{v}")
    save_visual_directive(brand_slug, new_directive)
    return new_directive
