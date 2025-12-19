"""Brand context builder for agent prompts.

Generates consistent brand context sections to inject into agent prompts,
including the L0 summary and pointers to deeper layers.

Also provides context builders for Products and Projects, and a
HierarchicalContextBuilder for per-turn context injection.
"""

from __future__ import annotations

from .storage import (
    load_brand_summary,
    load_product,
    load_project,
)
from sip_videogen.config.settings import get_settings

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


# =============================================================================
# Product Context Builder
# =============================================================================


class ProductContextBuilder:
    """Builds product context for agent prompts."""

    def __init__(self, brand_slug: str, product_slug: str):
        """Initialize with brand and product slugs.

        Args:
            brand_slug: Brand identifier.
            product_slug: Product identifier.

        Raises:
            ValueError: If product not found.
        """
        self.brand_slug = brand_slug
        self.product_slug = product_slug
        self.product = load_product(brand_slug, product_slug)

        if self.product is None:
            raise ValueError(
                f"Product '{product_slug}' not found in brand '{brand_slug}'"
            )

    def build_context_section(self) -> str:
        """Build product context section for prompts.

        Returns:
            Formatted string including product info and brand-relative image paths.
            Includes explicit accuracy requirements and categorized attributes
            to ensure exact reproduction of product appearance.
        """
        p = self.product
        settings = get_settings()
        specs_injection_enabled = settings.sip_product_specs_injection

        # Categorize attributes by importance for accurate reproduction
        measurements = []
        materials = []
        colors = []
        other_attrs = []

        if p.attributes:
            for attr in p.attributes:
                key_lower = attr.key.lower()
                cat_lower = attr.category.lower() if attr.category else ""

                # Check for measurements (dimensions, size, etc.)
                if (
                    cat_lower == "measurements"
                    or "height" in key_lower
                    or "width" in key_lower
                    or "size" in key_lower
                    or "dimension" in key_lower
                    or "volume" in key_lower
                    or "weight" in key_lower
                ):
                    measurements.append(f"  - {attr.key}: {attr.value}")
                # Check for materials/textures (critical for visual accuracy)
                elif (
                    "material" in key_lower
                    or "texture" in key_lower
                    or "finish" in key_lower
                    or "surface" in key_lower
                ):
                    materials.append(f"  - {attr.key}: {attr.value} [PRESERVE EXACTLY]")
                # Check for colors (critical for brand consistency)
                elif "color" in key_lower or "colour" in key_lower:
                    colors.append(f"  - {attr.key}: {attr.value} [PRESERVE EXACTLY]")
                else:
                    other_attrs.append(f"  - {attr.key}: {attr.value}")

        # Build categorized attributes section
        attr_sections = []

        if measurements:
            attr_sections.append("**Measurements** (use for accurate scale):")
            attr_sections.extend(measurements)

        if materials:
            attr_sections.append("**Materials/Texture** (CRITICAL - preserve exactly):")
            attr_sections.extend(materials)

        if colors:
            attr_sections.append("**Colors** (CRITICAL - preserve exactly):")
            attr_sections.extend(colors)

        if other_attrs:
            attr_sections.append("**Other Attributes**:")
            attr_sections.extend(other_attrs)

        if not attr_sections:
            attr_sections.append("  (No attributes defined)")

        attributes_str = "\n".join(attr_sections)

        # Format images
        images_str = ""
        if p.images:
            image_lines = []
            for img in p.images:
                is_primary = " [PRIMARY - use as reference]" if img == p.primary_image else ""
                image_lines.append(f"  - {img}{is_primary}")
            images_str = "\n".join(image_lines)
        else:
            images_str = "  (No images)"

        prompt_guidance = ""
        if specs_injection_enabled:
            prompt_guidance = (
                "\n**PROMPT GUIDANCE (Specs Injection Enabled):**\n"
                "- Keep the product description concise (1-2 visual identifiers)\n"
                "- Use relative size cues (short/wide vs tall/slim)\n"
                "- Omit numeric dimensions and do not restate constraint blocks\n"
            )

        context = f"""### Product: {p.name}
**CRITICAL - EXACT REPRODUCTION REQUIRED**
This product must appear IDENTICAL to its reference image.
Preserve: exact shape, materials, colors, textures, and proportions.

**Slug**: `{p.slug}`
**Description**: {p.description}

{attributes_str}

**Reference Images**:
{images_str}
{prompt_guidance}

**HOW TO USE THIS PRODUCT IN IMAGES**:
→ Call `generate_image(product_slug="{p.slug}", prompt="...")`
→ DO NOT manually copy the reference image path
→ The product_slug parameter auto-loads the reference AND injects product specs
"""
        return context.strip()


