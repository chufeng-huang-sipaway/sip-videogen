#!/usr/bin/env python3
"""
Reset (and optionally rebuild) Brand Studio image read/unread state for a brand.

Default behavior:
- Backs up `~/.sip-videogen/brands/<slug>/image_status.json` (if present)
- Replaces it with a fresh, empty status file containing:
  - version: 1
  - unreadTrackingStartedAt: now (UTC)
  - images: {}

Then, unless --no-backfill is provided, it will scan:
  assets/generated/  -> status "unsorted"
  assets/kept/       -> status "kept"
  assets/trash/      -> status "trashed"

and repopulate `images` entries. Files that existed before the baseline are marked
as viewed (read) so only newly generated images will show as unread going forward.

This script is intentionally self-contained (no sip_videogen imports) so you can
run it even if your venv isn't active.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
STATUS_FILE_NAME = "image_status.json"
CURRENT_VERSION = 1


@dataclass(frozen=True)
class FolderSpec:
    name: str
    status: str


FOLDERS: list[FolderSpec] = [
    FolderSpec("generated", "unsorted"),
    FolderSpec("kept", "kept"),
    FolderSpec("trash", "trashed"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def generate_id() -> str:
    return f"img_{uuid.uuid4().hex[:12]}"


def brand_dir_for_slug(slug: str) -> Path:
    return Path.home() / ".sip-videogen" / "brands" / slug


def status_path_for_slug(slug: str) -> Path:
    return brand_dir_for_slug(slug) / STATUS_FILE_NAME


def safe_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.bak-{ts}")
    shutil.copy2(path, backup)
    return backup


def iter_image_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    items: list[Path] = []
    for p in folder.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in ALLOWED_IMAGE_EXTS:
            continue
        items.append(p)
    return sorted(items)


def build_entry(
    file_path: Path,
    status: str,
    baseline_dt: datetime,
    baseline_iso: str,
) -> dict:
    mtime_dt = datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc)
    ts = mtime_dt.isoformat()

    # Backward compat: images that pre-date the baseline are assumed already read.
    viewed_at = baseline_iso if mtime_dt <= baseline_dt else None

    kept_at = ts if status == "kept" else None
    trashed_at = ts if status == "trashed" else None

    return {
        "id": "",  # filled by caller with the dict key
        "status": status,
        "originalPath": str(file_path),
        "currentPath": str(file_path),
        "prompt": None,
        "sourceTemplatePath": None,
        "timestamp": ts,
        "viewedAt": viewed_at,
        "keptAt": kept_at,
        "trashedAt": trashed_at,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Reset Brand Studio image_status.json for a brand.")
    parser.add_argument("slug", help="Brand slug (e.g. activatedyou)")
    parser.add_argument(
        "--no-backfill",
        action="store_true",
        help="Do not repopulate entries from assets folders (leaves images: {}).",
    )
    args = parser.parse_args(argv)

    slug = args.slug
    brand_dir = brand_dir_for_slug(slug)
    if not brand_dir.exists():
        print(f"ERROR: Brand directory not found: {brand_dir}", file=sys.stderr)
        return 2

    status_path = status_path_for_slug(slug)
    backup = backup_file(status_path)
    if backup:
        print(f"Backed up: {status_path} -> {backup}")
    else:
        print(f"No existing status file found at: {status_path} (creating new)")

    baseline_iso = now_iso()
    baseline_dt = parse_iso(baseline_iso)

    data: dict = {
        "version": CURRENT_VERSION,
        "unreadTrackingStartedAt": baseline_iso,
        "images": {},
    }

    if not args.no_backfill:
        assets_dir = brand_dir / "assets"
        images: dict[str, dict] = {}

        for spec in FOLDERS:
            folder = assets_dir / spec.name
            for fp in iter_image_files(folder):
                image_id = generate_id()
                entry = build_entry(fp, spec.status, baseline_dt, baseline_iso)
                entry["id"] = image_id
                images[image_id] = entry

        data["images"] = images

    safe_write_json(status_path, data)
    print(f"Wrote fresh status file: {status_path}")
    print(f"Entries: {len(data.get('images', {}))}")
    print("Next: restart the app, select the brand, and generate a new image to see unread indicators.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

