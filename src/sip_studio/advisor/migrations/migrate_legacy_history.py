"""Migration for legacy chat_history.json to new session format.
Migrates existing chat_history.json files to the new sessions directory structure.
Migration is idempotent - won't re-migrate already migrated brands.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sip_studio.advisor.session_manager import (
    Message,
    MessagesFile,
    SessionManager,
    SessionSettings,
    brand_lock,
    utc_now_iso,
)
from sip_studio.brands.storage.base import get_brand_dir
from sip_studio.config.logging import get_logger

logger = get_logger(__name__)
__all__ = ["MigrationResult", "migrate_legacy_history", "migrate_all_brands"]
LEGACY_FILENAME = "chat_history.json"
MIGRATED_MARKER = ".chat_history_migrated"


class MigrationResult(Enum):
    """Result of a migration operation."""

    SUCCESS = "success"
    ALREADY_DONE = "already_done"
    NO_LEGACY_DATA = "no_legacy_data"
    CORRUPTED_UNRECOVERABLE = "corrupted"
    ERROR = "error"


def _normalize_timestamp(ts: str | None) -> str:
    """Convert timestamp to UTC with Z suffix."""
    if not ts:
        return utc_now_iso()
    # Already has Z suffix
    if ts.endswith("Z"):
        return ts
    try:
        # Parse as ISO format (may have +00:00 or no tz)
        if "+" in ts or ts.endswith("Z"):
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            # Naive datetime - assume local time, convert to UTC
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        logger.warning(f"Invalid timestamp format: {ts}, using current time")
        return utc_now_iso()


def _convert_legacy_message(legacy: dict[str, Any]) -> Message:
    """Convert a legacy message dict to new Message format."""
    ts = _normalize_timestamp(legacy.get("timestamp"))
    return Message(
        id=legacy.get("id", str(uuid.uuid4())),
        role=legacy["role"],
        content=legacy.get("content", ""),
        timestamp=ts,
        tool_calls=None,
        tool_call_id=None,
        attachments=None,
        metadata=None,
    )


def _generate_preview(messages: list[Message]) -> str:
    """Generate a preview from the first user message."""
    for m in messages:
        if m.role == "user" and m.content:
            preview = m.content[:100]
            if len(m.content) > 100:
                preview += "..."
            return preview
    return ""


def _generate_title_from_messages(messages: list[Message]) -> str:
    """Generate a title from the first user message."""
    for m in messages:
        if m.role == "user" and m.content:
            # Take first sentence or first 50 chars
            first_line = m.content.split("\n")[0]
            first_sent = first_line.split(".")[0]
            title = first_sent[:50]
            if len(first_sent) > 50:
                title += "..."
            return title if title else "Migrated conversation"
    return "Migrated conversation"


def migrate_legacy_history(brand_slug: str) -> MigrationResult:
    """Migrate legacy chat_history.json to new session format.
    Args:
            brand_slug: The brand slug to migrate.
    Returns:
            MigrationResult indicating the outcome.
    """
    brand_dir = get_brand_dir(brand_slug)
    legacy_path = brand_dir / LEGACY_FILENAME
    migrated_marker = brand_dir / MIGRATED_MARKER
    # Check if already migrated
    if migrated_marker.exists():
        logger.debug(f"Brand {brand_slug} already migrated")
        return MigrationResult.ALREADY_DONE
    # Check if legacy file exists
    if not legacy_path.exists():
        logger.debug(f"No legacy history for brand {brand_slug}")
        # Create marker to avoid re-checking
        migrated_marker.touch()
        return MigrationResult.NO_LEGACY_DATA
    # Create backup before migration
    backup_path = legacy_path.parent / (legacy_path.name + ".backup")
    if not backup_path.exists():
        try:
            shutil.copy2(legacy_path, backup_path)
        except Exception as e:
            logger.warning(f"Failed to create backup for {brand_slug}: {e}")
    try:
        # Read legacy data
        with open(legacy_path, encoding="utf-8") as f:
            legacy = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Corrupted legacy history for {brand_slug}: {e}")
        migrated_marker.touch()
        return MigrationResult.CORRUPTED_UNRECOVERABLE
    except Exception as e:
        logger.error(f"Failed to read legacy history for {brand_slug}: {e}")
        return MigrationResult.ERROR
    try:
        # Get legacy messages
        legacy_messages = legacy.get("messages", [])
        legacy_summary = legacy.get("summary")
        if not legacy_messages:
            logger.debug(f"No messages to migrate for {brand_slug}")
            migrated_marker.touch()
            return MigrationResult.NO_LEGACY_DATA
        # Convert messages
        new_messages = [_convert_legacy_message(m) for m in legacy_messages]
        # Create session via SessionManager (methods have internal locking)
        manager = SessionManager(brand_slug)
        # Generate session metadata
        title = _generate_title_from_messages(new_messages)
        preview = _generate_preview(new_messages)
        # Determine timestamps
        first_ts = new_messages[0].timestamp if new_messages else utc_now_iso()
        last_ts = new_messages[-1].timestamp if new_messages else utc_now_iso()
        # Create session with settings
        session = manager.create_session(settings=SessionSettings(), title=title)
        # Load messages file and update it
        mf = manager.load_messages_file(session.id)
        if mf is None:
            mf = MessagesFile(session_id=session.id, settings=SessionSettings())
        mf.full_history = new_messages
        mf.summary = legacy_summary
        manager.save_messages_file(session.id, mf)
        # Update session meta with correct timestamps
        manager.update_session_meta(
            session.id, title=title, preview=preview, message_count=len(new_messages)
        )
        # Fix original timestamps (use brand_lock for atomic index update)
        with brand_lock(brand_slug):
            index = manager._load_index()
            for s in index.sessions:
                if s.id == session.id:
                    s.created_at = first_ts
                    s.last_active_at = last_ts
                    s.updated_at = last_ts
                    break
            manager._save_index(index)
        # Create marker file
        migrated_marker.touch()
        logger.info(f"Successfully migrated {len(new_messages)} messages for brand {brand_slug}")
        return MigrationResult.SUCCESS
    except Exception as e:
        logger.error(f"Migration failed for {brand_slug}: {e}")
        return MigrationResult.ERROR


def migrate_all_brands() -> dict[str, MigrationResult]:
    """Migrate all brands with legacy history.
    Returns:
            Dictionary mapping brand_slug to MigrationResult.
    """
    from sip_studio.brands.storage.brand_storage import list_brands

    results: dict[str, MigrationResult] = {}
    try:
        brands = list_brands()
        for brand in brands:
            slug = brand.slug
            try:
                result = migrate_legacy_history(slug)
                results[slug] = result
                if result == MigrationResult.SUCCESS:
                    logger.info(f"Migrated brand: {slug}")
                elif result == MigrationResult.ALREADY_DONE:
                    logger.debug(f"Already migrated: {slug}")
                elif result == MigrationResult.NO_LEGACY_DATA:
                    logger.debug(f"No legacy data: {slug}")
                else:
                    logger.warning(f"Migration issue for {slug}: {result}")
            except Exception as e:
                logger.error(f"Failed to migrate brand {slug}: {e}")
                results[slug] = MigrationResult.ERROR
    except Exception as e:
        logger.error(f"Failed to list brands for migration: {e}")
    return results
