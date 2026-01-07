"""Image status tracking service for workstation curation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from sip_studio.brands.storage import get_brand_dir, load_image_status_raw, save_image_status
from sip_studio.config.logging import get_logger

from ..state import BridgeState
from ..utils.bridge_types import bridge_error, bridge_ok

logger = get_logger(__name__)
ImageStatus = Literal["unsorted", "kept", "trashed"]
STATUS_FILE_NAME = "image_status.json"
CURRENT_VERSION = 1
UNREAD_TRACKING_STARTED_AT_KEY = "unreadTrackingStartedAt"


class ImageStatusService:
    """Track image lifecycle with viewedAt for unread/read status."""

    def __init__(self, state: BridgeState):
        self._state = state

    def _get_status_file(self, brand_slug: str) -> Path:
        """Get path to image_status.json for a brand."""
        return get_brand_dir(brand_slug) / STATUS_FILE_NAME

    def _load_status_data(self, brand_slug: str) -> dict:
        """Load status data from file, creating empty structure if missing."""
        data = load_image_status_raw(brand_slug)
        # Migrate legacy data: ensure unread tracking baseline exists + mark legacy images as viewed
        baseline, changed = self._ensure_unread_tracking_started_at(data)
        changed = self._migrate_legacy_viewed_at(data, baseline) or changed
        changed = self._migrate_legacy_status_fields(data) or changed
        if changed:
            self._save_status_data(brand_slug, data)
        return data

    def _save_status_data(self, brand_slug: str, data: dict) -> None:
        """Atomically save status data to file."""
        save_image_status(brand_slug, data)

    def _generate_id(self) -> str:
        """Generate unique image ID."""
        return f"img_{uuid.uuid4().hex[:12]}"

    def _now_iso(self) -> str:
        """Get current time as ISO 8601 string."""
        return datetime.now(timezone.utc).isoformat()

    def _parse_iso(self, value: str | None) -> datetime | None:
        """Parse ISO 8601 time string to timezone-aware datetime (UTC fallback)."""
        if not value or not isinstance(value, str):
            return None
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def _ensure_unread_tracking_started_at(self, data: dict) -> tuple[str, bool]:
        """Ensure baseline timestamp exists for backward compatibility decisions."""
        existing = data.get(UNREAD_TRACKING_STARTED_AT_KEY)
        if isinstance(existing, str) and existing:
            return existing, False
        now = self._now_iso()
        data[UNREAD_TRACKING_STARTED_AT_KEY] = now
        return now, True

    def _migrate_legacy_viewed_at(self, data: dict, baseline_iso: str) -> bool:
        """Mark pre-unread-tracking images as viewed so they don't show as unread."""
        images = data.get("images", {})
        if not isinstance(images, dict):
            return False
        changed = False
        for entry in images.values():
            if not isinstance(entry, dict):
                continue
            if "viewedAt" not in entry:
                # Legacy entry from older versions: assume already read
                ts = entry.get("timestamp")
                entry["viewedAt"] = ts if isinstance(ts, str) and ts else baseline_iso
                changed = True
            elif entry.get("viewedAt") == "":
                entry["viewedAt"] = baseline_iso
                changed = True
        return changed

    def _migrate_legacy_status_fields(self, data: dict) -> bool:
        """Ensure legacy entries have kept/trash timestamp fields."""
        images = data.get("images", {})
        if not isinstance(images, dict):
            return False
        changed = False
        for entry in images.values():
            if not isinstance(entry, dict):
                continue
            if "keptAt" not in entry:
                entry["keptAt"] = None
                changed = True
            if "trashedAt" not in entry:
                entry["trashedAt"] = None
                changed = True
        return changed

    def _normalize_path(self, path: str | None) -> str:
        """Normalize path for consistent comparison by extracting filename."""
        if not path:
            return ""
        # Extract just the filename for comparison since paths may be stored
        # as relative or absolute inconsistently
        return Path(path).name

    def get_status(self, brand_slug: str, image_id: str) -> dict:
        """Get status entry for a specific image."""
        try:
            data = self._load_status_data(brand_slug)
            images = data.get("images", {})
            if image_id not in images:
                return bridge_error(f"Image not found: {image_id}")
            return bridge_ok(images[image_id])
        except Exception as e:
            return bridge_error(str(e))

    def set_status(self, brand_slug: str, image_id: str, status: ImageStatus) -> dict:
        """Update status of an image."""
        try:
            data = self._load_status_data(brand_slug)
            images = data.get("images", {})
            if image_id not in images:
                return bridge_error(f"Image not found: {image_id}")
            entry = images[image_id]
            entry["status"] = status
            now = self._now_iso()
            if status == "kept":
                entry["keptAt"] = now
                entry["trashedAt"] = None
            elif status == "trashed":
                entry["trashedAt"] = now
                entry["keptAt"] = None
            else:
                entry["keptAt"] = None
                entry["trashedAt"] = None
            images[image_id] = entry
            data["images"] = images
            self._save_status_data(brand_slug, data)
            return bridge_ok(entry)
        except Exception as e:
            return bridge_error(str(e))

    def list_by_status(self, brand_slug: str, status: ImageStatus) -> dict:
        """List all images with a specific status, filtering out missing files."""
        try:
            data = self._load_status_data(brand_slug)
            images = data.get("images", {})
            # Filter by status and verify file exists on disk
            filtered = []
            stale_ids = []
            for img_id, v in images.items():
                if v.get("status") != status:
                    continue
                path = v.get("originalPath") or v.get("currentPath")
                if path and Path(path).exists():
                    filtered.append(v)
                else:
                    stale_ids.append(img_id)
            # Clean up stale entries from index
            if stale_ids:
                for img_id in stale_ids:
                    del images[img_id]
                data["images"] = images
                self._save_status_data(brand_slug, data)
                logger.info(f"Cleaned up {len(stale_ids)} stale image entries")
            return bridge_ok(filtered)
        except Exception as e:
            return bridge_error(str(e))

    def register_image(
        self,
        brand_slug: str,
        image_path: str,
        prompt: str | None = None,
        source_template_path: str | None = None,
    ) -> dict:
        """Register a new image with unsorted status."""
        try:
            data = self._load_status_data(brand_slug)
            image_id = self._generate_id()
            now = self._now_iso()
            self._ensure_unread_tracking_started_at(data)
            source_path = source_template_path
            if source_template_path and not source_template_path.startswith(
                ("data:", "http://", "https://")
            ):
                p = Path(source_template_path)
                if not p.is_absolute():
                    brand_dir = get_brand_dir(brand_slug)
                    resolved = (brand_dir / source_template_path).resolve()
                    try:
                        resolved.relative_to(brand_dir.resolve())
                        source_path = str(resolved)
                    except ValueError:
                        source_path = source_template_path
                else:
                    source_path = str(p)
            entry = {
                "id": image_id,
                "status": "unsorted",
                "originalPath": image_path,
                "currentPath": image_path,
                "prompt": prompt,
                "sourceTemplatePath": source_path,
                "timestamp": now,
                "viewedAt": None,
                "keptAt": None,
                "trashedAt": None,
            }
            data["images"][image_id] = entry
            self._save_status_data(brand_slug, data)
            return bridge_ok(entry)
        except Exception as e:
            return bridge_error(str(e))

    def mark_viewed(self, brand_slug: str, image_id: str) -> dict:
        """Mark image as viewed (read)."""
        try:
            data = self._load_status_data(brand_slug)
            images = data.get("images", {})
            if image_id not in images:
                return bridge_error(f"Image not found: {image_id}")
            entry = images[image_id]
            if not entry.get("viewedAt"):
                entry["viewedAt"] = self._now_iso()
                images[image_id] = entry
                data["images"] = images
                self._save_status_data(brand_slug, data)
            return bridge_ok(entry)
        except Exception as e:
            return bridge_error(str(e))

    def update_path(self, brand_slug: str, image_id: str, new_path: str) -> dict:
        """Update the current path of an image."""
        try:
            data = self._load_status_data(brand_slug)
            images = data.get("images", {})
            if image_id not in images:
                return bridge_error(f"Image not found: {image_id}")
            images[image_id]["currentPath"] = new_path
            data["images"] = images
            self._save_status_data(brand_slug, data)
            return bridge_ok(images[image_id])
        except Exception as e:
            return bridge_error(str(e))

    def delete_image(self, brand_slug: str, image_id: str) -> dict:
        """Remove an image entry from the status file."""
        try:
            data = self._load_status_data(brand_slug)
            images = data.get("images", {})
            if image_id not in images:
                return bridge_error(f"Image not found: {image_id}")
            del images[image_id]
            data["images"] = images
            self._save_status_data(brand_slug, data)
            return bridge_ok()
        except Exception as e:
            return bridge_error(str(e))

    def find_by_path(self, brand_slug: str, path: str) -> dict:
        """Find image entry by current path. Returns entry with ID or error if not found."""
        try:
            data = self._load_status_data(brand_slug)
            images = data.get("images", {})
            for img_id, entry in images.items():
                if entry.get("currentPath") == path or entry.get("originalPath") == path:
                    return bridge_ok({**entry, "id": img_id})
            return bridge_error(f"Image not found for path: {path}")
        except Exception as e:
            return bridge_error(str(e))

    def register_or_find(
        self, brand_slug: str, path: str, status: ImageStatus = "unsorted"
    ) -> dict:
        """Find existing entry by path or register new one."""
        try:
            found = self.find_by_path(brand_slug, path)
            if found.get("success"):
                return found
            # Register new entry
            data = self._load_status_data(brand_slug)
            image_id = self._generate_id()
            now = self._now_iso()
            kept_at = now if status == "kept" else None
            trashed_at = now if status == "trashed" else None
            entry = {
                "id": image_id,
                "status": status,
                "originalPath": path,
                "currentPath": path,
                "prompt": None,
                "sourceTemplatePath": None,
                "timestamp": now,
                "viewedAt": None,
                "keptAt": kept_at,
                "trashedAt": trashed_at,
            }
            data["images"][image_id] = entry
            self._save_status_data(brand_slug, data)
            return bridge_ok(entry)
        except Exception as e:
            return bridge_error(str(e))

    def backfill_from_folders(self, brand_slug: str) -> dict:
        """Scan asset folders and backfill missing entries."""
        try:
            from sip_studio.studio.utils.bridge_types import ALLOWED_IMAGE_EXTS

            brand_dir = get_brand_dir(brand_slug)
            data = self._load_status_data(brand_slug)
            baseline_iso, _ = self._ensure_unread_tracking_started_at(data)
            baseline_dt = self._parse_iso(baseline_iso) or datetime.now(timezone.utc)
            # Use normalized paths for consistent comparison
            existing_paths = {
                self._normalize_path(e.get("currentPath")) for e in data.get("images", {}).values()
            }
            added = []
            folders_status = [("generated", "unsorted"), ("kept", "kept"), ("trash", "trashed")]
            for folder, status in folders_status:
                folder_path = brand_dir / "assets" / folder
                if not folder_path.exists():
                    continue
                for fp in folder_path.iterdir():
                    if not fp.is_file() or fp.suffix.lower() not in ALLOWED_IMAGE_EXTS:
                        continue
                    path_str = str(fp)
                    if self._normalize_path(path_str) in existing_paths:
                        continue
                    image_id = self._generate_id()
                    mtime_dt = datetime.fromtimestamp(fp.stat().st_mtime, timezone.utc)
                    ts = mtime_dt.isoformat()
                    # Backward compat: anything that existed before baseline is assumed read
                    viewed_at = baseline_iso if mtime_dt <= baseline_dt else None
                    kept_at = ts if status == "kept" else None
                    trashed_at = ts if status == "trashed" else None
                    entry = {
                        "id": image_id,
                        "status": status,
                        "originalPath": path_str,
                        "currentPath": path_str,
                        "prompt": None,
                        "sourceTemplatePath": None,
                        "timestamp": ts,
                        "viewedAt": viewed_at,
                        "keptAt": kept_at,
                        "trashedAt": trashed_at,
                    }
                    data["images"][image_id] = entry
                    added.append(entry)
            if added:
                self._save_status_data(brand_slug, data)
            return bridge_ok({"added": added, "count": len(added)})
        except Exception as e:
            return bridge_error(str(e))

    def cleanup_old_trash(self, brand_slug: str, days: int = 30) -> dict:
        """Delete trash items older than specified days."""
        try:
            from datetime import timedelta

            data = self._load_status_data(brand_slug)
            images = data.get("images", {})
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            deleted = []
            to_remove = []
            for image_id, entry in images.items():
                if not isinstance(entry, dict) or entry.get("status") != "trashed":
                    continue
                trashed_dt = self._parse_iso(entry.get("trashedAt"))
                if not trashed_dt or trashed_dt >= cutoff:
                    continue
                path = Path(entry.get("currentPath", ""))
                if path.exists():
                    try:
                        path.unlink()
                    except OSError as e:
                        logger.debug("Failed to delete trashed image %s: %s", path, e)
                to_remove.append(image_id)
                deleted.append(entry)
            for image_id in to_remove:
                del images[image_id]
            if to_remove:
                data["images"] = images
                self._save_status_data(brand_slug, data)
            return bridge_ok({"deleted": deleted, "count": len(deleted)})
        except Exception as e:
            return bridge_error(str(e))
