"""Token-aware conversation history management.
Manages conversation history with a token budget. When budget is exceeded,
old messages are summarized rather than dropped entirely.
Supports persistence to disk for history survival across app restarts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from sip_studio.config.logging import get_logger

logger = get_logger(__name__)
__all__ = ["ConversationHistoryManager", "Message"]
HISTORY_VERSION = 1
HISTORY_FILENAME = "chat_history.json"


@dataclass
class Message:
    """A single conversation message."""

    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp.isoformat()}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Message":
        ts = datetime.fromisoformat(d["timestamp"]) if d.get("timestamp") else datetime.now()
        return cls(role=d["role"], content=d["content"], timestamp=ts)


class ConversationHistoryManager:
    """Manages conversation history with token budget and optional persistence.
    When total tokens exceed the budget, old messages are summarized
    to make room for new ones. This preserves context while staying within limits.
    Supports auto-save to disk when brand_dir is provided.
    Usage:
        manager = ConversationHistoryManager(max_tokens=8000)
        manager.add("user", "Hello!")
        manager.add("assistant", "Hi there!")
        # Get formatted history for prompt
        history = manager.get_formatted(max_tokens=4000)
        # With persistence:
        manager = ConversationHistoryManager(max_tokens=8000, brand_dir=Path("/path/to/brand"))
        manager.load_from_disk()  # Load existing history
        manager.add("user", "Hello!")  # Auto-saves to disk
    """

    DEFAULT_MAX_TOKENS = 8000
    SUMMARY_THRESHOLD = 10

    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS, brand_dir: Path | None = None):
        """Initialize the history manager.
        Args:
            max_tokens: Maximum tokens to keep in history.
            brand_dir: Optional brand directory for auto-persistence.
        """
        if max_tokens < 100:
            max_tokens = 100
        self._messages: list[Message] = []
        self._max_tokens = max_tokens
        self._summary: str | None = None
        self._brand_dir = brand_dir

    @property
    def message_count(self) -> int:
        """Number of messages in history."""
        return len(self._messages)

    @property
    def brand_dir(self) -> Path | None:
        """Get the brand directory for persistence."""
        return self._brand_dir

    @brand_dir.setter
    def brand_dir(self, value: Path | None) -> None:
        """Set the brand directory for persistence."""
        self._brand_dir = value

    def add(self, role: Literal["user", "assistant"], content: str) -> None:
        """Add a message to history. Auto-saves if brand_dir is set.
        Args:
            role: "user" or "assistant"
            content: Message content
        """
        msg = Message(role=role, content=content)
        self._messages.append(msg)
        total = self._estimate_total_tokens()
        if total > self._max_tokens:
            self._compact()
        if self._brand_dir:
            self.save_to_disk()

    def save_to_disk(self, brand_dir: Path | None = None) -> bool:
        """Save history to disk.
        Args:
            brand_dir: Override brand directory (uses self._brand_dir if None)
        Returns:
            True if saved successfully, False otherwise.
        """
        d = brand_dir or self._brand_dir
        if not d:
            return False
        try:
            d.mkdir(parents=True, exist_ok=True)
            fp = d / HISTORY_FILENAME
            data = {
                "version": HISTORY_VERSION,
                "summary": self._summary,
                "messages": [m.to_dict() for m in self._messages],
            }
            from sip_studio.utils.file_utils import write_atomically

            write_atomically(fp, json.dumps(data, indent=2, ensure_ascii=False))
            logger.debug(f"Saved {len(self._messages)} messages to {fp}")
            return True
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            return False

    def load_from_disk(self, brand_dir: Path | None = None) -> bool:
        """Load history from disk.
        Args:
            brand_dir: Override brand directory (uses self._brand_dir if None)
        Returns:
            True if loaded successfully, False otherwise.
        """
        d = brand_dir or self._brand_dir
        if not d:
            return False
        fp = d / HISTORY_FILENAME
        if not fp.exists():
            logger.debug(f"No history file at {fp}")
            return False
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            v = data.get("version", 0)
            if v != HISTORY_VERSION:
                logger.warning(f"History version mismatch: {v} vs {HISTORY_VERSION}, clearing")
                return False
            self._summary = data.get("summary")
            self._messages = [Message.from_dict(m) for m in data.get("messages", [])]
            logger.info(f"Loaded {len(self._messages)} messages from {fp}")
            return True
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return False

    def delete_from_disk(self, brand_dir: Path | None = None) -> bool:
        """Delete history file from disk.
        Args:
            brand_dir: Override brand directory (uses self._brand_dir if None)
        Returns:
            True if deleted successfully, False otherwise.
        """
        d = brand_dir or self._brand_dir
        if not d:
            return False
        fp = d / HISTORY_FILENAME
        if fp.exists():
            try:
                fp.unlink()
                logger.debug(f"Deleted history file {fp}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete history: {e}")
                return False
        return True

    def get_formatted(self, max_tokens: int | None = None) -> str:
        """Get formatted history string for prompt injection.

        Args:
            max_tokens: Optional token limit (uses default if not specified)

        Returns:
            Formatted conversation history string
        """
        limit = max_tokens or self._max_tokens

        parts = []

        # Include summary if we have one
        if self._summary:
            parts.append(f"[Earlier conversation summary: {self._summary}]\n")

        # Format recent messages
        current_tokens = self._estimate_tokens(self._summary or "")

        for msg in self._messages:
            msg_text = f"{'User' if msg.role == 'user' else 'Assistant'}: {msg.content}"
            msg_tokens = self._estimate_tokens(msg_text)

            if current_tokens + msg_tokens > limit:
                parts.append("[... older messages truncated ...]")
                break

            parts.append(msg_text)
            current_tokens += msg_tokens

        return "\n\n".join(parts)

    def clear(self, delete_file: bool = False) -> None:
        """Clear all history.
        Args:
            delete_file: If True, also delete the history file from disk.
        """
        self._messages.clear()
        self._summary = None
        if delete_file and self._brand_dir:
            self.delete_from_disk()
        logger.debug("Cleared conversation history")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count with conservative heuristic.

        Uses ~3 chars per token as base, but counts CJK and emoji separately
        since they consume more tokens. Intentionally overestimates to prevent
        context overflow.
        """
        # Count CJK characters
        cjk_pattern = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af]")
        cjk_count = len(cjk_pattern.findall(text))

        # Count emoji
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
            r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]"
        )
        emoji_count = len(emoji_pattern.findall(text))

        # Base tokens for remaining text
        remaining_chars = len(text) - cjk_count - emoji_count
        base_tokens = remaining_chars // 3

        # Add extra for CJK and emoji
        cjk_tokens = int(cjk_count * 1.5)
        emoji_tokens = int(emoji_count * 2.5)

        return base_tokens + cjk_tokens + emoji_tokens + 1

    def _estimate_total_tokens(self) -> int:
        """Estimate total tokens in all messages."""
        total = self._estimate_tokens(self._summary or "")
        for msg in self._messages:
            total += self._estimate_tokens(msg.content)
        return total

    def _compact(self) -> None:
        """Compact history by summarizing old messages."""
        if len(self._messages) <= self.SUMMARY_THRESHOLD:
            # Not enough messages to summarize, just truncate oldest
            while self._estimate_total_tokens() > self._max_tokens and self._messages:
                removed = self._messages.pop(0)
                logger.debug(f"Removed oldest message ({removed.role})")
            return

        # Summarize older half of messages
        split_point = len(self._messages) // 2
        old_messages = self._messages[:split_point]
        self._messages = self._messages[split_point:]

        # Create summary of old messages
        summary_parts = []
        for msg in old_messages:
            preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            summary_parts.append(f"{msg.role}: {preview}")

        new_summary = "; ".join(summary_parts)

        # Combine with existing summary if present
        if self._summary:
            self._summary = f"{self._summary} ... {new_summary}"
        else:
            self._summary = new_summary

        # Truncate summary if too long
        max_summary_tokens = self._max_tokens // 4
        max_summary_chars = max_summary_tokens * 3  # Conservative
        if len(self._summary) > max_summary_chars:
            self._summary = self._summary[:max_summary_chars] + "..."

        logger.debug(
            f"Compacted history: summarized {len(old_messages)} messages, "
            f"kept {len(self._messages)} recent"
        )
