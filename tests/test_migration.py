"""Tests for legacy chat_history.json migration to new session format."""

import json
import sys
from pathlib import Path

import pytest

import sip_studio.advisor.session_manager as session_manager_mod
import sip_studio.brands.storage.base as storage_base_mod
from sip_studio.advisor.migrations.migrate_legacy_history import (
    MigrationResult,
    _convert_legacy_message,
    _generate_preview,
    _generate_title_from_messages,
    _normalize_timestamp,
)
from sip_studio.advisor.session_manager import Message, SessionManager


@pytest.fixture
def tmp_brand_dir(tmp_path, monkeypatch):
    """Create temporary brand directory and mock get_brand_dir."""
    brand_slug = "test-brand"
    brand_dir = tmp_path / ".sip-studio" / "brands" / brand_slug
    brand_dir.mkdir(parents=True)

    def mock_get_brand_dir(slug: str) -> Path:
        return tmp_path / ".sip-studio" / "brands" / slug

    # Patch at module level to override cached imports
    monkeypatch.setattr(session_manager_mod, "get_brand_dir", mock_get_brand_dir)
    monkeypatch.setattr(storage_base_mod, "get_brand_dir", mock_get_brand_dir)
    # Patch migrate module directly via sys.modules (avoids name collision with function)
    migrate_module = sys.modules["sip_studio.advisor.migrations.migrate_legacy_history"]
    monkeypatch.setattr(migrate_module, "get_brand_dir", mock_get_brand_dir)
    return brand_slug, brand_dir


def _migrate_legacy_history(slug: str) -> MigrationResult:
    """Import and call migrate_legacy_history to use fresh module state."""
    from sip_studio.advisor.migrations.migrate_legacy_history import migrate_legacy_history

    return migrate_legacy_history(slug)


class TestNormalizeTimestamp:
    def test_already_utc(self):
        ts = "2026-01-09T20:09:38Z"
        assert _normalize_timestamp(ts) == ts

    def test_with_microseconds(self):
        ts = "2026-01-09T20:09:38.142409"
        result = _normalize_timestamp(ts)
        assert result.endswith("Z")
        assert "2026-01-09T20" in result

    def test_none_returns_current(self):
        result = _normalize_timestamp(None)
        assert result.endswith("Z")
        assert len(result) == 20

    def test_invalid_format_returns_current(self):
        result = _normalize_timestamp("not-a-timestamp")
        assert result.endswith("Z")


class TestConvertLegacyMessage:
    def test_basic_message(self):
        legacy = {"role": "user", "content": "Hello", "timestamp": "2026-01-09T20:09:38.142409"}
        msg = _convert_legacy_message(legacy)
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp.endswith("Z")
        assert msg.id is not None

    def test_missing_content(self):
        legacy = {"role": "assistant", "timestamp": "2026-01-09T20:09:38Z"}
        msg = _convert_legacy_message(legacy)
        assert msg.content == ""

    def test_with_existing_id(self):
        legacy = {
            "role": "user",
            "content": "Test",
            "timestamp": "2026-01-09T20:09:38Z",
            "id": "custom-id",
        }
        msg = _convert_legacy_message(legacy)
        assert msg.id == "custom-id"


class TestGeneratePreview:
    def test_first_user_message(self):
        msgs = [Message.create("assistant", "Ignored"), Message.create("user", "Hello world!")]
        preview = _generate_preview(msgs)
        assert preview == "Hello world!"

    def test_truncates_long_message(self):
        msgs = [Message.create("user", "A" * 150)]
        preview = _generate_preview(msgs)
        assert len(preview) == 103  # 100 chars + "..."
        assert preview.endswith("...")

    def test_empty_messages(self):
        assert _generate_preview([]) == ""


class TestGenerateTitle:
    def test_first_sentence(self):
        msgs = [Message.create("user", "Create a logo. For my brand.")]
        title = _generate_title_from_messages(msgs)
        assert title == "Create a logo"

    def test_truncates_long(self):
        msgs = [Message.create("user", "A" * 100)]
        title = _generate_title_from_messages(msgs)
        assert len(title) == 53  # 50 + "..."

    def test_empty_messages(self):
        assert _generate_title_from_messages([]) == "Migrated conversation"


