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
    """Generate prompt for the definitive brand logo."""
    anchors = _anchor_summary(brief, direction)
    prompt = (
        f"Create a single, definitive logo for {brief.brand_name}, "
        f"a {brief.product_category} brand offering {brief.core_product}. "
        f"Target audience: {brief.target_audience}. {anchors}. "
        f"Typography: {direction.typography or 'clean sans serif'}. "
        "Requirements: ONE logo only, centered on neutral background, professional vector "
        "style, suitable for packaging and marketing materials. Include both a symbol/icon "
        "and the brand name. No multiple variations, no grids, no sheets, no extra marks. "
        "High contrast, crisp edges."
    )
    return [
        BrandAssetPrompt(
            id="logo_primary",
            category=BrandAssetCategory.LOGO,
            label="Primary Brand Logo",
            prompt=prompt,
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
        f"({brief.product_category}). {anchors}. Photorealistic product photography. "
        "IMPORTANT: Use the provided logo reference image exactly as shown - "
        "incorporate it prominently on the packaging without modification."
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
    logo_instruction = (
        "IMPORTANT: Use the provided logo reference image exactly as shown - "
        "incorporate it prominently without modification. "
    )
    return [
        BrandAssetPrompt(
            id="marketing_landing",
            category=BrandAssetCategory.MARKETING,
            label="Marketing - Landing Page",
            prompt=(
                f"Landing page hero layout for {brief.brand_name}. {logo_instruction}"
                f"Show the product hero shot, clean grid, strong CTA, {brief.tone} tone. "
                f"Palette {palette}. Modern web aesthetic, generous whitespace."
            ),
            aspect_ratio="16:9",
            variants=1,
        ),
        BrandAssetPrompt(
            id="marketing_recipe_usage",
            category=BrandAssetCategory.MARKETING,
            label="Marketing - Usage/Recipe Card",
            prompt=(
                f"Usage or recipe card for {brief.core_product}, styled for social. "
                f"{anchors}. {logo_instruction}Ingredient or step visual cues, "
                "minimal readable text placeholders, neat layout on neutral backdrop."
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
                f"{logo_instruction}Use the palette ({palette}). {anchors}. Studio lighting."
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
                f"{logo_instruction}{anchors}. Include counter, backdrop graphics, display. "
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
                f"Playful meme-style visual using the {brief.brand_name} product and mascot. "
                f"{logo_instruction}Keep it lighthearted, brand-safe, simple layout."
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


def _enhance_logo_prompt_with_feedback(
    original_prompt: str,
    feedback: str,
    attempt: int,
) -> str:
    """Enhance logo prompt based on user feedback.

    Args:
        original_prompt: The original logo generation prompt.
        feedback: User's feedback on what to improve.
        attempt: Current attempt number (1-indexed).

    Returns:
        Enhanced prompt incorporating the feedback.
    """
    return (
        f"{original_prompt}\n\n"
        f"REVISION #{attempt + 1} - User feedback to address:\n"
        f"{feedback}\n\n"
        "Please create a new logo that addresses this feedback while "
        "maintaining the brand identity. Focus on the specific improvements requested."
    )


def generate_brand_assets(
    prompts: List[BrandAssetPrompt],
    generator: NanoBananaImageGenerator,
    output_dir: Path,
    on_progress: Callable[[BrandAssetPrompt, List[str]], None] | None = None,
    on_logo_ready: Callable[[str], bool | tuple[str, str]] | None = None,
    max_logo_attempts: int = 3,
) -> List[BrandAssetResult]:
    """Generate all assets for the provided prompts.

    Args:
        prompts: Prepared prompts to execute.
        generator: Nano Banana image generator instance.
        output_dir: Base directory for outputs.
        on_progress: Optional callback for progress updates.
        on_logo_ready: Optional callback when logo is generated. Receives logo path,
            returns True to continue, False to abort, or ("retry", feedback) to
            regenerate with feedback.
        max_logo_attempts: Maximum number of logo generation attempts (default 3).

    Returns:
        List of BrandAssetResult capturing image paths and metadata.
    """
    results: list[BrandAssetResult] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    logo_path: str | None = None

    for prompt in prompts:
        category_dir = output_dir / prompt.category.value
        logger.info("Generating %s (%s)", prompt.label, prompt.category.value)

        # Special handling for logo with feedback loop
        if prompt.category == BrandAssetCategory.LOGO:
            attempt = 1
            current_prompt = prompt.prompt
            final_image_paths: list[str] = []

            while attempt <= max_logo_attempts:
                logger.info("Logo attempt %d/%d", attempt, max_logo_attempts)
                image_paths = generator.generate_images(
                    prompt=current_prompt,
                    output_dir=category_dir,
                    n=prompt.variants,
                    aspect_ratio=prompt.aspect_ratio,
                    filename_prefix=f"{prompt.id}_v{attempt}",
                )

                if not image_paths:
                    logger.warning("No logo image generated on attempt %d", attempt)
                    attempt += 1
                    continue

                logo_path = image_paths[0]
                logger.info("Logo generated: %s", logo_path)

                if on_logo_ready:
                    result = on_logo_ready(logo_path)

                    if result is True:
                        # Approved - continue with other assets
                        final_image_paths = image_paths
                        break
                    elif isinstance(result, tuple) and result[0] == "retry":
                        # User provided feedback - regenerate
                        feedback = result[1]
                        logger.info("User feedback: %s", feedback)
                        current_prompt = _enhance_logo_prompt_with_feedback(
                            original_prompt=prompt.prompt,
                            feedback=feedback,
                            attempt=attempt,
                        )
                        attempt += 1
                        continue
                    else:
                        # Aborted
                        raise ValueError("Logo generation cancelled by user")
                else:
                    # No callback - just use the first result
                    final_image_paths = image_paths
                    break
            else:
                # Exhausted all attempts
                raise ValueError(
                    f"Max logo attempts ({max_logo_attempts}) reached without approval"
                )

            # Record logo result
            result = BrandAssetResult(
                prompt_id=prompt.id,
                category=prompt.category,
                label=prompt.label,
                prompt_used=current_prompt,
                image_paths=final_image_paths,
            )
            results.append(result)

            if on_progress:
                try:
                    on_progress(prompt, final_image_paths)
                except Exception as callback_error:
                    logger.debug("Progress callback failed: %s", callback_error)

            continue  # Move to next prompt

        # Standard handling for non-logo assets
        use_logo_ref = (
            logo_path is not None
            and prompt.category in [BrandAssetCategory.PACKAGING, BrandAssetCategory.MARKETING]
        )

        image_paths = generator.generate_images(
            prompt=prompt.prompt,
            output_dir=category_dir,
            n=prompt.variants,
            aspect_ratio=prompt.aspect_ratio,
            filename_prefix=prompt.id,
            reference_image_path=logo_path if use_logo_ref else None,
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
