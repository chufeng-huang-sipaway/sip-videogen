"""Style reference management tools."""

from __future__ import annotations

import re
from datetime import datetime as _dt
from pathlib import Path

from agents import function_tool

from sip_videogen.advisor.style_reference_analyzer import analyze_style_reference_v2
from sip_videogen.brands.models import StyleReferenceFull
from sip_videogen.config.logging import get_logger

from . import _common
from .memory_tools import emit_tool_thinking

logger = get_logger(__name__)


def _impl_list_style_references() -> str:
    """List all style references for active brand."""
    logger.info("list_style_references called")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    srs = _common.storage_list_style_references(slug)
    if not srs:
        return "No style references found for this brand."
    lines = ["**Style References:**"]
    for sr in srs:
        img_count = 1 if sr.primary_image else 0
        lines.append(f"- **{sr.name}** (`{sr.slug}`) - {img_count} image(s)")
    return "\n".join(lines)


def _impl_get_style_reference_detail(style_ref_slug: str) -> str:
    """Get detailed style reference info including analysis."""
    logger.info(f"get_style_reference_detail called with style_ref_slug={style_ref_slug}")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    sr = _common.load_style_reference(slug, style_ref_slug)
    if not sr:
        return f"Error: Style reference '{style_ref_slug}' not found."
    lines = [
        f"# {sr.name}",
        f"**Slug:** `{sr.slug}`",
        f"**Description:** {sr.description or '(none)'}",
        f"**Default Strict:** {sr.default_strict}",
        f"**Images:** {len(sr.images)}",
    ]
    if sr.primary_image:
        lines.append(f"**Primary Image:** {sr.primary_image}")
    if sr.analysis:
        lines.append("\n## Analysis")
        version = getattr(sr.analysis, "version", "1.0")
        if version == "3.0":
            lines.append("**V3 Color Grading DNA Available**")
            cg = getattr(sr.analysis, "color_grading", None)
            if cg and cg.film_stock_reference:
                lines.append(f'- Film Look: "{cg.film_stock_reference}"')
            ss = getattr(sr.analysis, "style_suggestions", None)
            if ss and ss.mood:
                lines.append(f'- Mood: "{ss.mood}"')
        elif hasattr(sr.analysis, "visual_scene"):
            lines.append("**V2 Semantic Analysis Available**")
            style = getattr(sr.analysis, "style", None)
            if style and style.mood:
                lines.append(f'- Mood: "{style.mood}"')
            if sr.analysis.visual_scene and sr.analysis.visual_scene.photography_style:
                lines.append(f'- Photography: "{sr.analysis.visual_scene.photography_style}"')
        else:
            lines.append("**V1 Geometry Analysis Available**")
    return "\n".join(lines)


async def _generate_style_reference_name(image_path: Path) -> str:
    """Generate descriptive style reference name from image using Gemini."""
    try:
        from google import genai
        from google.genai import types

        settings = _common.get_settings()
        client = genai.Client(api_key=settings.gemini_api_key)
        img_bytes = image_path.read_bytes()
        prompt = "Analyze this design style reference image and suggest a short descriptive name (2-4 words) that captures its visual style. Examples: 'Hero Centered Product', 'Split Two-Column', 'Minimalist Product Card'. Reply with ONLY the name, nothing else."
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Part.from_bytes(data=img_bytes, mime_type="image/png"), prompt],  # type: ignore[arg-type]
        )
        name = (resp.text or "").strip().strip('"').strip("'")
        return name if name else "New Style Reference"
    except Exception as e:
        logger.warning(f"Failed to generate style reference name: {e}")
        return "New Style Reference"


