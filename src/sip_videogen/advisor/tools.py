"""Universal tools for Brand Marketing Advisor.

These are the 5 basic tools available to the advisor agent:
1. generate_image - Create images via Gemini 3.0 Pro
2. read_file - Read files from brand directory
3. write_file - Write files to brand directory
4. list_files - List files in brand directory
5. load_brand - Load brand identity and context

Tool functions are defined as pure functions (prefixed with _impl_) for testing,
then wrapped with @function_tool for agent use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from agents import function_tool

from sip_videogen.brands.storage import (
    get_active_brand,
    get_brand_dir,
    get_brands_dir,
)
from sip_videogen.brands.storage import (
    load_brand as storage_load_brand,
)
from sip_videogen.config.logging import get_logger
from sip_videogen.config.settings import get_settings

logger = get_logger(__name__)


# =============================================================================
# Path Resolution Helper
# =============================================================================


def _resolve_brand_path(relative_path: str) -> Path | None:
    """Resolve a relative path within the active brand directory.

    Args:
        relative_path: Path relative to brand directory (e.g., "assets/logo/")

    Returns:
        Absolute Path, or None if no active brand or path escapes.
    """
    brand_slug = get_active_brand()
    if not brand_slug:
        return None

    brand_dir = get_brand_dir(brand_slug)
    resolved = brand_dir / relative_path

    # Security: ensure path doesn't escape brand directory
    try:
        resolved.resolve().relative_to(brand_dir.resolve())
    except ValueError:
        logger.warning(f"Path escapes brand directory: {relative_path}")
        return None

    return resolved


# =============================================================================
# Interaction + Memory State (captured via hooks)
# =============================================================================

# Stored between tool calls and cleared when hooks read them
_pending_interaction: dict | None = None
_pending_memory_update: dict | None = None


def get_pending_interaction() -> dict | None:
    """Get and clear any pending interaction."""
    global _pending_interaction
    result = _pending_interaction
    _pending_interaction = None
    return result


def get_pending_memory_update() -> dict | None:
    """Get and clear any pending memory update."""
    global _pending_memory_update
    result = _pending_memory_update
    _pending_memory_update = None
    return result


# =============================================================================
# Implementation Functions (for testing)
# =============================================================================


async def _impl_generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    filename: str | None = None,
    reference_image: str | None = None,
    validate_identity: bool = False,
    max_retries: int = 3,
) -> str:
    """Implementation of generate_image tool with optional reference-based generation.

    Args:
        prompt: Text description for image generation.
        aspect_ratio: Image aspect ratio.
        filename: Optional output filename (without extension).
        reference_image: Optional path to reference image within brand directory.
        validate_identity: When True with reference_image, validates that the
            generated image preserves object identity from the reference.
        max_retries: Maximum validation attempts (only used with validate_identity).

    Returns:
        Path to saved image, or error message.
    """
    import io

    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    settings = get_settings()
    brand_slug = get_active_brand()

    # Determine output path
    if brand_slug:
        output_dir = get_brand_dir(brand_slug) / "assets" / "generated"
    else:
        output_dir = get_brands_dir() / "_temp"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename if not provided
    if not filename:
        import time

        filename = f"image_{int(time.time())}"

    output_path = output_dir / f"{filename}.png"

    # Resolve and load reference image if provided
    reference_image_bytes: bytes | None = None
    if reference_image:
        reference_path = _resolve_brand_path(reference_image)
        if reference_path is None:
            return f"Error: No active brand or invalid path: {reference_image}"
        if not reference_path.exists():
            return f"Error: Reference image not found: {reference_image}"
        try:
            reference_image_bytes = reference_path.read_bytes()
            logger.info(
                f"Loaded reference image: {reference_image} ({len(reference_image_bytes)} bytes)"
            )
        except Exception as e:
            return f"Error reading reference image: {e}"

    try:
        client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)

        # Use validation loop if enabled and reference provided
        if validate_identity and reference_image_bytes:
            from sip_videogen.advisor.validation import generate_with_validation

            logger.info(f"Generating with validation (max {max_retries} retries)...")
            return await generate_with_validation(
                client=client,
                prompt=prompt,
                reference_image_bytes=reference_image_bytes,
                output_dir=output_dir,
                filename=filename,
                aspect_ratio=aspect_ratio,
                max_retries=max_retries,
            )

        # Standard generation (with or without reference)
        if reference_image_bytes:
            # Include reference image in contents
            ref_pil = PILImage.open(io.BytesIO(reference_image_bytes))
            contents = [prompt, ref_pil]
            logger.info(f"Generating image with reference: {prompt[:100]}...")
        else:
            contents = prompt
            logger.info(f"Generating image: {prompt[:100]}...")

        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size="2K",
                ),
            ),
        )

        # Extract and save the image
        for part in response.parts:
            if part.inline_data:
                image = part.as_image()
                image.save(str(output_path))
                logger.info(f"Saved image to: {output_path}")
                return str(output_path)

        return "Error: No image generated in response"

    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return f"Error generating image: {str(e)}"


def _impl_read_file(path: str) -> str:
    """Implementation of read_file tool."""
    resolved = _resolve_brand_path(path)

    if resolved is None:
        return "Error: No active brand selected. Use load_brand() first."

    if not resolved.exists():
        return f"Error: File not found: {path}"

    if not resolved.is_file():
        return f"Error: {path} is a directory, not a file. Use list_files() to browse."

    # Check if it's a text file or binary
    text_extensions = {".json", ".md", ".txt", ".yaml", ".yml", ".csv"}

    if resolved.suffix.lower() in text_extensions:
        try:
            content = resolved.read_text(encoding="utf-8")
            return content
        except Exception as e:
            return f"Error reading file: {e}"
    else:
        # Binary file (image, etc.) - just confirm it exists
        size = resolved.stat().st_size
        return f"Binary file exists: {path} ({size} bytes)"


def _impl_write_file(path: str, content: str) -> str:
    """Implementation of write_file tool."""
    resolved = _resolve_brand_path(path)

    if resolved is None:
        return "Error: No active brand selected. Use load_brand() first."

    try:
        # Create parent directories
        resolved.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        resolved.write_text(content, encoding="utf-8")

        logger.info(f"Wrote file: {resolved}")
        return f"Successfully wrote to: {path}"

    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        return f"Error writing file: {e}"


def _impl_list_files(path: str = "", limit: int = 20, offset: int = 0) -> str:
    """Implementation of list_files tool with pagination support."""
    # Parameter validation
    if limit < 1:
        limit = 20  # Reset to default
    if limit > 100:
        limit = 100  # Cap at maximum
    if offset < 0:
        offset = 0  # No negative offsets

    resolved = _resolve_brand_path(path) if path else None

    if resolved is None and path:
        return "Error: No active brand selected. Use load_brand() first."

    if resolved is None:
        # List at brand root
        brand_slug = get_active_brand()
        if not brand_slug:
            return "Error: No active brand selected. Use load_brand() first."
        resolved = get_brand_dir(brand_slug)

    if not resolved.exists():
        return f"Error: Directory not found: {path or '/'}"

    if not resolved.is_dir():
        return f"Error: {path} is a file, not a directory. Use read_file() to read it."

    try:
        items = sorted(resolved.iterdir())
        total_count = len(items)

        # Validate offset
        if offset >= total_count and total_count > 0:
            return (
                f"Error: offset {offset} is past end of directory "
                f"({total_count} items). Use offset 0-{total_count - 1}."
            )

        # Apply pagination
        paginated_items = items[offset : offset + limit]
        lines = []

        for item in paginated_items:
            if item.is_dir():
                # Count items in directory
                count = len(list(item.iterdir()))
                lines.append(f"  {item.name}/ ({count} items)")
            else:
                size = item.stat().st_size
                lines.append(f"  {item.name} ({size} bytes)")

        if not lines and total_count == 0:
            return f"Directory is empty: {path or '/'}"

        # Build header with pagination info
        start_idx = offset + 1
        end_idx = min(offset + limit, total_count)
        display_path = path or "/"
        if total_count <= limit and offset == 0:
            header = f"Contents of {display_path}:\n"
        else:
            header = (
                f"Contents of {display_path} (showing {start_idx}-{end_idx} of {total_count}):\n"
            )

        result = header + "\n".join(lines)

        # Add pagination hint if there are more items
        if offset + limit < total_count:
            next_offset = offset + limit
            if path:
                hint = f'\n\nUse list_files("{path}", offset={next_offset}) to see more.'
            else:
                hint = f"\n\nUse list_files(offset={next_offset}) to see more."
            result += hint

        return result

    except Exception as e:
        logger.error(f"Failed to list directory: {e}")
        return f"Error listing directory: {e}"


def _impl_load_brand(slug: str | None = None) -> str:
    """Implementation of load_brand tool."""
    from sip_videogen.brands.memory import list_brand_assets
    from sip_videogen.brands.storage import (
        list_brands,
        set_active_brand,
    )

    # Get brand slug
    if not slug:
        slug = get_active_brand()

    if not slug:
        # List available brands
        brands = list_brands()
        if not brands:
            return (
                "No brands found. Create a brand first by telling me about your brand, "
                "and I'll help you develop its identity."
            )

        brand_list = "\n".join(f"  - {b.slug}: {b.name}" for b in brands)
        return (
            f"No active brand. Available brands:\n{brand_list}\n\n"
            "Tell me which brand to work with, or describe a new brand to create."
        )

    # Load the brand
    identity = storage_load_brand(slug)
    if identity is None:
        return f"Error: Brand not found: {slug}"

    # Set as active brand
    set_active_brand(slug)

    # Format brand context
    context_parts = []

    # Header
    context_parts.append(f"# Brand: {identity.core.name}")
    context_parts.append(f"*{identity.core.tagline}*\n")

    # Summary
    context_parts.append("## Summary")
    context_parts.append(f"- **Category**: {identity.positioning.market_category}")
    context_parts.append(f"- **Mission**: {identity.core.mission}")
    if identity.voice.tone_attributes:
        context_parts.append(f"- **Tone**: {', '.join(identity.voice.tone_attributes[:3])}")
    context_parts.append("")

    # Visual Identity
    context_parts.append("## Visual Identity")
    if identity.visual.primary_colors:
        colors = ", ".join(f"{c.name} ({c.hex})" for c in identity.visual.primary_colors)
        context_parts.append(f"- **Primary Colors**: {colors}")
    if identity.visual.style_keywords:
        context_parts.append(f"- **Style**: {', '.join(identity.visual.style_keywords)}")
    if identity.visual.overall_aesthetic:
        context_parts.append(f"- **Aesthetic**: {identity.visual.overall_aesthetic[:200]}...")
    context_parts.append("")

    # Voice
    context_parts.append("## Brand Voice")
    context_parts.append(f"- **Personality**: {identity.voice.personality}")
    if identity.voice.key_messages:
        context_parts.append("- **Key Messages**:")
        for msg in identity.voice.key_messages[:3]:
            context_parts.append(f'  - "{msg}"')
    context_parts.append("")

    # Audience
    context_parts.append("## Target Audience")
    context_parts.append(f"- **Primary**: {identity.audience.primary_summary}")
    if identity.audience.demographics:
        demo = identity.audience.demographics
        if demo.age_range:
            context_parts.append(f"- **Age**: {demo.age_range}")
    context_parts.append("")

    # Positioning
    context_parts.append("## Positioning")
    context_parts.append(f"- **UVP**: {identity.positioning.unique_value_proposition}")
    if identity.positioning.positioning_statement:
        context_parts.append(f"- **Statement**: {identity.positioning.positioning_statement}")
    context_parts.append("")

    # Assets - group by category
    try:
        assets = list_brand_assets(slug)
        if assets:
            # Group assets by category
            by_category: dict[str, list[dict]] = {}
            for asset in assets:
                cat = asset.get("category", "other")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(asset)

            context_parts.append("## Available Assets")
            for category, files in sorted(by_category.items()):
                context_parts.append(f"- **{category}**: {len(files)} files")
            context_parts.append("")
    except Exception:
        pass  # Assets listing is optional

    # Values
    if identity.core.values:
        context_parts.append("## Core Values")
        for value in identity.core.values[:5]:
            context_parts.append(f"- **{value.name}**: {value.meaning}")
        context_parts.append("")

    return "\n".join(context_parts)


# =============================================================================
# Wrapped Tools for Agent (with @function_tool decorator)
# =============================================================================


@function_tool
def propose_choices(
    question: str,
    choices: list[str],
    allow_custom: bool = False,
) -> str:
    """Present a multiple-choice question to the user with clickable options.

    Use this tool when you want the user to select from specific options.
    The user will see clickable buttons in the UI. Their selection will be
    returned as the next message in the conversation.

    Args:
        question: The question to ask (e.g., "Which logo style do you prefer?")
        choices: List of 2-5 choices to present as buttons
        allow_custom: If True, show an input field for custom response

    Returns:
        Confirmation that choices are being presented.
    """
    global _pending_interaction

    if len(choices) < 2:
        return "Error: Please provide at least 2 choices"
    if len(choices) > 5:
        choices = choices[:5]

    _pending_interaction = {
        "type": "choices",
        "question": question,
        "choices": choices,
        "allow_custom": allow_custom,
    }

    # Return text for the agent to include in its response
    return f"[Presenting choices to user: {question}]"


@function_tool
def propose_images(
    question: str,
    image_paths: list[str],
    labels: list[str] | None = None,
) -> str:
    """Present images for the user to select from.

    Use this after generating multiple images when you want the user
    to pick their favorite. Images will be shown as clickable cards.

    Args:
        question: The question (e.g., "Which logo do you prefer?")
        image_paths: List of image file paths (relative to brand assets directory,
            e.g. "generated/foo.png")
        labels: Optional short labels for each image (e.g., ["Modern", "Classic"])

    Returns:
        Confirmation that image selection is being presented.
    """
    global _pending_interaction

    if len(image_paths) < 2:
        return "Error: Please provide at least 2 images to choose from"

    # Normalize paths for the UI thumbnail API:
    # - Frontend calls bridge.getAssetThumbnail(path), expects "generated/foo.png"
    # - generate_image returns absolute paths; convert to relative-to-assets
    brand_slug = get_active_brand()
    if brand_slug:
        assets_dir = (get_brand_dir(brand_slug) / "assets").resolve()
        normalized: list[str] = []
        for p in image_paths:
            try:
                candidate = Path(p)
                if candidate.is_absolute():
                    rel = candidate.resolve().relative_to(assets_dir)
                    normalized.append(rel.as_posix())
                else:
                    normalized.append(p)
            except Exception:
                # Skip paths outside assets/ (PyWebView bridge will reject them anyway)
                continue
        image_paths = normalized
        if len(image_paths) < 2:
            return "Error: Please provide at least 2 images within the brand assets folder"

    _pending_interaction = {
        "type": "image_select",
        "question": question,
        "image_paths": image_paths,
        "labels": labels or [f"Option {i + 1}" for i in range(len(image_paths))],
    }

    return f"[Presenting {len(image_paths)} images for user to select]"


@function_tool
async def generate_image(
    prompt: str,
    aspect_ratio: Literal["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"] = "1:1",
    filename: str | None = None,
    reference_image: str | None = None,
    validate_identity: bool = False,
    max_retries: int = 3,
) -> str:
    """Generate an image using Gemini 3.0 Pro.

    Creates a high-quality image from a text prompt. Use for brand assets like
    logos, mascots, lifestyle photos, and marketing materials.

    Args:
        prompt: Detailed description of the image to generate. Be specific about
            style, colors, composition, and what to avoid.
        aspect_ratio: Image aspect ratio. Common choices:
            - "1:1" for logos, mascots, social posts
            - "4:5" for Instagram, lifestyle photos
            - "16:9" for hero images, landing pages
            - "9:16" for stories, vertical content
        filename: Optional filename to save as (without extension).
            If not provided, uses a generated name.
        reference_image: Optional path to a reference image within the brand directory.
            When provided, the generated image will incorporate visual elements from
            this reference to maintain consistency. Path should be relative to the
            brand folder (e.g., "uploads/product.png", "assets/logo/main.png").
        validate_identity: When True AND reference_image is provided, enables a
            validation loop that ensures the generated image preserves the identity
            of objects in the reference. Use when the user needs the EXACT SAME
            object (their specific product, logo, etc.) to appear in the generated
            image, not just something similar.
        max_retries: Maximum attempts for the validation loop (default 3). Only
            used when validate_identity is True. If validation fails after all
            retries, returns the best attempt with a warning.

    Returns:
        Path to the saved image file, or error message if generation fails.
        If validation was enabled but didn't pass, includes a warning about
        potential differences from the reference.
    """
    return await _impl_generate_image(
        prompt, aspect_ratio, filename, reference_image, validate_identity, max_retries
    )


@function_tool
def read_file(path: str) -> str:
    """Read a file from the brand directory.

    Args:
        path: Relative path within the brand directory.
            Examples: "identity.json", "assets/logo/logo_primary.png",
            "uploads/reference.jpg"

    Returns:
        File contents as string (for text files), or
        confirmation that binary file exists (for images/binaries),
        or error message if file not found.
    """
    return _impl_read_file(path)


@function_tool
def write_file(path: str, content: str) -> str:
    """Write content to a file in the brand directory.

    Creates parent directories if they don't exist.

    Args:
        path: Relative path within the brand directory.
            Examples: "identity.json", "memory.json", "notes.md"
        content: Content to write. For JSON, ensure it's valid JSON string.

    Returns:
        Confirmation message or error.
    """
    return _impl_write_file(path, content)


@function_tool
def list_files(path: str = "", limit: int = 20, offset: int = 0) -> str:
    """List files and directories in the brand directory.

    Args:
        path: Relative path within brand directory. Empty string for root.
            Examples: "", "assets/", "assets/logo/"
        limit: Maximum number of items to return (1-100, default 20).
        offset: Number of items to skip for pagination (default 0).

    Returns:
        Formatted list of files and directories with pagination info,
        or error message.
    """
    return _impl_list_files(path, limit, offset)


@function_tool
def load_brand(slug: str | None = None) -> str:
    """Load brand identity and context.

    If no slug is provided, loads the currently active brand.
    Sets the brand as active for subsequent tool calls.

    Args:
        slug: Brand slug to load. If not provided, uses active brand.
            Available brands can be found in ~/.sip-videogen/brands/

    Returns:
        Formatted brand context as markdown, including:
        - Brand summary (name, tagline, category, tone)
        - Visual identity (colors, typography, style)
        - Voice guidelines (personality, messaging)
        - Audience profile
        - Positioning
        - Available assets

        Or error message if brand not found.
    """
    return _impl_load_brand(slug)


@function_tool
def update_memory(
    key: str,
    value: str,
    display_message: str,
) -> str:
    """Record a user preference or learning for future reference.

    Use this when the user expresses a preference, gives feedback,
    or makes a decision that should be remembered for future interactions.

    Examples:
    - User says "I prefer minimalist designs" → remember style preference
    - User says "Don't use red" → remember color restriction
    - User picks a direction → remember that preference

    Args:
        key: Short identifier (e.g., "style_preference", "color_avoid")
        value: The actual preference/learning to store
        display_message: User-friendly confirmation (e.g., "Noted: You prefer minimalist designs")

    Returns:
        Confirmation of memory update.
    """
    global _pending_memory_update
    import json
    from datetime import datetime

    brand_slug = get_active_brand()
    if not brand_slug:
        return "No active brand - cannot save memory"

    memory_path = get_brand_dir(brand_slug) / "memory.json"
    memory = {}
    if memory_path.exists():
        try:
            memory = json.loads(memory_path.read_text())
        except json.JSONDecodeError:
            memory = {}

    memory[key] = {
        "value": value,
        "updated_at": datetime.utcnow().isoformat(),
    }

    memory_path.write_text(json.dumps(memory, indent=2))
    _pending_memory_update = {"message": display_message}

    return f"Memory updated: {key}"


# =============================================================================
# Tool List for Agent
# =============================================================================

# All tools available to the Brand Marketing Advisor
ADVISOR_TOOLS = [
    generate_image,
    read_file,
    write_file,
    list_files,
    load_brand,
    propose_choices,
    propose_images,
    update_memory,
]
