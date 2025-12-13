"""Migration utility for converting legacy brand_kit.json to new brand format.

This module provides functions to migrate existing brand kit runs
(from output directories) into the new persistent brand system.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path

from sip_videogen.models.brand_kit import BrandKitBrief, BrandDirection, BrandKitPackage

from .models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIdentityFull,
    ColorDefinition,
    CompetitivePositioning,
    TypographyRule,
    VisualIdentity,
    VoiceGuidelines,
)
from .storage import create_brand, get_brand_dir, slugify

logger = logging.getLogger(__name__)


def find_legacy_brand_kits(output_dir: Path | None = None) -> list[Path]:
    """Find all brand_kit.json files in the output directory.

    Args:
        output_dir: Output directory to search. Defaults to ./output.

    Returns:
        List of paths to brand_kit.json files, sorted by modification time (newest first).
    """
    if output_dir is None:
        output_dir = Path("./output")

    if not output_dir.exists():
        return []

    brand_kit_files = list(output_dir.glob("**/brand_kit.json"))

    # Sort by modification time (newest first)
    brand_kit_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    logger.info("Found %d legacy brand kit(s) in %s", len(brand_kit_files), output_dir)
    return brand_kit_files


def convert_brief_and_direction_to_identity(
    brief: BrandKitBrief,
    direction: BrandDirection,
    slug: str | None = None,
    source_dir: Path | None = None,
) -> BrandIdentityFull:
    """Convert a BrandKitBrief and BrandDirection to BrandIdentityFull.

    Args:
        brief: The brand brief from legacy format.
        direction: The selected direction from legacy format.
        slug: Optional slug override. If not provided, generated from brand name.
        source_dir: Optional source directory for copying assets.

    Returns:
        BrandIdentityFull model with mapped fields.
    """
    if slug is None:
        slug = slugify(brief.brand_name)

    # Parse typography from direction (e.g., "Serif typeface with... (e.g., Merriweather, Georgia)")
    typography_rules = []
    if direction.typography:
        # Try to extract font family from description
        font_match = re.search(r"\(e\.g\.,?\s*([^)]+)\)", direction.typography)
        if font_match:
            fonts = [f.strip() for f in font_match.group(1).split(",")]
            if fonts:
                typography_rules.append(
                    TypographyRule(
                        role="headings",
                        family=fonts[0],
                        weight="regular",
                        style_notes=direction.typography,
                    )
                )
                if len(fonts) > 1:
                    typography_rules.append(
                        TypographyRule(
                            role="body",
                            family=fonts[1],
                            weight="regular",
                            style_notes="",
                        )
                    )
        else:
            # Use the whole description as notes
            typography_rules.append(
                TypographyRule(
                    role="headings",
                    family="Sans-serif",
                    weight="regular",
                    style_notes=direction.typography,
                )
            )

    # Convert color palette to ColorDefinition list
    primary_colors = []
    secondary_colors = []
    for i, hex_color in enumerate(direction.color_palette):
        color = ColorDefinition(
            hex=hex_color,
            name=f"Color {i + 1}",
            usage="Primary" if i < 2 else "Supporting",
        )
        if i < 2:
            primary_colors.append(color)
        else:
            secondary_colors.append(color)

    # Build the full identity
    identity = BrandIdentityFull(
        slug=slug,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        core=BrandCoreIdentity(
            name=brief.brand_name,
            tagline=direction.summary[:200] if direction.summary else "",
            mission=f"To provide {brief.core_product} for {brief.target_audience}",
            brand_story="",
            values=brief.style_keywords[:5] if brief.style_keywords else [],
        ),
        visual=VisualIdentity(
            primary_colors=primary_colors,
            secondary_colors=secondary_colors,
            accent_colors=[],
            typography=typography_rules,
            imagery_style=(
                direction.differentiator or direction.summary[:200]
                if direction.differentiator or direction.summary
                else ""
            ),
            imagery_keywords=direction.style_keywords,
            imagery_avoid=brief.avoid,
            materials=direction.materials,
            logo_description="",
            logo_usage_rules="",
            overall_aesthetic=direction.summary,
            style_keywords=direction.style_keywords,
        ),
        voice=VoiceGuidelines(
            personality=direction.tone or brief.tone,
            tone_attributes=(
                [t.strip() for t in (direction.tone or brief.tone).split(",")]
                if (direction.tone or brief.tone)
                else []
            ),
            key_messages=[],
            messaging_do=[],
            messaging_dont=[],
            example_headlines=[],
            example_taglines=[direction.label] if direction.label else [],
        ),
        audience=AudienceProfile(
            primary_summary=brief.target_audience,
            age_range="",
            gender="",
            income_level="",
            location="",
            interests=[],
            values=brief.style_keywords[:3] if brief.style_keywords else [],
            lifestyle="",
            pain_points=[],
            desires=[],
        ),
        positioning=CompetitivePositioning(
            market_category=brief.product_category,
            unique_value_proposition=brief.core_product,
            primary_competitors=[],
            differentiation=direction.differentiator or "",
            positioning_statement=(
                f"{brief.brand_name} is the {brief.product_category} brand "
                f"for {brief.target_audience} who want {brief.core_product}."
            ),
        ),
        constraints=brief.constraints,
        avoid=brief.avoid,
    )

    return identity


def load_legacy_brand_kit(brand_kit_path: Path) -> BrandKitPackage | None:
    """Load a legacy brand_kit.json file.

    Args:
        brand_kit_path: Path to brand_kit.json file.

    Returns:
        BrandKitPackage or None if loading fails.
    """
    try:
        data = json.loads(brand_kit_path.read_text())
        return BrandKitPackage.model_validate(data)
    except Exception as e:
        logger.error("Failed to load brand kit from %s: %s", brand_kit_path, e)
        return None


def migrate_brand_kit(
    brand_kit_path: Path,
    copy_assets: bool = True,
    slug_override: str | None = None,
) -> str | None:
    """Migrate a single brand_kit.json to the new brand system.

    Args:
        brand_kit_path: Path to brand_kit.json file.
        copy_assets: Whether to copy generated assets to brand directory.
        slug_override: Optional slug override (defaults to slugified brand name).

    Returns:
        Brand slug if successful, None if failed.
    """
    package = load_legacy_brand_kit(brand_kit_path)
    if package is None:
        return None

    slug = slug_override or slugify(package.brief.brand_name)

    # Convert to new format
    identity = convert_brief_and_direction_to_identity(
        brief=package.brief,
        direction=package.selected_direction,
        slug=slug,
        source_dir=brand_kit_path.parent,
    )

    # Create the brand
    try:
        create_brand(identity)
        logger.info("Created brand: %s from %s", slug, brand_kit_path)
    except ValueError as e:
        # Brand already exists
        logger.warning("Brand '%s' already exists: %s", slug, e)
        return None

    # Copy assets if requested
    if copy_assets:
        brand_dir = get_brand_dir(slug)
        source_assets = brand_kit_path.parent / "assets"

        if source_assets.exists():
            for category in ["logo", "packaging", "lifestyle", "mascot", "marketing"]:
                source_cat = source_assets / category
                target_cat = brand_dir / "assets" / category

                if source_cat.exists():
                    for asset_file in source_cat.iterdir():
                        if asset_file.is_file() and asset_file.suffix.lower() in [
                            ".png",
                            ".jpg",
                            ".jpeg",
                            ".webp",
                        ]:
                            target_file = target_cat / asset_file.name
                            shutil.copy2(asset_file, target_file)
                            logger.debug("Copied asset: %s", target_file)

            logger.info("Copied assets from %s to %s", source_assets, brand_dir / "assets")

    return slug


def migrate_all_brand_kits(
    output_dir: Path | None = None,
    copy_assets: bool = True,
    skip_existing: bool = True,
) -> dict[str, str | None]:
    """Migrate all legacy brand kits to the new brand system.

    Args:
        output_dir: Output directory to search. Defaults to ./output.
        copy_assets: Whether to copy generated assets to brand directory.
        skip_existing: Whether to skip if brand already exists.

    Returns:
        Dict mapping brand_kit.json paths to created slugs (or None if skipped/failed).
    """
    results: dict[str, str | None] = {}
    brand_kit_files = find_legacy_brand_kits(output_dir)

    for brand_kit_path in brand_kit_files:
        logger.info("Migrating: %s", brand_kit_path)

        # Check if this brand already exists
        package = load_legacy_brand_kit(brand_kit_path)
        if package is None:
            results[str(brand_kit_path)] = None
            continue

        slug = slugify(package.brief.brand_name)
        brand_dir = get_brand_dir(slug)

        if skip_existing and brand_dir.exists():
            logger.info("Skipping existing brand: %s", slug)
            results[str(brand_kit_path)] = None
            continue

        result = migrate_brand_kit(brand_kit_path, copy_assets=copy_assets)
        results[str(brand_kit_path)] = result

    migrated_count = sum(1 for v in results.values() if v is not None)
    logger.info(
        "Migration complete: %d/%d brand kits migrated",
        migrated_count,
        len(brand_kit_files),
    )

    return results