def build_product_context(brand_slug: str, product_slug: str) -> str:
    """Convenience function to build product context.

    Args:
        brand_slug: Brand identifier.
        product_slug: Product identifier.

    Returns:
        Formatted product context string, or error message if not found.
    """
    try:
        builder = ProductContextBuilder(brand_slug, product_slug)
        return builder.build_context_section()
    except ValueError as e:
        return f"Error: {e}"


# =============================================================================
# Project Context Builder
# =============================================================================


class ProjectContextBuilder:
    """Builds project context for agent prompts."""

    def __init__(self, brand_slug: str, project_slug: str):
        """Initialize with brand and project slugs.

        Args:
            brand_slug: Brand identifier.
            project_slug: Project identifier.

        Raises:
            ValueError: If project not found.
        """
        self.brand_slug = brand_slug
        self.project_slug = project_slug
        self.project = load_project(brand_slug, project_slug)

        if self.project is None:
            raise ValueError(
                f"Project '{project_slug}' not found in brand '{brand_slug}'"
            )

    def build_context_section(self) -> str:
        """Build project context section for prompts.

        Returns:
            Formatted string with project instructions markdown.
        """
        p = self.project

        instructions = p.instructions.strip() if p.instructions else "(No instructions defined)"

        context = f"""### Active Project: {p.name}
**Slug**: {p.slug}
**Status**: {p.status.value}

**Project Instructions**:
{instructions}
"""
        return context.strip()


def build_project_context(brand_slug: str, project_slug: str) -> str:
    """Convenience function to build project context.

    Args:
        brand_slug: Brand identifier.
        project_slug: Project identifier.

    Returns:
        Formatted project context string, or error message if not found.
    """
    try:
        builder = ProjectContextBuilder(brand_slug, project_slug)
        return builder.build_context_section()
    except ValueError as e:
        return f"Error: {e}"


# =============================================================================
# Hierarchical Context Builder (Per-Turn Injection)
# =============================================================================


