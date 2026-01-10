"""Tests for session manager - CRUD operations, session switching, settings persistence."""

import json
from pathlib import Path
from threading import Thread

import pytest

from sip_studio.advisor.session_manager import (
    Attachment,
    Message,
    MessagesFile,
    SessionIndex,
    SessionManager,
    SessionMeta,
    SessionSettings,
    ToolCall,
    atomic_write,
    safe_read,
    utc_now_iso,
)


@pytest.fixture
def tmp_brand_dir(tmp_path, monkeypatch):
    """Create temporary brand directory and mock get_brand_dir."""
    brand_slug = "test-brand"
    brand_dir = tmp_path / ".sip-studio" / "brands" / brand_slug
    brand_dir.mkdir(parents=True)

    def mock_get_brand_dir(slug: str) -> Path:
        return tmp_path / ".sip-studio" / "brands" / slug

    monkeypatch.setattr("sip_studio.advisor.session_manager.get_brand_dir", mock_get_brand_dir)
    return brand_slug, tmp_path


class TestUtcNowIso:
    def test_returns_z_suffix(self):
        ts = utc_now_iso()
        assert ts.endswith("Z")

    def test_iso_format(self):
        ts = utc_now_iso()
        from datetime import datetime

        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert dt is not None


class TestAtomicWrite:
    def test_creates_file(self, tmp_path):
        path = tmp_path / "test.json"
        data = {"key": "value"}
        atomic_write(path, data)
        assert path.exists()
        assert json.loads(path.read_text()) == data

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "test.json"
        data = {"nested": True}
        atomic_write(path, data)
        assert path.exists()

    def test_creates_backup(self, tmp_path):
        path = tmp_path / "test.json"
        atomic_write(path, {"v": 1})
        atomic_write(path, {"v": 2})
        backup = tmp_path / "test.json.backup"
        assert backup.exists()
        assert json.loads(backup.read_text()) == {"v": 1}


class TestSafeRead:
    def test_returns_none_for_missing(self, tmp_path):
        assert safe_read(tmp_path / "missing.json") is None

    def test_reads_valid_json(self, tmp_path):
        path = tmp_path / "valid.json"
        path.write_text('{"key": "value"}')
        assert safe_read(path) == {"key": "value"}

    def test_returns_none_for_invalid_json(self, tmp_path):
        path = tmp_path / "invalid.json"
        path.write_text("not json")
        assert safe_read(path) is None

    def test_recovers_from_backup(self, tmp_path):
        path = tmp_path / "corrupt.json"
        backup = tmp_path / "corrupt.json.backup"
        path.write_text("corrupt")
        backup.write_text('{"recovered": true}')
        result = safe_read(path)
        assert result == {"recovered": True}
        assert json.loads(path.read_text()) == {"recovered": True}


