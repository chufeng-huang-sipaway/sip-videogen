"""Template management tools."""

from __future__ import annotations

import re
from datetime import datetime as _dt
from pathlib import Path

from agents import function_tool

from sip_videogen.advisor.template_analyzer import analyze_template_v2
from sip_videogen.brands.models import TemplateFull
from sip_videogen.config.logging import get_logger

from . import _common

logger = get_logger(__name__)


def _impl_list_templates() -> str:
    """List all templates for active brand."""
    logger.info("list_templates called")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    templates = _common.storage_list_templates(slug)
    if not templates:
        return "No templates found for this brand."
    lines = ["**Templates:**"]
    for t in templates:
        img_count = 1 if t.primary_image else 0
        lines.append(f"- **{t.name}** (`{t.slug}`) - {img_count} image(s)")
    return "\n".join(lines)


def _impl_get_template_detail(template_slug: str) -> str:
    """Get detailed template info including analysis."""
    logger.info(f"get_template_detail called with template_slug={template_slug}")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    t = _common.load_template(slug, template_slug)
    if not t:
        return f"Error: Template '{template_slug}' not found."
    lines = [
        f"# {t.name}",
        f"**Slug:** `{t.slug}`",
        f"**Description:** {t.description or '(none)'}",
        f"**Default Strict:** {t.default_strict}",
        f"**Images:** {len(t.images)}",
    ]
    if t.primary_image:
        lines.append(f"**Primary Image:** {t.primary_image}")
    if t.analysis:
        lines.append("\n## Analysis")
        if hasattr(t.analysis, "copywriting"):
            lines.append("**V2 Semantic Analysis Available**")
            if t.analysis.copywriting:
                cw = t.analysis.copywriting
                if cw.headline:
                    lines.append(f'- Headline: "{cw.headline}"')
                if cw.cta:
                    lines.append(f'- CTA: "{cw.cta}"')
        else:
            lines.append("**V1 Geometry Analysis Available**")
    return "\n".join(lines)


async def _generate_template_name(image_path: Path) -> str:
    """Generate descriptive template name from image using Gemini."""
    try:
        from google import genai
        from google.genai import types

        settings = _common.get_settings()
        client = genai.Client(api_key=settings.gemini_api_key)
        img_bytes = image_path.read_bytes()
        prompt = "Analyze this design template image and suggest a short descriptive name (2-4 words) that captures its layout style. Examples: 'Hero Centered Product', 'Split Two-Column', 'Minimalist Product Card'. Reply with ONLY the name, nothing else."
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Part.from_bytes(data=img_bytes, mime_type="image/png"), prompt],
        )
        name = resp.text.strip().strip('"').strip("'")
        return name if name else "New Template"
    except Exception as e:
        logger.warning(f"Failed to generate template name: {e}")
        return "New Template"


