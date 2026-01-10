"""Session management for chat conversations.
Provides CRUD operations for sessions with atomic writes and file locking.
Sessions stored in {brand_dir}/sessions/ with index.json for fast listing.
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from sip_studio.brands.storage.base import get_brand_dir
from sip_studio.config.logging import get_logger

logger = get_logger(__name__)
__all__ = [
    "SessionManager",
    "SessionMeta",
    "SessionIndex",
    "Message",
    "MessagesFile",
    "SessionSettings",
    "ToolCall",
    "Attachment",
    "utc_now_iso",
    "atomic_write",
    "safe_read",
    "brand_lock",
    "session_lock",
]
SCHEMA_VERSION = 1


def utc_now_iso() -> str:
    """Return current UTC time as ISO string with Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# region Data Models
@dataclass
class ToolCall:
    """Tool call in a message."""

    id: str
    name: str
    arguments: str  # JSON string

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ToolCall":
        return cls(id=d["id"], name=d["name"], arguments=d.get("arguments", "{}"))


@dataclass
class Attachment:
    """Attachment in a message."""

    type: Literal["image", "file"]
    url: str
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type, "url": self.url}
        if self.name:
            d["name"] = self.name
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Attachment":
        return cls(type=d["type"], url=d["url"], name=d.get("name"))


@dataclass
class Message:
    """A single conversation message."""

    id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: str  # ISO UTC with Z suffix
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    attachments: list[Attachment] | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        if self.tool_calls:
            d["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.attachments:
            d["attachments"] = [a.to_dict() for a in self.attachments]
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Message":
        tcs = None
        if d.get("tool_calls"):
            tcs = [ToolCall.from_dict(tc) for tc in d["tool_calls"]]
        atts = None
        if d.get("attachments"):
            atts = [Attachment.from_dict(a) for a in d["attachments"]]
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            role=d["role"],
            content=d.get("content", ""),
            timestamp=d.get("timestamp", utc_now_iso()),
            tool_calls=tcs,
            tool_call_id=d.get("tool_call_id"),
            attachments=atts,
            metadata=d.get("metadata"),
        )

    @classmethod
    def create(
        cls, role: Literal["user", "assistant", "system", "tool"], content: str, **kwargs: Any
    ) -> "Message":
        """Create a new message with auto-generated id and timestamp."""
        return cls(
            id=str(uuid.uuid4()), role=role, content=content, timestamp=utc_now_iso(), **kwargs
        )


@dataclass
class SessionSettings:
    """Settings for a chat session."""

    project_slug: str | None = None
    image_aspect_ratio: str = "1:1"
    video_aspect_ratio: str = "16:9"
    attached_product_slugs: list[str] = field(default_factory=list)
    attached_style_references: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_slug": self.project_slug,
            "image_aspect_ratio": self.image_aspect_ratio,
            "video_aspect_ratio": self.video_aspect_ratio,
            "attached_product_slugs": self.attached_product_slugs,
            "attached_style_references": self.attached_style_references,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SessionSettings":
        return cls(
            project_slug=d.get("project_slug"),
            image_aspect_ratio=d.get("image_aspect_ratio", "1:1"),
            video_aspect_ratio=d.get("video_aspect_ratio", "16:9"),
            attached_product_slugs=d.get("attached_product_slugs", []),
            attached_style_references=d.get("attached_style_references", []),
        )


@dataclass
class SessionMeta:
    """Metadata for a session stored in index."""

    id: str
    brand_slug: str
    title: str
    created_at: str  # ISO UTC with Z
    last_active_at: str  # ISO UTC with Z
    updated_at: str  # ISO UTC with Z - used as source_version
    message_count: int
    preview: str
    is_archived: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "brand_slug": self.brand_slug,
            "title": self.title,
            "created_at": self.created_at,
            "last_active_at": self.last_active_at,
            "updated_at": self.updated_at,
            "message_count": self.message_count,
            "preview": self.preview,
            "is_archived": self.is_archived,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SessionMeta":
        return cls(
            id=d["id"],
            brand_slug=d["brand_slug"],
            title=d.get("title", "New conversation"),
            created_at=d.get("created_at", utc_now_iso()),
            last_active_at=d.get("last_active_at", utc_now_iso()),
            updated_at=d.get("updated_at", utc_now_iso()),
            message_count=d.get("message_count", 0),
            preview=d.get("preview", ""),
            is_archived=d.get("is_archived", False),
        )


@dataclass
class SessionIndex:
    """Index of all sessions for a brand."""

    schema_version: int = SCHEMA_VERSION
    sessions: list[SessionMeta] = field(default_factory=list)
    active_session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sessions": [s.to_dict() for s in self.sessions],
            "active_session_id": self.active_session_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SessionIndex":
        sessions = [SessionMeta.from_dict(s) for s in d.get("sessions", [])]
        return cls(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            sessions=sessions,
            active_session_id=d.get("active_session_id"),
        )


