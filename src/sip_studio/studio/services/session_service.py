"""Session management service for chat conversations."""

from __future__ import annotations

from sip_studio.advisor.session_manager import Message, SessionManager, SessionMeta, SessionSettings
from sip_studio.config.logging import get_logger

from ..state import BridgeState
from ..utils.bridge_types import bridge_error, bridge_ok

logger = get_logger(__name__)


class SessionService:
    """Session CRUD for chat history management."""

    def __init__(self, state: BridgeState):
        self._state = state

    def _get_manager(self) -> SessionManager:
        """Get SessionManager for active brand. Raises if no brand selected."""
        slug = self._state.get_active_slug()
        if not slug:
            raise ValueError("No brand selected")
        return SessionManager(slug)

    def list_sessions(self, brand_slug: str | None = None, include_archived: bool = False) -> dict:
        """List all sessions for a brand."""
        try:
            slug = brand_slug or self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            mgr = SessionManager(slug)
            sessions = mgr.list_sessions(include_archived=include_archived)
            return bridge_ok({"sessions": [_meta_to_dict(s) for s in sessions]})
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return bridge_error(str(e))

    def get_session(self, session_id: str) -> dict:
        """Get session metadata by ID."""
        try:
            mgr = self._get_manager()
            session = mgr.get_session(session_id)
            if not session:
                return bridge_error(f"Session '{session_id}' not found")
            return bridge_ok(_meta_to_dict(session))
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return bridge_error(str(e))

    def get_active_session(self) -> dict:
        """Get the active session for current brand."""
        try:
            mgr = self._get_manager()
            session = mgr.get_active_session()
            return bridge_ok(_meta_to_dict(session) if session else None)
        except Exception as e:
            logger.error(f"Failed to get active session: {e}")
            return bridge_error(str(e))

    def create_session(self, title: str | None = None, settings: dict | None = None) -> dict:
        """Create a new session."""
        try:
            mgr = self._get_manager()
            sess_settings = SessionSettings.from_dict(settings) if settings else SessionSettings()
            # Handle JS undefined/null -> Python None
            session = mgr.create_session(settings=sess_settings, title=title or "New conversation")
            # Clear cached advisor so next chat uses new session
            self._state.advisor = None
            return bridge_ok(_meta_to_dict(session))
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return bridge_error(str(e))

    def set_active_session(self, session_id: str) -> dict:
        """Set the active session."""
        try:
            mgr = self._get_manager()
            if not mgr.set_active_session(session_id):
                return bridge_error(f"Session '{session_id}' not found")
            # Clear cached advisor so next chat uses new session
            self._state.advisor = None
            return bridge_ok({"active_session_id": session_id})
        except Exception as e:
            logger.error(f"Failed to set active session: {e}")
            return bridge_error(str(e))

    def update_session(
        self, session_id: str, title: str | None = None, is_archived: bool | None = None
    ) -> dict:
        """Update session metadata."""
        try:
            mgr = self._get_manager()
            if not mgr.update_session_meta(session_id, title=title, is_archived=is_archived):
                return bridge_error(f"Session '{session_id}' not found")
            session = mgr.get_session(session_id)
            return bridge_ok(_meta_to_dict(session) if session else None)
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            return bridge_error(str(e))

    def delete_session(self, session_id: str) -> dict:
        """Delete a session and all its data."""
        try:
            mgr = self._get_manager()
            if not mgr.delete_session(session_id):
                return bridge_error(f"Session '{session_id}' not found")
            return bridge_ok()
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return bridge_error(str(e))

    def load_session(self, session_id: str, limit: int = 50, before: str | None = None) -> dict:
        """Load session with messages (paginated).
        Args:
            session_id: Session ID to load
            limit: Max messages to return (default 50)
            before: ISO timestamp to load messages before (for pagination)
        Returns:
            Session data with settings, summary, and paginated messages
        """
        # Handle None limit (can happen when JS passes undefined)
        if limit is None:
            limit = 50
        try:
            mgr = self._get_manager()
            session = mgr.get_session(session_id)
            if not session:
                return bridge_error(f"Session '{session_id}' not found")
            mf = mgr.load_messages_file(session_id)
            if not mf:
                return bridge_error(f"Messages file not found for session '{session_id}'")
            # Pagination: filter by timestamp if before is provided
            all_msgs = mf.full_history
            if before:
                all_msgs = [m for m in all_msgs if m.timestamp < before]
            has_more = len(all_msgs) > limit
            msgs = all_msgs[-limit:] if len(all_msgs) > limit else all_msgs
            return bridge_ok(
                {
                    "session": _meta_to_dict(session),
                    "settings": mf.settings.to_dict(),
                    "summary": mf.summary,
                    "messages": [_msg_to_dict(m) for m in msgs],
                    "hasMore": has_more,
                    "totalMessageCount": len(mf.full_history),
                }
            )
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return bridge_error(str(e))

    def get_session_settings(self, session_id: str) -> dict:
        """Get settings for a session."""
        try:
            mgr = self._get_manager()
            settings = mgr.get_session_settings(session_id)
            if not settings:
                return bridge_error(f"Session '{session_id}' not found")
            return bridge_ok(settings.to_dict())
        except Exception as e:
            logger.error(f"Failed to get session settings: {e}")
            return bridge_error(str(e))

    def save_session_settings(self, session_id: str, settings: dict) -> dict:
        """Save settings for a session."""
        try:
            mgr = self._get_manager()
            sess_settings = SessionSettings.from_dict(settings)
            if not mgr.save_session_settings(session_id, sess_settings):
                return bridge_error(f"Session '{session_id}' not found")
            return bridge_ok()
        except Exception as e:
            logger.error(f"Failed to save session settings: {e}")
            return bridge_error(str(e))


# Helper functions
def _meta_to_dict(meta: SessionMeta) -> dict:
    """Convert SessionMeta to frontend-friendly dict."""
    return {
        "id": meta.id,
        "brandSlug": meta.brand_slug,
        "title": meta.title,
        "createdAt": meta.created_at,
        "lastActiveAt": meta.last_active_at,
        "updatedAt": meta.updated_at,
        "messageCount": meta.message_count,
        "preview": meta.preview,
        "isArchived": meta.is_archived,
    }


def _msg_to_dict(msg: Message) -> dict:
    """Convert Message to frontend-friendly dict."""
    d: dict = {"id": msg.id, "role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
    if msg.tool_calls:
        d["toolCalls"] = [
            {"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in msg.tool_calls
        ]
    if msg.tool_call_id:
        d["toolCallId"] = msg.tool_call_id
    if msg.attachments:
        d["attachments"] = [{"type": a.type, "url": a.url, "name": a.name} for a in msg.attachments]
    if msg.metadata:
        d["metadata"] = msg.metadata
    return d