async def _impl_create_style_reference_async(
    name: str, description: str = "", image_path: str | None = None, default_strict: bool = True
) -> str:
    """Create a new style reference."""
    logger.info(f"create_style_reference called with name={name}")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    sr_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not sr_slug:
        return "Error: Invalid style reference name."
    existing = _common.load_style_reference_summary(slug, sr_slug)
    if existing:
        return f"Error: Style reference '{sr_slug}' already exists."
    step_id = emit_tool_thinking(
        "Analyzing style from your images...", name, expertise="Visual Design", status="pending"
    )
    now = _dt.utcnow()
    sr = StyleReferenceFull(
        slug=sr_slug,
        name=name,
        description=description,
        images=[],
        primary_image="",
        default_strict=default_strict,
        analysis=None,
        created_at=now,
        updated_at=now,
    )
    try:
        _common.storage_create_style_reference(slug, sr)
    except Exception as e:
        emit_tool_thinking(
            "Style reference creation failed",
            str(e)[:100],
            expertise="Visual Design",
            status="failed",
            step_id=step_id,
        )
        return f"Error creating style reference: {e}"
    if image_path:
        result = await _impl_add_style_reference_image_async(sr_slug, image_path, reanalyze=True)
        if result.startswith("Error"):
            emit_tool_thinking(
                "Style reference created, image failed",
                "",
                expertise="Visual Design",
                status="complete",
                step_id=step_id,
            )
            return f"Created style reference but failed to add image: {result}"
    emit_tool_thinking(
        "Style reference created",
        "",
        expertise="Visual Design",
        status="complete",
        step_id=step_id,
    )
    return f"Created style reference **{name}** (`{sr_slug}`)."


async def _impl_create_style_references_from_images_async(
    image_paths: list[str], default_strict: bool = True
) -> str:
    """Create one style reference per image with auto-generated names."""
    logger.info(f"create_style_references_from_images called with {len(image_paths)} images")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    brand_dir = _common.get_brand_dir(slug)
    created = []
    errors = []
    for img_path in image_paths:
        if not img_path.startswith("uploads/"):
            errors.append(f"{img_path}: must be in uploads/ folder")
            continue
        full_path = brand_dir / img_path
        if not full_path.exists():
            errors.append(f"{img_path}: file not found")
            continue
        name = await _generate_style_reference_name(full_path)
        base_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "style-reference"
        sr_slug = base_slug
        counter = 1
        while _common.load_style_reference_summary(slug, sr_slug):
            sr_slug = f"{base_slug}-{counter}"
            counter += 1
        now = _dt.utcnow()
        sr = StyleReferenceFull(
            slug=sr_slug,
            name=name,
            description="",
            images=[],
            primary_image="",
            default_strict=default_strict,
            analysis=None,
            created_at=now,
            updated_at=now,
        )
        try:
            _common.storage_create_style_reference(slug, sr)
            img_bytes = full_path.read_bytes()
            _common.storage_add_style_reference_image(slug, sr_slug, full_path.name, img_bytes)
            sr_loaded = _common.load_style_reference(slug, sr_slug)
            if sr_loaded and sr_loaded.images:
                img_full = brand_dir / sr_loaded.images[0]
                analysis = await analyze_style_reference_v2([img_full])
                if analysis:
                    sr_loaded.analysis = analysis
                    sr_loaded.updated_at = _dt.utcnow()
                    _common.storage_save_style_reference(slug, sr_loaded)
            created.append(f"**{name}** (`{sr_slug}`)")
        except Exception as e:
            errors.append(f"{img_path}: {e}")
    result_lines = []
    if created:
        result_lines.append(
            f"Created {len(created)} style reference(s):\n" + "\n".join(f"- {c}" for c in created)
        )
    if errors:
        result_lines.append("\nErrors:\n" + "\n".join(f"- {e}" for e in errors))
    return "\n".join(result_lines) if result_lines else "No style references created."


