"""Asset (image/video) management service."""

from __future__ import annotations

import base64
import hashlib
import logging
import subprocess
import sys
from pathlib import Path

from sip_studio.brands.memory import list_brand_assets
from sip_studio.brands.storage import get_active_brand
from sip_studio.brands.storage import save_asset as storage_save_asset

from ..state import BridgeState
from ..utils.bridge_types import (
    ALLOWED_IMAGE_EXTS,
    ALLOWED_VIDEO_EXTS,
    ASSET_CATEGORIES,
    MIME_TYPES,
    VIDEO_MIME_TYPES,
    bridge_error,
    bridge_ok,
)
from ..utils.decorators import require_brand
from ..utils.os_utils import reveal_in_file_manager
from ..utils.path_utils import resolve_assets_path, resolve_in_dir

logger = logging.getLogger(__name__)


def _get_thumb_cache_dir() -> Path:
    """Get or create thumbnail cache directory."""
    d = Path.home() / ".sip-studio" / "cache" / "thumbnails"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_cache_key(source_path: Path) -> str:
    """Generate cache key from source path + mtime for auto-invalidation."""
    mtime = int(source_path.stat().st_mtime)
    key = f"{source_path}:{mtime}"
    return hashlib.md5(key.encode()).hexdigest()


def _move_to_trash(path: Path) -> bool:
    """Move file to system trash. Returns True on success."""
    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["osascript", "-e", f'tell application "Finder" to delete POSIX file "{path}"'],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
    else:
        path.unlink()
        return True


