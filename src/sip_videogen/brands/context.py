"""Brand context builder for agent prompts.

Generates consistent brand context sections to inject into agent prompts,
including the L0 summary and pointers to deeper layers.
"""

from __future__ import annotations

from .storage import load_brand_summary

# Description of each detail type for agent prompts
DETAIL_DESCRIPTIONS = {
    "visual_identity": "Complete color palette, typography rules, imagery style guidelines",
    "voice_guidelines": "Tone of voice, messaging do's/don'ts, example copy",
    "audience_profile": "Target demographics, psychographics, pain points, desires",
    "positioning": "Market category, competitors, differentiation strategy",
}


class BrandContextBuilder:
    """Builds brand context sections for agent prompts."""

    def __init__(self, slug: str):
        """Initialize with a brand slug.

        Args:
            slug: Brand identifier to build context for.

        Raises:
            ValueError: If brand not found.
        """
        self.slug = slug
        self.summary = load_brand_summary(slug)

        if self.summary is None:
            raise ValueError(f"Brand '{slug}' not found")

    def build_context_section(self) -> str:
        """Build the complete brand context section for prompts.

        Returns:
            Formatted string to include in agent prompts.
        """
        s = self.summary

        colors_str = ", ".join(s.primary_colors) if s.primary_colors else "Not defined"

        context = f"""
## Brand Context: {s.name}

**Tagline**: {s.tagline}
**Category**: {s.category}
**Tone**: {s.tone}
**Primary Colors**: {colors_str}
**Visual Style**: {s.visual_style or "Not defined"}
**Target Audience**: {s.audience_summary or "Not defined"}

## Available Brand Details

Use `fetch_brand_detail(detail_type)` to access deeper information:

{self._format_available_details()}

## Asset Library

{s.asset_count} existing assets available. Use `browse_brand_assets(category)` to explore.

## Memory Exploration Protocol

**IMPORTANT**: Before making creative decisions:
1. Review the summary above
2. Fetch relevant details using `fetch_brand_detail()`
3. Check existing assets with `browse_brand_assets()`
4. If details don't fully answer your question, use your best judgment
5. Document any assumptions in your output
"""
        return context.strip()

    def _format_available_details(self) -> str:
        """Format the available details list."""
        lines = []
        for detail_type in self.summary.available_details:
            desc = DETAIL_DESCRIPTIONS.get(detail_type, "Additional brand information")
            lines.append(f'- `fetch_brand_detail("{detail_type}")`: {desc}')
        return "\n".join(lines)

    def inject_into_prompt(self, base_prompt: str, placeholder: str = "{brand_context}") -> str:
        """Inject brand context into an existing prompt.

        Args:
            base_prompt: The agent's base prompt with placeholder.
            placeholder: The placeholder string to replace.

        Returns:
            Prompt with brand context injected.
        """
        context = self.build_context_section()
        return base_prompt.replace(placeholder, context)


def build_brand_context(slug: str) -> str:
    """Convenience function to build brand context.

    Args:
        slug: Brand identifier.

    Returns:
        Formatted brand context string, or error message if brand not found.
    """
    try:
        builder = BrandContextBuilder(slug)
        return builder.build_context_section()
    except ValueError as e:
        return f"Error: {e}"
