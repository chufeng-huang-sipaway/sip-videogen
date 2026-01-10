"""Prompt building utilities for the Brand Marketing Advisor.
This module contains functions for constructing system prompts with brand context.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sip_studio.advisor.skills.registry import get_skills_registry
from sip_studio.brands.knowledge_summary import build_knowledge_context
from sip_studio.brands.memory import list_brand_assets
from sip_studio.brands.storage import (
    get_brand_dir,
    list_products,
    list_style_references,
    load_brand,
    load_brand_summary,
)

if TYPE_CHECKING:
    from sip_studio.brands.models import BrandIdentityFull
# Default prompt if file not found
DEFAULT_PROMPT = """# Brand Marketing Advisor

You are a Brand Marketing Advisor - an expert in brand strategy, visual identity,
and marketing communications. You help users build, evolve, and maintain their
brand identities.

## Your Capabilities

You have 5 core tools:
1. **generate_image** - Create images via Gemini (logos, mascots, lifestyle photos)
2. **read_file** - Read files from the brand directory
3. **write_file** - Write/update files in the brand directory
4. **list_files** - Browse the brand directory structure
5. **load_brand** - Load brand identity (summary by default; use `detail_level='full'` for full)

## Your Approach

1. **Understand First**: Always load and understand the brand context before making decisions
2. **Be Consultative**: Ask clarifying questions when requirements are ambiguous
3. **Stay On-Brand**: Ensure all outputs align with established brand guidelines
4. **Document Decisions**: Use write_file to persist important decisions and rationale
5. **Reference Skills**: Use the available skills as guides for specific tasks

## Output Quality

- Generate high-quality, professional brand assets
- Provide clear rationale for creative decisions
- Maintain consistency with existing brand materials
- Suggest improvements based on brand strategy principles
"""


def _group_assets(assets: list[dict]) -> dict[str, list[dict]]:
    """Group assets by category."""
    g: dict[str, list[dict]] = {}
    for a in assets:
        c = a.get("category", "other")
        if c not in g:
            g[c] = []
        g[c].append(a)
    return g


def format_brand_context(slug: str, identity: "BrandIdentityFull") -> str:
    """Format brand identity as context for the system prompt.
    Args:
        slug: Brand slug.
        identity: Full brand identity.
    Returns:
        Formatted brand context markdown.
    """
    p = [
        "## Current Brand Context",
        "",
        f"**Brand**: {identity.core.name}",
        f"**Tagline**: {identity.core.tagline}",
        f"**Category**: {identity.positioning.market_category}",
        "",
    ]
    # Visual identity summary
    if identity.visual.primary_colors:
        c = ", ".join(f"{c.name} ({c.hex})" for c in identity.visual.primary_colors[:3])
        p.append(f"**Colors**: {c}")
    if identity.visual.style_keywords:
        p.append(f"**Style**: {', '.join(identity.visual.style_keywords[:5])}")
    # Voice summary
    if identity.voice.tone_attributes:
        p.append(f"**Tone**: {', '.join(identity.voice.tone_attributes[:3])}")
    # Audience summary
    p.append(f"**Audience**: {identity.audience.primary_summary}")
    # Assets summary
    try:
        assets = list_brand_assets(slug)
        if assets:
            s = ", ".join(f"{cat}: {len(files)}" for cat, files in _group_assets(assets).items())
            p.append(f"**Assets**: {s}")
    except Exception:
        pass
    p.append("")
    p.append(
        "Use `load_brand()` for a quick summary, or "
        "`load_brand(detail_level='full')` for complete context. "
        "Use `list_files()` to browse assets."
    )
    return "\n".join(p)


def build_lean_brand_context(slug: str, conversation_summary: str | None = None) -> str:
    """Build lean brand context using knowledge pointers (Stage 7).
    Replaces full data injection with ~300 tokens of context + tool pointers.
    Args:
        slug: Brand slug.
        conversation_summary: Optional compacted conversation summary.
    Returns:
        Lean context string with tool pointers.
    """
    brand_summary = load_brand_summary(slug)
    if not brand_summary:
        return ""
    # Get product and style reference summaries
    products = list_products(slug) or []
    style_refs = list_style_references(slug) or []
    return build_knowledge_context(
        brand_summary=brand_summary,
        products=products,
        style_refs=style_refs,
        active_project=None,
        conversation_summary=conversation_summary,
    )


def build_system_prompt(
    brand_slug: str | None = None,
    use_lean_context: bool = False,
    conversation_summary: str | None = None,
) -> str:
    """Build the system prompt for the Brand Marketing Advisor.
    Args:
        brand_slug: Optional brand slug to include context for.
        use_lean_context: If True, use lean context with tool pointers (Stage 7).
        conversation_summary: Optional compacted conversation summary (for lean context).
    Returns:
        Complete system prompt with skills and brand context.
    """
    import json as _json

    # Load base prompt
    pp = Path(__file__).parent / "prompts" / "advisor.md"
    base = pp.read_text() if pp.exists() else DEFAULT_PROMPT
    # Add skills section
    sr = get_skills_registry()
    skills_sec = sr.format_for_prompt()
    # Add brand context if available
    brand_sec = ""
    mem_sec = ""
    if brand_slug:
        if use_lean_context:
            # Use lean context with tool pointers (Stage 7 - ~300 tokens vs ~500+)
            brand_sec = build_lean_brand_context(brand_slug, conversation_summary)
        else:
            # Legacy: full brand context injection
            ident = load_brand(brand_slug)
            if ident:
                brand_sec = format_brand_context(brand_slug, ident)
        mp = get_brand_dir(brand_slug) / "memory.json"
        if mp.exists():
            try:
                mem = _json.loads(mp.read_text())
                if mem:
                    ml = ["## Remembered Preferences", ""]
                    for k, d in mem.items():
                        ml.append(f"- **{k}**: {d.get('value', '')}")
                    mem_sec = "\n".join(ml)
            except (_json.JSONDecodeError, KeyError):
                pass
    return f"""{base}

{skills_sec}

{brand_sec}

{mem_sec}
""".strip()