class TestMigrateLegacyHistory:
    def test_no_legacy_data(self, tmp_brand_dir):
        slug, brand_dir = tmp_brand_dir
        result = _migrate_legacy_history(slug)
        assert result == MigrationResult.NO_LEGACY_DATA
        # Marker should be created
        assert (brand_dir / ".chat_history_migrated").exists()

    def test_already_migrated(self, tmp_brand_dir):
        slug, brand_dir = tmp_brand_dir
        # Create marker
        (brand_dir / ".chat_history_migrated").touch()
        result = _migrate_legacy_history(slug)
        assert result == MigrationResult.ALREADY_DONE

    def test_successful_migration(self, tmp_brand_dir):
        slug, brand_dir = tmp_brand_dir
        # Create legacy history
        legacy_data = {
            "version": 1,
            "summary": "Previous summary",
            "messages": [
                {"role": "user", "content": "Create a logo", "timestamp": "2026-01-09T10:00:00"},
                {
                    "role": "assistant",
                    "content": "I'll help you",
                    "timestamp": "2026-01-09T10:01:00",
                },
                {"role": "user", "content": "Make it blue", "timestamp": "2026-01-09T10:02:00"},
                {"role": "assistant", "content": "Done!", "timestamp": "2026-01-09T10:03:00"},
            ],
        }
        legacy_path = brand_dir / "chat_history.json"
        legacy_path.write_text(json.dumps(legacy_data), encoding="utf-8")
        result = _migrate_legacy_history(slug)
        assert result == MigrationResult.SUCCESS
        # Verify marker created
        assert (brand_dir / ".chat_history_migrated").exists()
        # Verify backup created
        assert (brand_dir / "chat_history.json.backup").exists()
        # Verify session created
        manager = SessionManager(slug)
        sessions = manager.list_sessions()
        assert len(sessions) == 1
        session = sessions[0]
        assert session.message_count == 4
        assert "Create a logo" in session.title
        # Verify messages migrated
        mf = manager.load_messages_file(session.id)
        assert mf is not None
        assert len(mf.full_history) == 4
        assert mf.summary == "Previous summary"

    def test_corrupted_json(self, tmp_brand_dir):
        slug, brand_dir = tmp_brand_dir
        # Create corrupted file
        legacy_path = brand_dir / "chat_history.json"
        legacy_path.write_text("not valid json{", encoding="utf-8")
        result = _migrate_legacy_history(slug)
        assert result == MigrationResult.CORRUPTED_UNRECOVERABLE
        # Marker should be created to avoid re-trying
        assert (brand_dir / ".chat_history_migrated").exists()

    def test_empty_messages(self, tmp_brand_dir):
        slug, brand_dir = tmp_brand_dir
        # Create empty messages
        legacy_data = {"version": 1, "summary": None, "messages": []}
        legacy_path = brand_dir / "chat_history.json"
        legacy_path.write_text(json.dumps(legacy_data), encoding="utf-8")
        result = _migrate_legacy_history(slug)
        assert result == MigrationResult.NO_LEGACY_DATA

    def test_idempotent_migration(self, tmp_brand_dir):
        slug, brand_dir = tmp_brand_dir
        # Create legacy history
        legacy_data = {
            "version": 1,
            "summary": None,
            "messages": [{"role": "user", "content": "Test", "timestamp": "2026-01-09T10:00:00"}],
        }
        legacy_path = brand_dir / "chat_history.json"
        legacy_path.write_text(json.dumps(legacy_data), encoding="utf-8")
        # First migration
        result1 = _migrate_legacy_history(slug)
        assert result1 == MigrationResult.SUCCESS
        # Second migration should be idempotent
        result2 = _migrate_legacy_history(slug)
        assert result2 == MigrationResult.ALREADY_DONE
        # Should still only have one session
        manager = SessionManager(slug)
        sessions = manager.list_sessions()
        assert len(sessions) == 1

    def test_preserves_timestamps(self, tmp_brand_dir):
        slug, brand_dir = tmp_brand_dir
        # Create legacy history with specific timestamps
        legacy_data = {
            "version": 1,
            "summary": None,
            "messages": [
                {"role": "user", "content": "First", "timestamp": "2026-01-01T10:00:00"},
                {"role": "assistant", "content": "Last", "timestamp": "2026-01-09T20:00:00"},
            ],
        }
        legacy_path = brand_dir / "chat_history.json"
        legacy_path.write_text(json.dumps(legacy_data), encoding="utf-8")
        result = _migrate_legacy_history(slug)
        assert result == MigrationResult.SUCCESS
        # Verify session timestamps
        manager = SessionManager(slug)
        sessions = manager.list_sessions()
        assert len(sessions) == 1
        session = sessions[0]
        # Session should use first message timestamp as created_at
        assert "2026-01-01" in session.created_at
        # Session should use last message timestamp as last_active_at
        assert "2026-01-09" in session.last_active_at
