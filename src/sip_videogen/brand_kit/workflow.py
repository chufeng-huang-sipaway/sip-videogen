"""Helpers for building and executing the Brand Kit workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, List

from sip_videogen.config.logging import get_logger
from sip_videogen.generators.nano_banana_generator import NanoBananaImageGenerator
from sip_videogen.models.brand_kit import (
    BrandAssetCategory,
    BrandAssetPrompt,
    BrandAssetResult,
    BrandDirection,
    BrandKitBrief,
)

logger = get_logger(__name__)


def _comma_join(items: Iterable[str]) -> str:
    """Join strings with commas, filtering empties."""
    cleaned = [i.strip() for i in items if i and i.strip()]
    return ", ".join(cleaned)


def _anchor_summary(brief: BrandKitBrief, direction: BrandDirection) -> str:
    """Quick summary string to keep prompts aligned."""
    palette = _comma_join(direction.color_palette) or "refined palette"
    style = _comma_join(direction.style_keywords) or brief.tone
    materials = _comma_join(direction.materials)
    settings = _comma_join(direction.settings)
    pieces = [
        f"Palette: {palette}",
        f"Style: {style}",
        f"Tone: {direction.tone or brief.tone}",
    ]
    if materials:
        pieces.append(f"Materials: {materials}")
    if settings:
        pieces.append(f"Settings: {settings}")
    if brief.constraints:
        pieces.append(f"Must-haves: {_comma_join(brief.constraints)}")
    if brief.avoid:
        pieces.append(f"Avoid: {_comma_join(brief.avoid)}")
    return " | ".join(pieces)


def _logo_prompts(brief: BrandKitBrief, direction: BrandDirection) -> list[BrandAssetPrompt]:
    """Generate prompts for logo exploration."""
    anchors = _anchor_summary(brief, direction)
    base = (
        f"Logo exploration for {brief.brand_name}, a {brief.product_category} brand offering "
        f"{brief.core_product}. Audience: {brief.target_audience}. {anchors}. "
        "Critical: one single logo only, centered, no multiple options, no grids or sheets, no extra marks."
    )

    return [
        BrandAssetPrompt(
            id="logo_wordmark",
            category=BrandAssetCategory.LOGO,
            label="Logo - Minimal Wordmark",
            prompt=(
                f"{base} Minimalist wordmark in clean {direction.typography or 'sans serif'} "
                f"type, vector style, high contrast on neutral background. Do not show multiple variations."
            ),
            aspect_ratio="1:1",
            variants=1,
        ),
        BrandAssetPrompt(
            id="logo_symbol",
            category=BrandAssetCategory.LOGO,
            label="Logo - Symbol + Logotype",
            prompt=(
                f"{base} Symbol plus logotype that nods to the product. Geometric icon with "
                f"balanced spacing, crisp vector edges, {direction.typography or 'contemporary type'}, "
                "monotone mark on softly textured backdrop. Only one logo in frame; no grid; ample whitespace."
            ),
            aspect_ratio="1:1",
            variants=1,
        ),
        BrandAssetPrompt(
            id="logo_badge",
            category=BrandAssetCategory.LOGO,
            label="Logo - Badge/Monogram",
            prompt=(
                f"{base} Monogram or badge treatment using the brand initials, compact and "
                "versatile. Elevated but legible, vector finish, subtle shadow for depth. One mark only; no sheets."
            ),
            aspect_ratio="1:1",
            variants=1,
        ),
    ]


def _packaging_prompts(
    brief: BrandKitBrief,
    direction: BrandDirection,
) -> list[BrandAssetPrompt]:
    """Generate prompts for packaging/product renders."""
    anchors = _anchor_summary(brief, direction)
    base = (
        f"Packaging concept for {brief.brand_name} {brief.core_product} "
        f"({brief.product_category}). {anchors}. Photorealistic product photography."
    )

    return [
        BrandAssetPrompt(
            id="packaging_hero",
            category=BrandAssetCategory.PACKAGING,
            label="Packaging - Hero",
            prompt=(
                f"{base} Clean hero shot with the logo centered on the pack, premium materials, "
                "soft studio lighting, light backdrop, crisp condensation or texture if relevant."
            ),
            aspect_ratio="3:4",
            variants=1,
        ),
        BrandAssetPrompt(
            id="packaging_alt_color",
            category=BrandAssetCategory.PACKAGING,
            label="Packaging - Alternate Palette",
            prompt=(
                f"{base} Alternate colorway from the palette, angled view, subtle shadow, "
                "no distracting props. Keep surfaces tidy and the logo readable."
            ),
            aspect_ratio="3:4",
            variants=1,
        ),
    ]


def _lifestyle_prompts(
    brief: BrandKitBrief,
    direction: BrandDirection,
) -> list[BrandAssetPrompt]:
    """Generate prompts for lifestyle/context scenes."""
    anchors = _anchor_summary(brief, direction)
    setting_hint = direction.settings[0] if direction.settings else "modern, airy setting"

    return [
        BrandAssetPrompt(
            id="lifestyle_in_use",
            category=BrandAssetCategory.LIFESTYLE,
            label="Lifestyle - In Use",
            prompt=(
                f"Lifestyle photo of {brief.brand_name} {brief.core_product} being enjoyed by the "
                f"target audience ({brief.target_audience}) in a {setting_hint}. {anchors}. "
                "Natural light, candid composition, premium yet approachable mood."
            ),
            aspect_ratio="4:5",
            variants=1,
        ),
        BrandAssetPrompt(
            id="lifestyle_flatlay",
            category=BrandAssetCategory.LIFESTYLE,
            label="Lifestyle - Flatlay",
            prompt=(
                f"High-angle flatlay of {brief.core_product} with complementary items that match "
                f"the palette ({_comma_join(direction.color_palette)}). {anchors}. "
                "Balanced spacing, soft shadows, editorial minimalism."
            ),
            aspect_ratio="4:5",
            variants=1,
        ),
        BrandAssetPrompt(
            id="lifestyle_environment",
            category=BrandAssetCategory.LIFESTYLE,
            label="Lifestyle - Environment Focus",
            prompt=(
                f"{brief.brand_name} presence within an environment: signage, countertop, or "
                f"display in {setting_hint}. {anchors}. Subtle depth of field, photorealistic, "
                "no crowded text."
            ),
            aspect_ratio="16:9",
            variants=1,
        ),
    ]


def _mascot_prompts(
    brief: BrandKitBrief,
    direction: BrandDirection,
) -> list[BrandAssetPrompt]:
    """Generate prompts for mascot exploration."""
    anchors = _anchor_summary(brief, direction)
    return [
        BrandAssetPrompt(
            id="mascot_primary",
            category=BrandAssetCategory.MASCOT,
            label="Mascot - Primary",
            prompt=(
                f"Mascot for {brief.brand_name}, embodying {brief.tone} and "
                f"{_comma_join(direction.style_keywords)}. {anchors}. "
                "Clear silhouette, friendly expression, no background text."
            ),
            aspect_ratio="1:1",
            variants=1,
        ),
        BrandAssetPrompt(
            id="mascot_alt",
            category=BrandAssetCategory.MASCOT,
            label="Mascot - Alternate",
            prompt=(
                f"Alternate mascot pose for {brief.brand_name} that fits the same palette and "
                "tone. Emphasize personality and charm. Keep background simple."
            ),
            aspect_ratio="1:1",
            variants=1,
        ),
    ]


def _marketing_prompts(
    brief: BrandKitBrief,
    direction: BrandDirection,
) -> list[BrandAssetPrompt]:
    """Generate prompts for marketing assets."""
    anchors = _anchor_summary(brief, direction)
    palette = _comma_join(direction.color_palette)
    return [
        BrandAssetPrompt(
            id="marketing_landing",
            category=BrandAssetCategory.MARKETING,
            label="Marketing - Landing Page",
            prompt=(
                f"Landing page hero layout for {brief.brand_name}. Show the product hero shot, "
                f"clean grid, strong CTA, {brief.tone} tone. Palette {palette}. "
                "Modern web aesthetic, generous whitespace, crisp typography."
            ),
            aspect_ratio="16:9",
            variants=1,
        ),
        BrandAssetPrompt(
            id="marketing_recipe_usage",
            category=BrandAssetCategory.MARKETING,
            label="Marketing - Usage/Recipe Card",
            prompt=(
                f"Usage or recipe card for {brief.core_product}, styled for social. {anchors}. "
                "Ingredient or step visual cues, minimal readable text placeholders, "
                "neat layout on neutral backdrop."
            ),
            aspect_ratio="4:5",
            variants=1,
        ),
        BrandAssetPrompt(
            id="marketing_merch",
            category=BrandAssetCategory.MARKETING,
            label="Marketing - Merch",
            prompt=(
                f"Merch assortment for {brief.brand_name}: tote, tee, hoodie or accessories. "
                f"Use the logo and palette ({palette}). {anchors}. Studio lighting, clean surface."
            ),
            aspect_ratio="4:5",
            variants=1,
        ),
        BrandAssetPrompt(
            id="marketing_popup",
            category=BrandAssetCategory.MARKETING,
            label="Marketing - Pop-up Stand",
            prompt=(
                f"Pop-up stand or booth design for {brief.brand_name} in a small footprint. "
                f"{anchors}. Include counter, backdrop graphics, and product display. "
                "Bright inviting lighting."
            ),
            aspect_ratio="16:9",
            variants=1,
        ),
        BrandAssetPrompt(
            id="marketing_meme",
            category=BrandAssetCategory.MARKETING,
            label="Marketing - Playful Meme",
            prompt=(
                f"Playful meme-style visual using the {brief.brand_name} product and mascot vibe. "
                "Keep it lighthearted and brand-safe, simple layout, no offensive content."
            ),
            aspect_ratio="1:1",
            variants=1,
        ),
    ]


def build_brand_asset_prompts(
    brief: BrandKitBrief,
    direction: BrandDirection,
) -> List[BrandAssetPrompt]:
    """Build the full prompt list for a chosen direction."""
    prompts: list[BrandAssetPrompt] = []
    prompts.extend(_logo_prompts(brief, direction))
    prompts.extend(_packaging_prompts(brief, direction))
    prompts.extend(_lifestyle_prompts(brief, direction))
    prompts.extend(_mascot_prompts(brief, direction))
    prompts.extend(_marketing_prompts(brief, direction))
    return prompts


def generate_brand_assets(
    prompts: List[BrandAssetPrompt],
    generator: NanoBananaImageGenerator,
    output_dir: Path,
    on_progress: Callable[[BrandAssetPrompt, List[str]], None] | None = None,
) -> List[BrandAssetResult]:
    """Generate all assets for the provided prompts.

    Args:
        prompts: Prepared prompts to execute.
        generator: Nano Banana image generator instance.
        output_dir: Base directory for outputs.

    Returns:
        List of BrandAssetResult capturing image paths and metadata.
    """
    results: list[BrandAssetResult] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for prompt in prompts:
        category_dir = output_dir / prompt.category.value
        logger.info("Generating %s (%s)", prompt.label, prompt.category.value)
        image_paths = generator.generate_images(
            prompt=prompt.prompt,
            output_dir=category_dir,
            n=prompt.variants,
            aspect_ratio=prompt.aspect_ratio,
            filename_prefix=prompt.id,
        )

        result = BrandAssetResult(
            prompt_id=prompt.id,
            category=prompt.category,
            label=prompt.label,
            prompt_used=prompt.prompt,
            image_paths=image_paths,
        )
        results.append(result)

        if on_progress:
            try:
                on_progress(prompt, image_paths)
            except Exception as callback_error:
                logger.debug("Progress callback failed: %s", callback_error)

    return results