def _impl_update_style_reference(
    style_ref_slug: str,
    name: str | None = None,
    description: str | None = None,
    default_strict: bool | None = None,
) -> str:
    """Update style reference metadata."""
    logger.info(f"update_style_reference called with style_ref_slug={style_ref_slug}")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    sr = _common.load_style_reference(slug, style_ref_slug)
    if not sr:
        return f"Error: Style reference '{style_ref_slug}' not found."
    if name is not None:
        sr.name = name
    if description is not None:
        sr.description = description
    if default_strict is not None:
        sr.default_strict = default_strict
    sr.updated_at = _dt.utcnow()
    try:
        _common.storage_save_style_reference(slug, sr)
    except Exception as e:
        return f"Error updating style reference: {e}"
    return f"Updated style reference **{sr.name}** (`{style_ref_slug}`)."


async def _impl_add_style_reference_image_async(
    style_ref_slug: str, image_path: str, reanalyze: bool = True
) -> str:
    """Add image to style reference from uploads folder."""
    logger.info(
        f"add_style_reference_image called with style_ref_slug={style_ref_slug}, image_path={image_path}"
    )
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    sr = _common.load_style_reference(slug, style_ref_slug)
    if not sr:
        return f"Error: Style reference '{style_ref_slug}' not found."
    if not image_path.startswith("uploads/"):
        return "Error: image_path must be within uploads/ folder."
    brand_dir = _common.get_brand_dir(slug)
    full_path = brand_dir / image_path
    if not full_path.exists():
        return f"Error: File not found: {image_path}"
    try:
        img_bytes = full_path.read_bytes()
        _common.storage_add_style_reference_image(slug, style_ref_slug, full_path.name, img_bytes)
    except Exception as e:
        return f"Error adding image: {e}"
    if reanalyze:
        result = await _impl_reanalyze_style_reference_async(style_ref_slug)
        if result.startswith("Error"):
            return f"Added image but reanalysis failed: {result}"
    return f"Added image `{full_path.name}` to style reference **{sr.name}**."


async def _impl_reanalyze_style_reference_async(style_ref_slug: str) -> str:
    """Re-run V2 analysis on style reference images."""
    logger.info(f"reanalyze_style_reference called with style_ref_slug={style_ref_slug}")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    sr = _common.load_style_reference(slug, style_ref_slug)
    if not sr:
        return f"Error: Style reference '{style_ref_slug}' not found."
    if not sr.images:
        return "Error: Style reference has no images to analyze."
    step_id = emit_tool_thinking(
        "Analyzing style from your images...", sr.name, expertise="Visual Design", status="pending"
    )
    brand_dir = _common.get_brand_dir(slug)
    img_paths = [brand_dir / img for img in sr.images[:2]]
    try:
        analysis = await analyze_style_reference_v2(img_paths)  # type: ignore[arg-type]
        if not analysis:
            emit_tool_thinking(
                "Analysis failed",
                "No result returned",
                expertise="Visual Design",
                status="failed",
                step_id=step_id,
            )
            return "Error: Analysis failed - no result returned."
        sr.analysis = analysis
        sr.updated_at = _dt.utcnow()
        _common.storage_save_style_reference(slug, sr)
        emit_tool_thinking(
            "Style analysis complete",
            "",
            expertise="Visual Design",
            status="complete",
            step_id=step_id,
        )
        return f"Re-analyzed style reference **{sr.name}** with V2 semantic analysis."
    except Exception as e:
        emit_tool_thinking(
            "Analysis failed",
            str(e)[:100],
            expertise="Visual Design",
            status="failed",
            step_id=step_id,
        )
        return f"Error during analysis: {e}"


def _impl_delete_style_reference(style_ref_slug: str, confirm: bool = False) -> str:
    """Delete style reference. Requires confirm=True."""
    logger.info(
        f"delete_style_reference called with style_ref_slug={style_ref_slug}, confirm={confirm}"
    )
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    sr = _common.load_style_reference(slug, style_ref_slug)
    if not sr:
        return f"Error: Style reference '{style_ref_slug}' not found."
    if not confirm:
        return f"This will permanently delete **{sr.name}** and {len(sr.images)} image(s). To confirm, call `delete_style_reference(style_ref_slug, confirm=True)`."
    try:
        _common.storage_delete_style_reference(slug, style_ref_slug)
        return f"Deleted style reference **{sr.name}** (`{style_ref_slug}`)."
    except Exception as e:
        return f"Error deleting style reference: {e}"