class TestMessage:
    def test_create(self):
        msg = Message.create("user", "Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.id
        assert msg.timestamp.endswith("Z")

    def test_to_dict_from_dict_roundtrip(self):
        msg = Message.create(
            "assistant", "Response", tool_calls=[ToolCall("tc1", "tool", '{"a":1}')]
        )
        d = msg.to_dict()
        restored = Message.from_dict(d)
        assert restored.role == msg.role
        assert restored.content == msg.content
        assert restored.tool_calls is not None
        assert restored.tool_calls[0].name == "tool"

    def test_with_attachments(self):
        msg = Message.create(
            "user", "With image", attachments=[Attachment("image", "http://x.com/img.png", "photo")]
        )
        d = msg.to_dict()
        assert d["attachments"][0]["type"] == "image"


class TestSessionSettings:
    def test_defaults(self):
        s = SessionSettings()
        assert s.image_aspect_ratio == "1:1"
        assert s.video_aspect_ratio == "16:9"
        assert s.attached_product_slugs == []

    def test_to_dict_from_dict_roundtrip(self):
        s = SessionSettings(
            project_slug="proj", image_aspect_ratio="16:9", attached_product_slugs=["p1", "p2"]
        )
        d = s.to_dict()
        restored = SessionSettings.from_dict(d)
        assert restored.project_slug == "proj"
        assert restored.attached_product_slugs == ["p1", "p2"]


class TestSessionMeta:
    def test_to_dict_from_dict_roundtrip(self):
        now = utc_now_iso()
        m = SessionMeta(
            id="sid",
            brand_slug="brand",
            title="Test",
            created_at=now,
            last_active_at=now,
            updated_at=now,
            message_count=5,
            preview="Hello...",
        )
        d = m.to_dict()
        restored = SessionMeta.from_dict(d)
        assert restored.id == "sid"
        assert restored.message_count == 5


class TestSessionIndex:
    def test_empty_index(self):
        idx = SessionIndex()
        assert idx.sessions == []
        assert idx.active_session_id is None

    def test_to_dict_from_dict_roundtrip(self):
        now = utc_now_iso()
        m = SessionMeta(
            id="s1",
            brand_slug="b",
            title="T",
            created_at=now,
            last_active_at=now,
            updated_at=now,
            message_count=0,
            preview="",
        )
        idx = SessionIndex(sessions=[m], active_session_id="s1")
        d = idx.to_dict()
        restored = SessionIndex.from_dict(d)
        assert len(restored.sessions) == 1
        assert restored.active_session_id == "s1"


class TestMessagesFile:
    def test_defaults(self):
        mf = MessagesFile(session_id="s1")
        assert mf.full_history == []
        assert mf.prompt_window_start == 0

    def test_to_dict_from_dict_roundtrip(self):
        mf = MessagesFile(
            session_id="s1",
            summary="Previous context",
            summary_token_count=100,
            full_history=[Message.create("user", "Hi")],
        )
        d = mf.to_dict()
        restored = MessagesFile.from_dict(d)
        assert restored.summary == "Previous context"
        assert len(restored.full_history) == 1


class TestSessionManager:
    def test_create_session(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        session = mgr.create_session()
        assert session.id
        assert session.brand_slug == brand_slug
        assert session.title == "New conversation"
        active = mgr.get_active_session()
        assert active is not None
        assert active.id == session.id

    def test_create_session_with_settings(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        settings = SessionSettings(project_slug="my-proj", image_aspect_ratio="16:9")
        session = mgr.create_session(settings=settings, title="Custom Title")
        assert session.title == "Custom Title"
        loaded_settings = mgr.get_session_settings(session.id)
        assert loaded_settings is not None
        assert loaded_settings.project_slug == "my-proj"

    def test_list_sessions_empty(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        assert mgr.list_sessions() == []

    def test_list_sessions_sorted_by_last_active(self, tmp_brand_dir, monkeypatch):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        # Create sessions with explicit timestamps via monkeypatching
        from sip_studio.advisor import session_manager

        monkeypatch.setattr(session_manager, "utc_now_iso", lambda: "2024-01-01T00:00:01Z")
        s1 = mgr.create_session(title="First")
        monkeypatch.setattr(session_manager, "utc_now_iso", lambda: "2024-01-01T00:00:02Z")
        s2 = mgr.create_session(title="Second")
        monkeypatch.setattr(session_manager, "utc_now_iso", lambda: "2024-01-01T00:00:03Z")
        s3 = mgr.create_session(title="Third")
        sessions = mgr.list_sessions()
        # Most recent first (s3 -> s2 -> s1)
        assert sessions[0].id == s3.id
        assert sessions[1].id == s2.id
        assert sessions[2].id == s1.id

    def test_get_session(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        created = mgr.create_session()
        fetched = mgr.get_session(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_session_not_found(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        assert mgr.get_session("nonexistent") is None

    def test_set_active_session(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        active = mgr.get_active_session()
        assert active is not None
        assert active.id == s2.id
        assert mgr.set_active_session(s1.id)
        active2 = mgr.get_active_session()
        assert active2 is not None
        assert active2.id == s1.id

    def test_set_active_session_invalid(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        mgr.create_session()
        assert not mgr.set_active_session("invalid-id")

    def test_update_session_meta(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        session = mgr.create_session()
        mgr.update_session_meta(
            session.id, title="Updated Title", preview="Hello world...", message_count=5
        )
        updated = mgr.get_session(session.id)
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.preview == "Hello world..."
        assert updated.message_count == 5

    def test_delete_session(self, tmp_brand_dir):
        brand_slug, tmp_path = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        session = mgr.create_session()
        session_dir = tmp_path / ".sip-studio" / "brands" / brand_slug / "sessions" / session.id
        assert session_dir.exists()
        assert mgr.delete_session(session.id)
        assert not session_dir.exists()
        assert mgr.get_session(session.id) is None

    def test_delete_session_clears_active(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        mgr.delete_session(s2.id)
        active = mgr.get_active_session()
        assert active is not None
        assert active.id == s1.id

    def test_delete_all_sessions(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        session = mgr.create_session()
        mgr.delete_session(session.id)
        assert mgr.get_active_session() is None
        assert mgr.list_sessions() == []

    def test_archived_sessions_excluded_by_default(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        mgr.create_session(title="Active")  # s1 - not used by name
        s2 = mgr.create_session(title="Archived")
        mgr.update_session_meta(s2.id, is_archived=True)
        sessions = mgr.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].title == "Active"
        all_sessions = mgr.list_sessions(include_archived=True)
        assert len(all_sessions) == 2

    def test_save_load_messages_file(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        session = mgr.create_session()
        mf = mgr.load_messages_file(session.id)
        assert mf is not None
        mf.full_history.append(Message.create("user", "Hello"))
        mf.full_history.append(Message.create("assistant", "Hi there!"))
        mgr.save_messages_file(session.id, mf)
        reloaded = mgr.load_messages_file(session.id)
        assert reloaded is not None
        assert len(reloaded.full_history) == 2
        assert reloaded.full_history[0].content == "Hello"

    def test_save_session_settings(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        session = mgr.create_session()
        new_settings = SessionSettings(project_slug="updated-proj", image_aspect_ratio="4:3")
        assert mgr.save_session_settings(session.id, new_settings)
        loaded = mgr.get_session_settings(session.id)
        assert loaded is not None
        assert loaded.project_slug == "updated-proj"
        assert loaded.image_aspect_ratio == "4:3"


class TestConcurrentAccess:
    """Test concurrent write handling."""

    def test_concurrent_session_creation(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        results: list[str] = []

        def create_session():
            session = mgr.create_session()
            results.append(session.id)

        threads = [Thread(target=create_session) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 5
        sessions = mgr.list_sessions()
        assert len(sessions) == 5
        assert len(set(results)) == 5

    def test_concurrent_message_writes(self, tmp_brand_dir):
        brand_slug, _ = tmp_brand_dir
        mgr = SessionManager(brand_slug)
        session = mgr.create_session()

        def add_message(msg_content: str):
            mf = mgr.load_messages_file(session.id)
            if mf is not None:
                mf.full_history.append(Message.create("user", msg_content))
                mgr.save_messages_file(session.id, mf)

        threads = [Thread(target=add_message, args=(f"msg-{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        mf = mgr.load_messages_file(session.id)
        assert mf is not None
        assert len(mf.full_history) > 0
