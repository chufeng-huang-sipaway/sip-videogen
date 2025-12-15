"""Token-aware conversation history management.

Manages conversation history with a token budget. When budget is exceeded,
old messages are summarized rather than dropped entirely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from sip_videogen.config.logging import get_logger

logger = get_logger(__name__)

__all__ = ["ConversationHistoryManager", "Message"]


@dataclass
class Message:
    """A single conversation message."""

    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


class ConversationHistoryManager:
    """Manages conversation history with token budget.

    When total tokens exceed the budget, old messages are summarized
    to make room for new ones. This preserves context while staying
    within limits.

    Usage:
        manager = ConversationHistoryManager(max_tokens=8000)
        manager.add("user", "Hello!")
        manager.add("assistant", "Hi there!")

        # Get formatted history for prompt
        history = manager.get_formatted(max_tokens=4000)
    """

    DEFAULT_MAX_TOKENS = 8000
    SUMMARY_THRESHOLD = 10  # Summarize when more than this many messages

    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS):
        """Initialize the history manager.

        Args:
            max_tokens: Maximum tokens to keep in history.
        """
        if max_tokens < 100:
            max_tokens = 100
        self._messages: list[Message] = []
        self._max_tokens = max_tokens
        self._summary: str | None = None  # Summary of old messages

    @property
    def message_count(self) -> int:
        """Number of messages in history."""
        return len(self._messages)

    def add(self, role: Literal["user", "assistant"], content: str) -> None:
        """Add a message to history.

        Args:
            role: "user" or "assistant"
            content: Message content
        """
        message = Message(role=role, content=content)
        self._messages.append(message)

        # Check if we need to compact
        total_tokens = self._estimate_total_tokens()
        if total_tokens > self._max_tokens:
            self._compact()

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

    def clear(self) -> None:
        """Clear all history."""
        self._messages.clear()
        self._summary = None
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