@dataclass
class MessagesFile:
    """Messages file for a session."""

    schema_version: int = SCHEMA_VERSION
    session_id: str = ""
    settings: SessionSettings = field(default_factory=SessionSettings)
    summary: str | None = None
    summary_token_count: int = 0
    full_history: list[Message] = field(default_factory=list)
    prompt_window_start: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "settings": self.settings.to_dict(),
            "summary": self.summary,
            "summary_token_count": self.summary_token_count,
            "full_history": [m.to_dict() for m in self.full_history],
            "prompt_window_start": self.prompt_window_start,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MessagesFile":
        settings = SessionSettings.from_dict(d.get("settings", {}))
        msgs = [Message.from_dict(m) for m in d.get("full_history", [])]
        return cls(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            session_id=d.get("session_id", ""),
            settings=settings,
            summary=d.get("summary"),
            summary_token_count=d.get("summary_token_count", 0),
            full_history=msgs,
            prompt_window_start=d.get("prompt_window_start", 0),
        )


# endregion
# region File Operations
def atomic_write(path: Path, data: dict[str, Any]) -> None:
    """Write with temp file + rename for atomicity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / (path.name + ".tmp")
    backup_path = path.parent / (path.name + ".backup")
    # Backup current file if exists
    if path.exists():
        shutil.copy2(path, backup_path)
    # Write to temp, then atomic rename
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    tmp_path.rename(path)


def safe_read(path: Path, _depth: int = 0) -> dict[str, Any] | None:
    """Read with corruption handling. Returns None if unreadable."""
    if _depth > 1:
        return None
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        backup_path = path.parent / (path.name + ".backup")
        if backup_path.exists() and _depth == 0:
            result = safe_read(backup_path, _depth=1)
            if result:
                shutil.copy2(backup_path, path)
            return result
        return None
    except Exception as e:
        logger.warning(f"Failed to read {path}: {e}")
        return None


@contextmanager
def brand_lock(brand_slug: str) -> Iterator[None]:
    """Lock for read-modify-write of sessions/index.json."""
    lock_dir = get_brand_dir(brand_slug) / "sessions"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / ".index.lock"
    with open(lock_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


@contextmanager
def session_lock(brand_slug: str, session_id: str) -> Iterator[None]:
    """Lock for read-modify-write of session messages."""
    lock_dir = get_brand_dir(brand_slug) / "sessions" / session_id
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / ".session.lock"
    with open(lock_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


# endregion
# region Path Helpers
def get_sessions_dir(brand_slug: str) -> Path:
    """Get the sessions directory for a brand."""
    return get_brand_dir(brand_slug) / "sessions"


def get_session_dir(brand_slug: str, session_id: str) -> Path:
    """Get the directory for a specific session."""
    return get_sessions_dir(brand_slug) / session_id


def get_session_index_path(brand_slug: str) -> Path:
    """Get the path to the session index file."""
    return get_sessions_dir(brand_slug) / "index.json"


def get_messages_path(brand_slug: str, session_id: str) -> Path:
    """Get the path to the messages file for a session."""
    return get_session_dir(brand_slug, session_id) / "messages.json"


# endregion
# region SessionManager
class SessionManager:
    """Manages chat sessions for a brand.
    Provides CRUD operations with atomic writes and file locking.
    Usage:
        manager = SessionManager("my-brand")
        session = manager.create_session(SessionSettings())
        sessions = manager.list_sessions()
        manager.set_active_session(session.id)
    """

    def __init__(self, brand_slug: str):
        self.brand_slug = brand_slug
        self._index_path = get_session_index_path(brand_slug)

    def _load_index(self) -> SessionIndex:
        """Load session index, returning empty if missing/corrupt."""
        data = safe_read(self._index_path)
        if data is None:
            return SessionIndex()
        try:
            return SessionIndex.from_dict(data)
        except (TypeError, KeyError) as e:
            logger.warning(f"Invalid session index for {self.brand_slug}: {e}")
            return SessionIndex()

    def _save_index(self, index: SessionIndex) -> None:
        """Save session index atomically."""
        atomic_write(self._index_path, index.to_dict())

    def create_session(
        self, settings: SessionSettings | None = None, title: str = "New conversation"
    ) -> SessionMeta:
        """Create a new session.
        Args:
            settings: Optional session settings (uses defaults if None).
            title: Session title.
        Returns:
            Created SessionMeta.
        """
        with brand_lock(self.brand_slug):
            index = self._load_index()
            session_id = str(uuid.uuid4())
            now = utc_now_iso()
            meta = SessionMeta(
                id=session_id,
                brand_slug=self.brand_slug,
                title=title,
                created_at=now,
                last_active_at=now,
                updated_at=now,
                message_count=0,
                preview="",
            )
            # Create session directory and messages file
            session_dir = get_session_dir(self.brand_slug, session_id)
            session_dir.mkdir(parents=True, exist_ok=True)
            messages_file = MessagesFile(
                session_id=session_id, settings=settings or SessionSettings()
            )
            atomic_write(get_messages_path(self.brand_slug, session_id), messages_file.to_dict())
            # Update index
            index.sessions.append(meta)
            index.active_session_id = session_id
            self._save_index(index)
            logger.info(f"Created session {session_id} for brand {self.brand_slug}")
            return meta

    def get_session(self, session_id: str) -> SessionMeta | None:
        """Get session metadata by ID."""
        index = self._load_index()
        for s in index.sessions:
            if s.id == session_id:
                return s
        return None

    def list_sessions(self, include_archived: bool = False) -> list[SessionMeta]:
        """List all sessions, sorted by last_active_at descending."""
        index = self._load_index()
        sessions = index.sessions
        if not include_archived:
            sessions = [s for s in sessions if not s.is_archived]
        return sorted(sessions, key=lambda s: s.last_active_at, reverse=True)

    def get_active_session(self) -> SessionMeta | None:
        """Get the active session."""
        index = self._load_index()
        if not index.active_session_id:
            return None
        return self.get_session(index.active_session_id)

    def set_active_session(self, session_id: str) -> bool:
        """Set the active session.
        Args:
            session_id: Session ID to activate.
        Returns:
            True if session exists and was activated, False otherwise.
        """
        with brand_lock(self.brand_slug):
            index = self._load_index()
            # Validate session exists
            if not any(s.id == session_id for s in index.sessions):
                logger.warning(f"Session {session_id} not found for brand {self.brand_slug}")
                return False
            index.active_session_id = session_id
            self._save_index(index)
            logger.debug(f"Set active session to {session_id}")
            return True

    def update_session_meta(
        self,
        session_id: str,
        title: str | None = None,
        preview: str | None = None,
        message_count: int | None = None,
        is_archived: bool | None = None,
    ) -> bool:
        """Update session metadata.
        Args:
            session_id: Session ID to update.
            title: New title (optional).
            preview: New preview text (optional).
            message_count: New message count (optional).
            is_archived: Archive status (optional).
        Returns:
            True if updated, False if session not found.
        """
        with brand_lock(self.brand_slug):
            index = self._load_index()
            for s in index.sessions:
                if s.id == session_id:
                    now = utc_now_iso()
                    if title is not None:
                        s.title = title
                    if preview is not None:
                        s.preview = preview
                    if message_count is not None:
                        s.message_count = message_count
                    if is_archived is not None:
                        s.is_archived = is_archived
                    s.last_active_at = now
                    s.updated_at = now
                    self._save_index(index)
                    return True
            return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its files.
        Args:
            session_id: Session ID to delete.
        Returns:
            True if deleted, False if not found.
        """
        with brand_lock(self.brand_slug):
            index = self._load_index()
            # Find and remove from index
            original_len = len(index.sessions)
            index.sessions = [s for s in index.sessions if s.id != session_id]
            if len(index.sessions) == original_len:
                return False
            # Clear active if deleted
            if index.active_session_id == session_id:
                index.active_session_id = index.sessions[0].id if index.sessions else None
            self._save_index(index)
        # Delete session directory
        session_dir = get_session_dir(self.brand_slug, session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
        logger.info(f"Deleted session {session_id} from brand {self.brand_slug}")
        return True

    def load_messages_file(self, session_id: str) -> MessagesFile | None:
        """Load the messages file for a session."""
        path = get_messages_path(self.brand_slug, session_id)
        data = safe_read(path)
        if data is None:
            return None
        try:
            return MessagesFile.from_dict(data)
        except (TypeError, KeyError) as e:
            logger.warning(f"Invalid messages file for session {session_id}: {e}")
            return None

    def save_messages_file(self, session_id: str, messages_file: MessagesFile) -> None:
        """Save the messages file for a session."""
        with session_lock(self.brand_slug, session_id):
            path = get_messages_path(self.brand_slug, session_id)
            atomic_write(path, messages_file.to_dict())

    def get_session_settings(self, session_id: str) -> SessionSettings | None:
        """Get settings for a session."""
        mf = self.load_messages_file(session_id)
        return mf.settings if mf else None

    def save_session_settings(self, session_id: str, settings: SessionSettings) -> bool:
        """Save settings for a session.
        Returns:
            True if saved, False if session not found.
        """
        with session_lock(self.brand_slug, session_id):
            mf = self.load_messages_file(session_id)
            if mf is None:
                return False
            mf.settings = settings
            path = get_messages_path(self.brand_slug, session_id)
            atomic_write(path, mf.to_dict())
            return True


# endregion