class HierarchicalContextBuilder:
    """Combines brand, product, and project context for per-turn injection.

    This builder creates dynamic context to prepend to user messages each turn.
    Unlike brand context (which is in the system prompt at init), project and
    product context can change mid-conversation.

    NOTE: Brand context is NOT included here - it's already in the system prompt.
    This builder only handles project and attached products.
    """

    def __init__(
        self,
        brand_slug: str,
        product_slugs: list[str] | None = None,
        project_slug: str | None = None,
    ):
        """Initialize with brand slug and optional products/project.

        Args:
            brand_slug: Brand identifier.
            product_slugs: List of product slugs to include (attached products).
            project_slug: Active project slug (if any).
        """
        self.brand_slug = brand_slug
        self.product_slugs = product_slugs or []
        self.project_slug = project_slug

    def build_turn_context(self) -> str:
        """Build context to prepend to user message each turn.

        Returns formatted string with:
        - Project instructions (if project active)
        - Attached product descriptions + image paths (if products attached)
        - Multi-product accuracy requirements (if 2+ products attached)

        NOTE: Brand context is in system prompt (existing).
        This is ADDITIONAL context injected per-turn.

        Returns:
            Formatted context string, or empty string if no context.
        """
        sections = []

        # Project context first (more global)
        if self.project_slug:
            try:
                project_builder = ProjectContextBuilder(
                    self.brand_slug, self.project_slug
                )
                sections.append(project_builder.build_context_section())
            except ValueError:
                # Project not found - skip silently
                pass

        settings = get_settings()
        specs_injection_enabled = settings.sip_product_specs_injection

        # Attached products
        if self.product_slugs:
            product_sections = []
            for slug in self.product_slugs:
                try:
                    product_builder = ProductContextBuilder(self.brand_slug, slug)
                    product_sections.append(product_builder.build_context_section())
                except ValueError:
                    # Product not found - skip silently
                    pass

            if product_sections:
                # Multi-product scenario requires special handling
                if len(product_sections) > 1:
                    multi_product_header = self._build_multi_product_header(
                        len(product_sections)
                    )
                    sections.append(
                        multi_product_header + "\n\n" + "\n\n".join(product_sections)
                    )
                else:
                    # Single product - just add with simple header
                    products_header = "### Attached Product"
                    if specs_injection_enabled:
                        products_header += (
                            "\nNOTE: Product specs (measurements/materials/colors) will be appended "
                            "automatically. Keep the prompt concise; omit numeric dimensions and "
                            "do not restate the constraints block."
                        )
                    sections.append(
                        products_header + "\n\n" + "\n\n".join(product_sections)
                    )

        if not sections:
            return ""

        return "\n\n---\n\n".join(sections)

    def _build_multi_product_header(self, product_count: int) -> str:
        """Build the multi-product accuracy requirements header.

        Args:
            product_count: Number of products attached.

        Returns:
            Formatted header with accuracy requirements.
        """
        settings = get_settings()
        specs_injection_enabled = settings.sip_product_specs_injection

        if specs_injection_enabled:
            size_guidance = "- Relative size cues only (e.g., short and wide vs tall and slim); omit numeric dimensions"
            prompt_pattern = """[Scene description].
Feature EXACTLY these products:
1. [Product A name]: [concise visual identifiers only; omit numeric dimensions]
2. [Product B name]: [concise visual identifiers only; omit numeric dimensions]
...
"""
            note = (
                "NOTE: Product specs (measurements/materials/colors) will be appended automatically. "
                "Keep per-product descriptions short and do not repeat numeric dimensions or restate the constraints block."
            )
        else:
            size_guidance = "- Exact size/dimensions if available"
            prompt_pattern = """[Scene description].
Feature EXACTLY these products:
1. [Product A name]: [exact material], [exact color], [exact size], [distinctive features]
2. [Product B name]: [exact material], [exact color], [exact size], [distinctive features]
...

CRITICAL: Each product must appear IDENTICAL to its reference image.
Preserve all materials, colors, textures, and proportions exactly.
"""
            note = ""

        note_block = f"\n\n{note}\n" if note else "\n"

        return f"""### MULTI-PRODUCT ACCURACY REQUIREMENTS

You have {product_count} products attached. Each must be reproduced with PIXEL-PERFECT accuracy.

**CRITICAL RULES:**
1. EVERY product must appear EXACTLY as its reference image
2. DO NOT change ANY materials, colors, or textures
3. Each product must be CLEARLY DISTINGUISHABLE from the others
4. Preserve exact proportions and scale relationships
5. If products have different materials (glass vs metal vs plastic),
   those differences MUST be visible

**When generating the prompt, include for EACH product:**
- Exact material description from attributes
- Exact color specification
{size_guidance}
- Distinctive features that differentiate it from other products

**PROMPT PATTERN for multi-product images:**
```
{prompt_pattern}
```
{note_block}
**WARNING:** Accuracy is paramount. Our brand's reputation depends on showing
products exactly as they are. A "similar-looking" product is a FAILURE."""


def build_turn_context(
    brand_slug: str,
    product_slugs: list[str] | None = None,
    project_slug: str | None = None,
) -> str:
    """Convenience function to build per-turn context.

    Args:
        brand_slug: Brand identifier.
        product_slugs: List of attached product slugs.
        project_slug: Active project slug.

    Returns:
        Formatted context string for per-turn injection.
    """
    builder = HierarchicalContextBuilder(
        brand_slug=brand_slug,
        product_slugs=product_slugs,
        project_slug=project_slug,
    )
    return builder.build_turn_context()