# Wrapped style reference tools
@function_tool
def list_style_references() -> str:
    """List all style references for the active brand.
    Returns:
        Formatted list of style references with name, slug, and image count.
    """
    return _impl_list_style_references()


@function_tool
def get_style_reference_detail(style_ref_slug: str) -> str:
    """Get detailed style reference information including analysis.
    Args:
        style_ref_slug: The style reference's slug identifier. Use list_style_references() to see available ones.
    Returns:
        Style reference details including name, description, images, and analysis summary.
    """
    return _impl_get_style_reference_detail(style_ref_slug)


@function_tool
async def create_style_reference(
    name: str, description: str = "", image_path: str | None = None, default_strict: bool = True
) -> str:
    """Create a new style reference for reusable visual styles.
    Args:
        name: Style reference name (e.g., "Hero Centered Product", "Split Banner").
        description: Optional style reference description.
        image_path: Optional path to image within uploads/ folder.
        default_strict: Default strict mode for this style reference (default True).
    Returns:
        Success message with style reference slug, or error message.
    """
    return await _impl_create_style_reference_async(name, description, image_path, default_strict)


@function_tool
async def create_style_references_from_images(
    image_paths: list[str], default_strict: bool = True
) -> str:
    """Create one style reference per image with auto-generated names.
    Use this when user drops multiple images and wants a style reference for each.
    The style reference name is auto-generated by analyzing each image's visual style.
    Args:
        image_paths: List of paths within uploads/ folder. Each creates a separate style reference.
        default_strict: Default strict mode for created style references (default True).
    Returns:
        Summary of created style references and any errors.
    Example:
        create_style_references_from_images(["uploads/banner1.png", "uploads/card.png"])
    """
    return await _impl_create_style_references_from_images_async(image_paths, default_strict)


@function_tool
def update_style_reference(
    style_ref_slug: str,
    name: str | None = None,
    description: str | None = None,
    default_strict: bool | None = None,
) -> str:
    """Update style reference metadata.
    Args:
        style_ref_slug: The style reference's slug identifier.
        name: Optional new name.
        description: Optional new description.
        default_strict: Optional new default strict mode.
    Returns:
        Success message or error.
    """
    return _impl_update_style_reference(style_ref_slug, name, description, default_strict)


@function_tool
async def add_style_reference_image(
    style_ref_slug: str, image_path: str, reanalyze: bool = True
) -> str:
    """Add an image to a style reference from uploads folder.
    Args:
        style_ref_slug: The style reference's slug identifier.
        image_path: Path within uploads/ folder (e.g., "uploads/design.png").
        reanalyze: Re-run V2 analysis after adding image (default True).
    Returns:
        Success message or error.
    """
    return await _impl_add_style_reference_image_async(style_ref_slug, image_path, reanalyze)


@function_tool
async def reanalyze_style_reference(style_ref_slug: str) -> str:
    """Re-run V2 Gemini analysis on style reference images.
    Use when style reference images have changed or you want to refresh the analysis.
    Args:
        style_ref_slug: The style reference's slug identifier.
    Returns:
        Success message or error.
    """
    return await _impl_reanalyze_style_reference_async(style_ref_slug)


@function_tool
def delete_style_reference(style_ref_slug: str, confirm: bool = False) -> str:
    """Delete a style reference and all its files. Requires confirm=True.
    Args:
        style_ref_slug: The style reference's slug identifier.
        confirm: Must be True to actually delete. If False, returns warning.
    Returns:
        Success message, warning, or error.
    """
    return _impl_delete_style_reference(style_ref_slug, confirm)
