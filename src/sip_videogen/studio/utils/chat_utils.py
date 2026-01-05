"""Chat attachment and message preparation utilities."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Callable

from sip_videogen.advisor.image_analyzer import analyze_image, format_analysis_for_message
from sip_videogen.config.logging import get_logger

from .bridge_types import ALLOWED_IMAGE_EXTS, ALLOWED_TEXT_EXTS

logger = get_logger(__name__)
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024  # 8 MB cap per file


async def process_attachments(
    attachments: list[dict] | None,
    brand_dir: Path,
    resolve_assets_fn: Callable,
    resolve_docs_fn: Callable,
) -> list[tuple[str, str, Path, bool]]:
    """Process attachments and return (filename, rel_path, full_path, is_image) tuples."""
    saved: list[tuple[str, str, Path, bool]] = []
    if not attachments:
        return saved
    upload_dir = brand_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    for idx, att in enumerate(attachments):
        if not isinstance(att, dict):
            continue
        name = att.get("name") or f"attachment-{idx + 1}"
        safe_name = Path(name).name or f"attachment-{idx + 1}"
        rel_path: str | None = None
        full_path: Path | None = None
        data_b64 = att.get("data")
        ref_path = att.get("path")
        if data_b64:
            try:
                content = base64.b64decode(data_b64)
                if len(content) > MAX_ATTACHMENT_BYTES:
                    continue
                suffix = Path(safe_name).suffix
                allowed = ALLOWED_IMAGE_EXTS | ALLOWED_TEXT_EXTS
                if suffix and suffix.lower() not in allowed:
                    continue
                stem = Path(safe_name).stem
                unique_name = f"{stem}-{int(time.time() * 1000)}{suffix}"
                target = upload_dir / unique_name
                target.write_bytes(content)
                rel_path = target.relative_to(brand_dir).as_posix()
                full_path = target
                safe_name = unique_name
            except Exception as e:
                logger.debug("Failed to decode/write attachment %s: %s", safe_name, e)
                continue
        elif ref_path:
            rp = Path(ref_path)
            # Allow absolute paths, but restrict them to within the active brand directory.
            if rp.is_absolute():
                try:
                    resolved = rp.resolve()
                    resolved.relative_to(brand_dir.resolve())
                    if resolved.exists():
                        rel_path = resolved.relative_to(brand_dir).as_posix()
                        full_path = resolved
                        safe_name = resolved.name
                except Exception as e:
                    logger.debug("Failed to resolve absolute path %s: %s", rp, e)
            if not full_path:
                resolved, error = resolve_assets_fn(ref_path)
                if error:
                    resolved, error = resolve_docs_fn(ref_path)
                if not error and resolved and resolved.exists():
                    rel_path = resolved.relative_to(brand_dir).as_posix()
                    full_path = resolved
                    safe_name = resolved.name
        if rel_path and full_path:
            is_image = full_path.suffix.lower() in ALLOWED_IMAGE_EXTS
            saved.append((safe_name, rel_path, full_path, is_image))
    return saved


async def analyze_and_format_attachments(
    saved_attachments: list[tuple[str, str, Path, bool]], brand_dir: Path
) -> str:
    """Analyze images with Gemini Vision and format for agent message."""
    analyses: list[tuple[str, str, dict | None]] = []
    for filename, rel_path, full_path, is_image in saved_attachments:
        if is_image and full_path.suffix.lower() not in {".svg", ".gif"}:
            try:
                analysis = await analyze_image(full_path)
                analyses.append((filename, rel_path, analysis))
                # Cache analysis for product tools
                if analysis is not None and rel_path.startswith("uploads/"):
                    try:
                        ap = full_path.with_name(f"{full_path.name}.analysis.json")
                        ap.write_text(json.dumps(analysis, indent=2, ensure_ascii=False))
                    except Exception as e:
                        logger.debug(
                            "Failed to write upload analysis cache for %s: %s", full_path, e
                        )
            except Exception as e:
                logger.warning(f"Image analysis failed for {filename}: {e}")
                analyses.append((filename, rel_path, None))
        else:
            analyses.append((filename, rel_path, None))
    return format_analysis_for_message(analyses)


def encode_new_images(paths: list[str], get_image_metadata_fn: Callable) -> list[dict]:
    """Encode newly generated images to base64 with metadata."""

    image_data: list[dict] = []
    for img_path in paths[:4]:
        try:
            path = Path(img_path)
            if not path.exists() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            content = path.read_bytes()
            encoded = base64.b64encode(content).decode("utf-8")
            mime = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }.get(path.suffix.lower(), "image/png")
            metadata = get_image_metadata_fn(img_path)
            image_data.append(
                {"url": f"data:{mime};base64,{encoded}", "path": str(path), "metadata": metadata}
            )
        except Exception as e:
            logger.debug("Failed to encode image %s: %s", img_path, e)
    return image_data


def encode_new_videos(paths: list[str], get_video_metadata_fn: Callable) -> list[dict]:
    """Encode newly generated videos to base64 with metadata.

    Args:
        paths: List of video file paths
        get_video_metadata_fn: Function to get video metadata by path

    Returns:
        List of dicts with url (base64 data URL) and metadata
    """
    video_exts = {".mp4", ".mov", ".webm"}
    mime_types = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
    video_data: list[dict] = []
    for vid_path in paths[:4]:  # Limit to 4 videos
        try:
            path = Path(vid_path)
            if not path.exists() or path.suffix.lower() not in video_exts:
                continue
            content = path.read_bytes()
            encoded = base64.b64encode(content).decode("utf-8")
            mime = mime_types.get(path.suffix.lower(), "video/mp4")
            metadata = get_video_metadata_fn(vid_path)
            video_data.append(
                {
                    "url": f"data:{mime};base64,{encoded}",
                    "path": str(path),
                    "filename": path.name,
                    "metadata": metadata,
                }
            )
        except Exception as e:
            logger.debug("Failed to encode video %s: %s", vid_path, e)
    return video_data