class AssetService:
    """Asset (image/video) file operations."""

    def __init__(self, state: BridgeState):
        self._state = state

    def _resolve_image_path(self, image_path: str) -> tuple[Path | None, str | None]:
        """Resolve an image path within the active brand directory."""
        brand_dir, err = self._state.get_brand_dir()
        if err or brand_dir is None:
            return None, err or "No brand selected"
        path = Path(image_path)
        resolved: Path | None = None
        if path.is_absolute():
            resolved = path.resolve()
        else:
            resolved, error = resolve_in_dir(brand_dir, image_path)
            if error or resolved is None:
                return None, error or "Path resolution failed"
        if resolved is None:
            return None, "Path resolution failed"
        try:
            resolved.relative_to(brand_dir.resolve())
        except ValueError:
            return None, "Invalid path: outside brand directory"
        return resolved, None

    @require_brand(param_name="slug")
    def get_assets(self, slug: str | None = None) -> dict:
        """Get asset tree for a brand."""
        try:
            if not slug:
                return bridge_error("Brand slug required")
            tree = []
            for category in ASSET_CATEGORIES:
                assets = list_brand_assets(slug, category=category)
                children = []
                for asset in assets:
                    filename = asset["filename"]
                    fp = Path(asset["path"])
                    size = fp.stat().st_size if fp.exists() else 0
                    asset_type = asset.get("type", "image")
                    children.append(
                        {
                            "name": filename,
                            "type": asset_type,
                            "path": f"{category}/{filename}",
                            "size": size,
                        }
                    )
                tree.append(
                    {"name": category, "type": "folder", "path": category, "children": children}
                )
            return bridge_ok({"tree": tree})
        except Exception as e:
            return bridge_error(str(e))

    def get_asset_thumbnail(self, relative_path: str) -> dict:
        """Get base64-encoded thumbnail for an asset with disk caching."""
        try:
            brand_dir, err = self._state.get_brand_dir()
            if err or brand_dir is None:
                return bridge_error(err or "No brand selected")
            rp = Path(relative_path)
            resolved: Path | None = None
            if rp.is_absolute():
                resolved = rp.resolve()
                try:
                    resolved.relative_to((brand_dir / "assets").resolve())
                except ValueError:
                    return bridge_error("Invalid path: outside assets directory")
            else:
                resolved, error = resolve_assets_path(brand_dir, relative_path)
                if error or resolved is None:
                    return bridge_error(error or "Path resolution failed")
            if resolved is None or not resolved.exists():
                return bridge_error("Asset not found")
            suffix = resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:
                return bridge_error("Unsupported file type")
            if suffix == ".svg":
                content = resolved.read_bytes()
                enc = base64.b64encode(content).decode("utf-8")
                return bridge_ok({"dataUrl": f"data:image/svg+xml;base64,{enc}"})
            # Check disk cache
            cache_key = _get_cache_key(resolved)
            cache_path = _get_thumb_cache_dir() / f"{cache_key}.webp"
            if cache_path.exists():
                enc = base64.b64encode(cache_path.read_bytes()).decode("utf-8")
                return bridge_ok({"dataUrl": f"data:image/webp;base64,{enc}"})
            # Generate and cache as WebP
            from PIL import Image

            with Image.open(resolved) as img_file:
                im = img_file.convert("RGBA")
                im.thumbnail((256, 256))
                im.save(cache_path, format="WEBP", quality=85)
                enc = base64.b64encode(cache_path.read_bytes()).decode("utf-8")
            return bridge_ok({"dataUrl": f"data:image/webp;base64,{enc}"})
        except Exception as e:
            return bridge_error(str(e))

    def get_asset_full(self, relative_path: str) -> dict:
        """Get base64-encoded full-resolution image for an asset."""
        try:
            brand_dir, err = self._state.get_brand_dir()
            if err or brand_dir is None:
                return bridge_error(err or "No brand selected")
            rp = Path(relative_path)
            resolved: Path | None = None
            if rp.is_absolute():
                resolved = rp.resolve()
                try:
                    resolved.relative_to((brand_dir / "assets").resolve())
                except ValueError:
                    return bridge_error("Invalid path: outside assets directory")
            else:
                resolved, error = resolve_assets_path(brand_dir, relative_path)
                if error or resolved is None:
                    return bridge_error(error or "Path resolution failed")
            if resolved is None or not resolved.exists():
                return bridge_error("Asset not found")
            suffix = resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:
                return bridge_error("Unsupported file type")
            content = resolved.read_bytes()
            enc = base64.b64encode(content).decode("utf-8")
            mime = MIME_TYPES.get(suffix, "image/png")
            return bridge_ok({"dataUrl": f"data:{mime};base64,{enc}"})
        except Exception as e:
            return bridge_error(str(e))

    def get_image_data(self, image_path: str) -> dict:
        """Get base64-encoded image data for a file under the brand directory."""
        try:
            resolved, error = self._resolve_image_path(image_path)
            if error or resolved is None:
                return bridge_error(error or "Path resolution failed")
            if not resolved.exists():
                return bridge_error("Image not found")
            suffix = resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:
                return bridge_error("Unsupported file type")
            content = resolved.read_bytes()
            enc = base64.b64encode(content).decode("utf-8")
            mime = "image/svg+xml" if suffix == ".svg" else MIME_TYPES.get(suffix, "image/png")
            return bridge_ok({"dataUrl": f"data:{mime};base64,{enc}"})
        except Exception as e:
            return bridge_error(str(e))

    def get_image_metadata(self, image_path: str) -> dict:
        """Get generation metadata for an image.
        Returns bridge_ok with metadata dict or None if no metadata exists.
        Returns bridge_error only for actual failures (not missing metadata).
        """
        from sip_studio.advisor.tools import load_image_metadata

        try:
            resolved, error = self._resolve_image_path(image_path)
            # Fallback: try with assets/ prefix if path not found (frontend may omit it)
            if error or not resolved or not resolved.exists():
                if not image_path.startswith("assets/"):
                    resolved2, error2 = self._resolve_image_path(f"assets/{image_path}")
                    if not error2 and resolved2 and resolved2.exists():
                        resolved, error = resolved2, None
                        logger.debug(
                            f"[get_image_metadata] Resolved with assets/ prefix: {image_path}"
                        )
            if error:
                return bridge_error(error)
            if not resolved or not resolved.exists():
                return bridge_error(f"Image not found: {image_path}")
            # load_image_metadata returns None for missing/corrupt .meta.json
            metadata = load_image_metadata(str(resolved))
            slugs = metadata.get("product_slugs") if metadata else None
            logger.info(
                f"[get_image_metadata] path={image_path}, "
                f"resolved={resolved}, product_slugs={slugs}"
            )
            return bridge_ok(metadata)
        except Exception as e:
            return bridge_error(str(e))

    def get_image_thumbnail(self, image_path: str) -> dict:
        """Get base64-encoded thumbnail for a file under the brand directory with disk caching."""
        try:
            resolved, error = self._resolve_image_path(image_path)
            if error or resolved is None:
                return bridge_error(error or "Path resolution failed")
            if not resolved.exists():
                return bridge_error("Image not found")
            suffix = resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:
                return bridge_error("Unsupported file type")
            if suffix == ".svg":
                content = resolved.read_bytes()
                enc = base64.b64encode(content).decode("utf-8")
                return bridge_ok({"dataUrl": f"data:image/svg+xml;base64,{enc}"})
            # Check disk cache
            cache_key = _get_cache_key(resolved)
            cache_path = _get_thumb_cache_dir() / f"{cache_key}.webp"
            if cache_path.exists():
                enc = base64.b64encode(cache_path.read_bytes()).decode("utf-8")
                return bridge_ok({"dataUrl": f"data:image/webp;base64,{enc}"})
            # Generate and cache as WebP
            from PIL import Image

            with Image.open(resolved) as img_file:
                im = img_file.convert("RGBA")
                im.thumbnail((256, 256))
                im.save(cache_path, format="WEBP", quality=85)
                enc = base64.b64encode(cache_path.read_bytes()).decode("utf-8")
            return bridge_ok({"dataUrl": f"data:image/webp;base64,{enc}"})
        except Exception as e:
            return bridge_error(str(e))

    def open_asset_in_finder(self, relative_path: str) -> dict:
        """Open an asset in Finder."""
        try:
            brand_dir, err = self._state.get_brand_dir()
            if err or brand_dir is None:
                return bridge_error(err or "No brand selected")
            resolved, error = resolve_assets_path(brand_dir, relative_path)
            if error or resolved is None:
                return bridge_error(error or "Path resolution failed")
            if not resolved.exists():
                return bridge_error("Asset not found")
            if resolved.suffix.lower() not in (ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS):
                return bridge_error("Unsupported file type")
            reveal_in_file_manager(resolved)
            return bridge_ok()
        except Exception as e:
            return bridge_error(str(e))

    def delete_asset(self, relative_path: str) -> dict:
        """Move an asset file to system trash."""
        try:
            brand_dir, err = self._state.get_brand_dir()
            if err or brand_dir is None:
                return bridge_error(err or "No brand selected")
            resolved, error = resolve_assets_path(brand_dir, relative_path)
            if error or resolved is None:
                return bridge_error(error or "Path resolution failed")
            if not resolved.exists():
                return bridge_error("Asset not found")
            if resolved.is_dir():
                return bridge_error("Cannot delete folders")
            if resolved.suffix.lower() not in (ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS):
                return bridge_error("Unsupported file type")
            if not _move_to_trash(resolved):
                return bridge_error("Failed to move to trash")
            return bridge_ok()
        except Exception as e:
            return bridge_error(str(e))

    def rename_asset(self, relative_path: str, new_name: str) -> dict:
        """Rename an asset file."""
        try:
            brand_dir, err = self._state.get_brand_dir()
            if err or brand_dir is None:
                return bridge_error(err or "No brand selected")
            resolved, error = resolve_assets_path(brand_dir, relative_path)
            if error or resolved is None:
                return bridge_error(error or "Path resolution failed")
            if not resolved.exists():
                return bridge_error("Asset not found")
            if resolved.suffix.lower() not in (ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS):
                return bridge_error("Unsupported file type")
            if "/" in new_name or "\\" in new_name:
                return bridge_error("Invalid filename")
            if Path(new_name).suffix.lower() not in (ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS):
                return bridge_error("Unsupported file type")
            new_path = resolved.parent / new_name
            if new_path.exists():
                return bridge_error(f"File already exists: {new_name}")
            resolved.rename(new_path)
            return bridge_ok({"newPath": f"{resolved.parent.name}/{new_name}"})
        except Exception as e:
            return bridge_error(str(e))

    def upload_asset(self, filename: str, data_base64: str, category: str = "generated") -> dict:
        """Upload a file to brand's assets directory."""
        try:
            slug = get_active_brand()
            if not slug:
                return bridge_error("No brand selected")
            content = base64.b64decode(data_base64)
            rel_path, err = storage_save_asset(slug, category, filename, content)
            if err:
                return bridge_error(err)
            return bridge_ok({"path": rel_path})
        except Exception as e:
            return bridge_error(str(e))

    def get_video_data(self, relative_path: str) -> dict:
        """Get base64-encoded video data.

        Args:
            relative_path: Path relative to brand assets (e.g., "video/scene_001.mp4")

        Returns:
            dict with dataUrl containing base64-encoded video data
        """
        try:
            brand_dir, err = self._state.get_brand_dir()
            if err or brand_dir is None:
                return bridge_error(err or "No brand selected")
            resolved, error = resolve_assets_path(brand_dir, relative_path)
            if error or resolved is None:
                return bridge_error(error or "Path resolution failed")
            if not resolved.exists():
                return bridge_error("Video not found")
            suffix = resolved.suffix.lower()
            if suffix not in ALLOWED_VIDEO_EXTS:
                return bridge_error("Unsupported video type")
            content = resolved.read_bytes()
            enc = base64.b64encode(content).decode("utf-8")
            mime = VIDEO_MIME_TYPES.get(suffix, "video/mp4")
            return bridge_ok(
                {
                    "dataUrl": f"data:{mime};base64,{enc}",
                    "path": str(resolved),
                    "filename": resolved.name,
                }
            )
        except Exception as e:
            return bridge_error(str(e))

    def get_video_path(self, relative_path: str) -> dict:
        """Get the absolute file path for a video (for local playback).
        Args:
            relative_path: Path (relative to brand assets or absolute)
        Returns:
            dict with absolute path to the video file
        """
        try:
            brand_dir, err = self._state.get_brand_dir()
            if err or brand_dir is None:
                return bridge_error(err or "No brand selected")
            rp = Path(relative_path)
            resolved: Path | None = None
            if rp.is_absolute():
                resolved = rp.resolve()
                try:
                    resolved.relative_to((brand_dir / "assets").resolve())
                except ValueError:
                    return bridge_error("Invalid path: outside assets directory")
            else:
                resolved, error = resolve_assets_path(brand_dir, relative_path)
                if error or resolved is None:
                    return bridge_error(error or "Path resolution failed")
            if resolved is None or not resolved.exists():
                return bridge_error("Video not found")
            suffix = resolved.suffix.lower()
            if suffix not in ALLOWED_VIDEO_EXTS:
                return bridge_error("Unsupported video type")
            return bridge_ok(
                {
                    "path": str(resolved),
                    "filename": resolved.name,
                    "file_url": resolved.resolve().as_uri(),
                }
            )
        except Exception as e:
            return bridge_error(str(e))

    def replace_asset(self, original_path: str, new_path: str) -> dict:
        """Backup-first replace: rename original→backup, move new→dest, delete backup.
        If new file has different extension, the destination keeps the new extension.
        """
        import shutil
        import time

        try:
            brand_dir, err = self._state.get_brand_dir()
            if err or brand_dir is None:
                return bridge_error(err or "No brand selected")
            orig, err1 = resolve_assets_path(brand_dir, original_path)
            if err1 or orig is None:
                return bridge_error(err1 or "Path resolution failed")
            new, err2 = resolve_assets_path(brand_dir, new_path)
            if err2 or new is None:
                return bridge_error(err2 or "Path resolution failed")
            if not orig.exists():
                return bridge_error("Original asset not found")
            if not new.exists():
                return bridge_error("New asset not found")
            # Backup name with timestamp to avoid collisions
            backup = orig.parent / f"{orig.stem}.backup.{int(time.time())}{orig.suffix}"
            # Destination keeps new file's extension (e.g. jpg→png keeps png)
            dest = orig.parent / f"{orig.stem}{new.suffix}"
            try:
                orig.rename(backup)
                shutil.move(str(new), str(dest))
                backup.unlink()
                # Return relative path from assets dir
                rel = dest.relative_to(brand_dir / "assets")
                return bridge_ok({"path": str(rel)})
            except Exception as e:
                # Cleanup partial dest if exists
                if dest.exists() and dest != backup:
                    try:
                        dest.unlink()
                    except Exception:
                        pass
                # Restore backup
                if backup.exists():
                    try:
                        backup.rename(orig)
                    except Exception:
                        pass
                return bridge_error(str(e))
        except Exception as e:
            return bridge_error(str(e))
