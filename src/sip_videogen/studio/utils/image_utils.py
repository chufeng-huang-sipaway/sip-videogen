"""Shared image utility functions for thumbnail and full-resolution image encoding."""

import base64
import io
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .bridge_types import ALLOWED_IMAGE_EXTS, MIME_TYPES, bridge_error, bridge_ok
from .path_utils import resolve_in_dir

# Limit for decompression bomb protection (100MP)
Image.MAX_IMAGE_PIXELS = 100_000_000


def get_image_thumbnail(brand_dir: Path, path: str, path_prefix: str) -> dict:
    """Get base64-encoded 256x256 thumbnail.

    Args:
        brand_dir: Base directory for the brand
        path: Relative path to the image file
        path_prefix: Required prefix for the path (e.g., "products", "templates")

    Returns:
        Bridge response with dataUrl or error
    """
    if not path.startswith(f"{path_prefix}/"):
        return bridge_error(f"Path must start with '{path_prefix}/'")
    resolved, error = resolve_in_dir(brand_dir, path)
    if error or resolved is None:
        return bridge_error(error or "Failed to resolve path")
    if not resolved.exists():
        return bridge_error("Image not found")
    if not resolved.is_file():
        return bridge_error("Path is not a file")
    suffix = resolved.suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTS:
        return bridge_error("Unsupported file type")
    try:
        if suffix == ".svg":
            content = resolved.read_bytes()
            encoded = base64.b64encode(content).decode("utf-8")
            return bridge_ok({"dataUrl": f"data:image/svg+xml;base64,{encoded}"})
        with Image.open(resolved) as img_file:
            img = img_file.convert("RGBA")
            img.thumbnail((256, 256))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return bridge_ok({"dataUrl": f"data:image/png;base64,{encoded}"})
    except UnidentifiedImageError:
        return bridge_error("Cannot decode image file")
    except Image.DecompressionBombError:
        return bridge_error("Image too large")
    except OSError as e:
        return bridge_error(f"Failed to read image: {e}")


def get_image_full(brand_dir: Path, path: str, path_prefix: str) -> dict:
    """Get base64-encoded full-resolution image.

    Args:
        brand_dir: Base directory for the brand
        path: Relative path to the image file
        path_prefix: Required prefix for the path (e.g., "products", "templates")

    Returns:
        Bridge response with dataUrl or error
    """
    if not path.startswith(f"{path_prefix}/"):
        return bridge_error(f"Path must start with '{path_prefix}/'")
    resolved, error = resolve_in_dir(brand_dir, path)
    if error or resolved is None:
        return bridge_error(error or "Failed to resolve path")
    if not resolved.exists():
        return bridge_error("Image not found")
    if not resolved.is_file():
        return bridge_error("Path is not a file")
    suffix = resolved.suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTS:
        return bridge_error("Unsupported file type")
    try:
        content = resolved.read_bytes()
        encoded = base64.b64encode(content).decode("utf-8")
        mime = MIME_TYPES.get(suffix, "image/png")
        return bridge_ok({"dataUrl": f"data:{mime};base64,{encoded}"})
    except OSError as e:
        return bridge_error(f"Failed to read image: {e}")
