"""Style reference management service."""

from __future__ import annotations

import asyncio
import base64
import re
from datetime import datetime
from pathlib import Path

from sip_studio.advisor.style_reference_analyzer import analyze_style_reference_v3
from sip_studio.brands.models import StyleReferenceFull
from sip_studio.brands.storage import (
    add_style_reference_image,
    create_style_reference,
    delete_style_reference,
    delete_style_reference_image,
    get_style_reference_dir,
    list_style_reference_images,
    list_style_references,
    load_style_reference,
    save_style_reference,
    set_primary_style_reference_image,
)
from sip_studio.config.logging import get_logger

from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_IMAGE_EXTS, bridge_error, bridge_ok
from ..utils.decorators import require_brand
from ..utils.image_utils import get_image_full, get_image_thumbnail

logger = get_logger(__name__)


class StyleReferenceService:
    """Style reference CRUD and image operations."""

    def __init__(self, state: BridgeState):
        self._state = state

    @require_brand()
    def get_style_references(self, brand_slug: str | None = None) -> dict:
        """Get list of style references for a brand."""
        try:
            if not brand_slug:
                return bridge_error("Brand slug required")
            srs = list_style_references(brand_slug)
            return bridge_ok(
                {
                    "style_references": [
                        {
                            "slug": s.slug,
                            "name": s.name,
                            "description": s.description,
                            "primary_image": s.primary_image,
                            "default_strict": s.default_strict,
                            "created_at": s.created_at.isoformat(),
                            "updated_at": s.updated_at.isoformat(),
                        }
                        for s in srs
                    ]
                }
            )
        except Exception as e:
            return bridge_error(str(e))

    def get_style_reference(self, sr_slug: str) -> dict:
        """Get detailed style reference information."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            sr = load_style_reference(slug, sr_slug)
            if not sr:
                return bridge_error(f"Style reference '{sr_slug}' not found")
            analysis_data = sr.analysis.model_dump() if sr.analysis else None
            return bridge_ok(
                {
                    "slug": sr.slug,
                    "name": sr.name,
                    "description": sr.description,
                    "images": sr.images,
                    "primary_image": sr.primary_image,
                    "default_strict": sr.default_strict,
                    "analysis": analysis_data,
                    "created_at": sr.created_at.isoformat(),
                    "updated_at": sr.updated_at.isoformat(),
                }
            )
        except Exception as e:
            return bridge_error(str(e))

    def create_style_reference(
        self,
        name: str,
        description: str,
        images: list[dict] | None = None,
        default_strict: bool = True,
    ) -> dict:
        """Create a new style reference."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            if not name.strip():
                return bridge_error("Style reference name is required")
            sr_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            if not sr_slug:
                return bridge_error("Invalid style reference name")
            if load_style_reference(slug, sr_slug):
                return bridge_error(f"Style reference '{sr_slug}' already exists")
            now = datetime.utcnow()
            sr = StyleReferenceFull(
                slug=sr_slug,
                name=name.strip(),
                description=description.strip(),
                images=[],
                primary_image="",
                default_strict=default_strict,
                analysis=None,
                created_at=now,
                updated_at=now,
            )
            create_style_reference(slug, sr)
            # Upload images
            if images:
                for img in images:
                    fn = img.get("filename", "")
                    data_b64 = img.get("data", "")
                    if not fn or not data_b64:
                        continue
                    ext = Path(fn).suffix.lower()
                    if ext not in ALLOWED_IMAGE_EXTS:
                        continue
                    try:
                        content = base64.b64decode(data_b64)
                        add_style_reference_image(slug, sr_slug, fn, content)
                    except Exception as e:
                        logger.warning("Failed to add style reference image %s: %s", fn, e)
            # Run V3 analyzer (color grading DNA) on uploaded images
            sr_loaded = load_style_reference(slug, sr_slug)
            if sr_loaded and sr_loaded.images:
                sr = sr_loaded
                sr_dir = get_style_reference_dir(slug, sr_slug)
                img_paths = [
                    sr_dir / "images" / Path(p).name
                    for p in sr.images
                    if (sr_dir / "images" / Path(p).name).exists()
                ]
                if img_paths:
                    try:
                        analysis = asyncio.get_event_loop().run_until_complete(
                            analyze_style_reference_v3(img_paths[:2])  # type: ignore[arg-type]
                        )
                        if analysis:
                            sr.analysis = analysis
                            sr.updated_at = datetime.utcnow()
                            save_style_reference(slug, sr)
                    except RuntimeError:
                        analysis = asyncio.run(analyze_style_reference_v3(img_paths[:2]))  # type: ignore[arg-type]
                        if analysis:
                            sr.analysis = analysis
                            sr.updated_at = datetime.utcnow()
                            save_style_reference(slug, sr)
            return bridge_ok({"slug": sr_slug})
        except Exception as e:
            return bridge_error(str(e))

    def update_style_reference(
        self,
        sr_slug: str,
        name: str | None = None,
        description: str | None = None,
        default_strict: bool | None = None,
    ) -> dict:
        """Update an existing style reference."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            sr = load_style_reference(slug, sr_slug)
            if not sr:
                return bridge_error(f"Style reference '{sr_slug}' not found")
            if name is not None:
                sr.name = name.strip()
            if description is not None:
                sr.description = description.strip()
            if default_strict is not None:
                sr.default_strict = default_strict
            sr.updated_at = datetime.utcnow()
            save_style_reference(slug, sr)
            return bridge_ok(
                {
                    "slug": sr.slug,
                    "name": sr.name,
                    "description": sr.description,
                    "default_strict": sr.default_strict,
                }
            )
        except Exception as e:
            return bridge_error(str(e))

    def reanalyze_style_reference(self, sr_slug: str) -> dict:
        """Re-run V3 Gemini analysis (color grading DNA) on style reference images."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            sr = load_style_reference(slug, sr_slug)
            if not sr:
                return bridge_error(f"Style reference '{sr_slug}' not found")
            if not sr.images:
                return bridge_error("No images to analyze")
            sr_dir = get_style_reference_dir(slug, sr_slug)
            img_paths = [
                sr_dir / "images" / Path(p).name
                for p in sr.images
                if (sr_dir / "images" / Path(p).name).exists()
            ]
            if not img_paths:
                return bridge_error("No valid image files found")
            try:
                analysis = asyncio.get_event_loop().run_until_complete(
                    analyze_style_reference_v3(img_paths[:2])  # type: ignore[arg-type]
                )
            except RuntimeError:
                analysis = asyncio.run(analyze_style_reference_v3(img_paths[:2]))  # type: ignore[arg-type]
            if not analysis:
                return bridge_error("Analysis failed - check Gemini API key")
            sr.analysis = analysis
            sr.updated_at = datetime.utcnow()
            save_style_reference(slug, sr)
            return bridge_ok({"analysis": analysis.model_dump()})
        except Exception as e:
            return bridge_error(str(e))

    def delete_style_reference(self, sr_slug: str) -> dict:
        """Delete a style reference and all its files."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            deleted = delete_style_reference(slug, sr_slug)
            if not deleted:
                return bridge_error(f"Style reference '{sr_slug}' not found")
            return bridge_ok()
        except Exception as e:
            return bridge_error(str(e))

    def get_style_reference_images(self, sr_slug: str) -> dict:
        """Get list of images for a style reference."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            images = list_style_reference_images(slug, sr_slug)
            return bridge_ok({"images": images})
        except Exception as e:
            return bridge_error(str(e))

    def upload_style_reference_image(self, sr_slug: str, filename: str, data_base64: str) -> dict:
        """Upload an image to a style reference."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            if "/" in filename or "\\" in filename:
                return bridge_error("Invalid filename")
            ext = Path(filename).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTS:
                return bridge_error("Unsupported file type")
            content = base64.b64decode(data_base64)
            brand_rel_path = add_style_reference_image(slug, sr_slug, filename, content)
            return bridge_ok({"path": brand_rel_path})
        except Exception as e:
            return bridge_error(str(e))

    def delete_style_reference_image(self, sr_slug: str, filename: str) -> dict:
        """Delete a style reference image."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            deleted = delete_style_reference_image(slug, sr_slug, filename)
            if not deleted:
                return bridge_error(f"Image '{filename}' not found")
            return bridge_ok()
        except Exception as e:
            return bridge_error(str(e))

    def set_primary_style_reference_image(self, sr_slug: str, filename: str) -> dict:
        """Set the primary image for a style reference."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            sr = load_style_reference(slug, sr_slug)
            if not sr:
                return bridge_error(f"Style reference '{sr_slug}' not found")
            brand_rel_path = f"style_references/{sr_slug}/images/{filename}"
            if brand_rel_path not in sr.images:
                return bridge_error(f"Image '{filename}' not found in style reference")
            success = set_primary_style_reference_image(slug, sr_slug, brand_rel_path)
            if not success:
                return bridge_error("Failed to set primary image")
            return bridge_ok()
        except Exception as e:
            return bridge_error(str(e))

    def get_style_reference_image_thumbnail(self, path: str) -> dict:
        """Get base64-encoded thumbnail for a style reference image."""
        brand_dir, err = self._state.get_brand_dir()
        if err or brand_dir is None:
            return bridge_error(err or "No brand selected")
        return get_image_thumbnail(brand_dir, path, "style_references")

    def get_style_reference_image_full(self, path: str) -> dict:
        """Get base64-encoded full-resolution style reference image."""
        brand_dir, err = self._state.get_brand_dir()
        if err or brand_dir is None:
            return bridge_error(err or "No brand selected")
        return get_image_full(brand_dir, path, "style_references")