async def _impl_create_template_async(
    name: str, description: str = "", image_path: str | None = None, default_strict: bool = True
) -> str:
    """Create a new template."""
    logger.info(f"create_template called with name={name}")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    template_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not template_slug:
        return "Error: Invalid template name."
    existing = _common.load_template_summary(slug, template_slug)
    if existing:
        return f"Error: Template '{template_slug}' already exists."
    now = _dt.utcnow()
    template = TemplateFull(
        slug=template_slug,
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
        _common.storage_create_template(slug, template)
    except Exception as e:
        return f"Error creating template: {e}"
    if image_path:
        result = await _impl_add_template_image_async(template_slug, image_path, reanalyze=True)
        if result.startswith("Error"):
            return f"Created template but failed to add image: {result}"
    return f"Created template **{name}** (`{template_slug}`)."


async def _impl_create_templates_from_images_async(
    image_paths: list[str], default_strict: bool = True
) -> str:
    """Create one template per image with auto-generated names."""
    logger.info(f"create_templates_from_images called with {len(image_paths)} images")
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
        name = await _generate_template_name(full_path)
        base_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "template"
        template_slug = base_slug
        counter = 1
        while _common.load_template_summary(slug, template_slug):
            template_slug = f"{base_slug}-{counter}"
            counter += 1
        now = _dt.utcnow()
        template = TemplateFull(
            slug=template_slug,
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
            _common.storage_create_template(slug, template)
            img_bytes = full_path.read_bytes()
            _common.storage_add_template_image(slug, template_slug, full_path.name, img_bytes)
            t = _common.load_template(slug, template_slug)
            if t and t.images:
                img_full = brand_dir / t.images[0]
                analysis = await analyze_template_v2([img_full])
                if analysis:
                    t.analysis = analysis
                    t.updated_at = _dt.utcnow()
                    _common.storage_save_template(slug, t)
            created.append(f"**{name}** (`{template_slug}`)")
        except Exception as e:
            errors.append(f"{img_path}: {e}")
    result_lines = []
    if created:
        result_lines.append(
            f"Created {len(created)} template(s):\n" + "\n".join(f"- {c}" for c in created)
        )
    if errors:
        result_lines.append("\nErrors:\n" + "\n".join(f"- {e}" for e in errors))
    return "\n".join(result_lines) if result_lines else "No templates created."


def _impl_update_template(
    template_slug: str,
    name: str | None = None,
    description: str | None = None,
    default_strict: bool | None = None,
) -> str:
    """Update template metadata."""
    logger.info(f"update_template called with template_slug={template_slug}")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    t = _common.load_template(slug, template_slug)
    if not t:
        return f"Error: Template '{template_slug}' not found."
    if name is not None:
        t.name = name
    if description is not None:
        t.description = description
    if default_strict is not None:
        t.default_strict = default_strict
    t.updated_at = _dt.utcnow()
    try:
        _common.storage_save_template(slug, t)
    except Exception as e:
        return f"Error updating template: {e}"
    return f"Updated template **{t.name}** (`{template_slug}`)."


async def _impl_add_template_image_async(
    template_slug: str, image_path: str, reanalyze: bool = True
) -> str:
    """Add image to template from uploads folder."""
    logger.info(
        f"add_template_image called with template_slug={template_slug}, image_path={image_path}"
    )
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    t = _common.load_template(slug, template_slug)
    if not t:
        return f"Error: Template '{template_slug}' not found."
    if not image_path.startswith("uploads/"):
        return "Error: image_path must be within uploads/ folder."
    brand_dir = _common.get_brand_dir(slug)
    full_path = brand_dir / image_path
    if not full_path.exists():
        return f"Error: File not found: {image_path}"
    try:
        img_bytes = full_path.read_bytes()
        _common.storage_add_template_image(slug, template_slug, full_path.name, img_bytes)
    except Exception as e:
        return f"Error adding image: {e}"
    if reanalyze:
        result = await _impl_reanalyze_template_async(template_slug)
        if result.startswith("Error"):
            return f"Added image but reanalysis failed: {result}"
    return f"Added image `{full_path.name}` to template **{t.name}**."


async def _impl_reanalyze_template_async(template_slug: str) -> str:
    """Re-run V2 analysis on template images."""
    logger.info(f"reanalyze_template called with template_slug={template_slug}")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    t = _common.load_template(slug, template_slug)
    if not t:
        return f"Error: Template '{template_slug}' not found."
    if not t.images:
        return "Error: Template has no images to analyze."
    brand_dir = _common.get_brand_dir(slug)
    img_paths = [brand_dir / img for img in t.images[:2]]
    try:
        analysis = await analyze_template_v2(img_paths)
        if not analysis:
            return "Error: Analysis failed - no result returned."
        t.analysis = analysis
        t.updated_at = _dt.utcnow()
        _common.storage_save_template(slug, t)
        return f"Re-analyzed template **{t.name}** with V2 semantic analysis."
    except Exception as e:
        return f"Error during analysis: {e}"


def _impl_delete_template(template_slug: str, confirm: bool = False) -> str:
    """Delete template. Requires confirm=True."""
    logger.info(f"delete_template called with template_slug={template_slug}, confirm={confirm}")
    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    t = _common.load_template(slug, template_slug)
    if not t:
        return f"Error: Template '{template_slug}' not found."
    if not confirm:
        return f"This will permanently delete **{t.name}** and {len(t.images)} image(s). To confirm, call `delete_template(template_slug, confirm=True)`."
    try:
        _common.storage_delete_template(slug, template_slug)
        return f"Deleted template **{t.name}** (`{template_slug}`)."
    except Exception as e:
        return f"Error deleting template: {e}"


# Wrapped template tools
@function_tool
def list_templates() -> str:
    """List all templates for the active brand.
    Returns:
        Formatted list of templates with name, slug, and image count.
    """
    return _impl_list_templates()


@function_tool
def get_template_detail(template_slug: str) -> str:
    """Get detailed template information including analysis.
    Args:
        template_slug: The template's slug identifier. Use list_templates() to see available templates.
    Returns:
        Template details including name, description, images, and analysis summary.
    """
    return _impl_get_template_detail(template_slug)


@function_tool
async def create_template(
    name: str, description: str = "", image_path: str | None = None, default_strict: bool = True
) -> str:
    """Create a new template for reusable layouts.
    Args:
        name: Template name (e.g., "Hero Centered Product", "Split Banner").
        description: Optional template description.
        image_path: Optional path to image within uploads/ folder.
        default_strict: Default strict mode for this template (default True).
    Returns:
        Success message with template slug, or error message.
    """
    return await _impl_create_template_async(name, description, image_path, default_strict)


@function_tool
async def create_templates_from_images(image_paths: list[str], default_strict: bool = True) -> str:
    """Create one template per image with auto-generated names.
    Use this when user drops multiple images and wants a template for each.
    The template name is auto-generated by analyzing each image's layout.
    Args:
        image_paths: List of paths within uploads/ folder. Each creates a separate template.
        default_strict: Default strict mode for created templates (default True).
    Returns:
        Summary of created templates and any errors.
    Example:
        create_templates_from_images(["uploads/banner1.png", "uploads/card.png"])
    """
    return await _impl_create_templates_from_images_async(image_paths, default_strict)


@function_tool
def update_template(
    template_slug: str,
    name: str | None = None,
    description: str | None = None,
    default_strict: bool | None = None,
) -> str:
    """Update template metadata.
    Args:
        template_slug: The template's slug identifier.
        name: Optional new name.
        description: Optional new description.
        default_strict: Optional new default strict mode.
    Returns:
        Success message or error.
    """
    return _impl_update_template(template_slug, name, description, default_strict)


@function_tool
async def add_template_image(template_slug: str, image_path: str, reanalyze: bool = True) -> str:
    """Add an image to a template from uploads folder.
    Args:
        template_slug: The template's slug identifier.
        image_path: Path within uploads/ folder (e.g., "uploads/design.png").
        reanalyze: Re-run V2 analysis after adding image (default True).
    Returns:
        Success message or error.
    """
    return await _impl_add_template_image_async(template_slug, image_path, reanalyze)


@function_tool
async def reanalyze_template(template_slug: str) -> str:
    """Re-run V2 Gemini analysis on template images.
    Use when template images have changed or you want to refresh the analysis.
    Args:
        template_slug: The template's slug identifier.
    Returns:
        Success message or error.
    """
    return await _impl_reanalyze_template_async(template_slug)


@function_tool
def delete_template(template_slug: str, confirm: bool = False) -> str:
    """Delete a template and all its files. Requires confirm=True.
    Args:
        template_slug: The template's slug identifier.
        confirm: Must be True to actually delete. If False, returns warning.
    Returns:
        Success message, warning, or error.
    """
    return _impl_delete_template(template_slug, confirm)
