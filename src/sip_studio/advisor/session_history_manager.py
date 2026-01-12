"""Session-aware conversation history manager with auto-compaction.
Manages message history for a session with LLM-based summarization.
Per IMPLEMENTATION_PLAN.md Stage 2.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from sip_studio.advisor.session_manager import (
    Message,
    MessagesFile,
    SessionManager,
    SessionSettings,
    atomic_write,
    get_messages_path,
    safe_read,
    session_lock,
)
from sip_studio.config.logging import get_logger

if TYPE_CHECKING:
    pass
logger = get_logger(__name__)
__all__ = [
    "SessionHistoryManager",
    "count_tokens",
    "estimate_messages_tokens",
    "schedule_compaction",
    "cancel_compaction",
    "COMPACTION_THRESHOLD",
    "SUMMARY_TARGET_TOKENS",
    "CHARS_PER_TOKEN",
    # Legacy aliases for backward compatibility
    "TOKEN_SOFT_LIMIT",
    "TOKEN_HARD_LIMIT",
    "MAX_CONTEXT_LIMIT",
    "SUMMARY_TOKEN_LIMIT",
]
# region Token Counting
# Use character-based approximation (~4 chars per token for English text)
# This avoids tiktoken's runtime dependency on encoding data files
CHARS_PER_TOKEN = 4


def count_tokens(text: str) -> int:
    """Estimate tokens in text using character count (~4 chars/token)."""
    if not text:
        return 0
    return len(text) // CHARS_PER_TOKEN


def estimate_messages_tokens(messages: list[Message]) -> int:
    """Estimate total tokens in a list of messages."""
    total = 0
    for m in messages:
        total += count_tokens(m.content) + 4
        if m.tool_calls:
            for tc in m.tool_calls:
                total += count_tokens(tc.arguments) + 10
    return total


# endregion
# region Constants
# GPT-5.1 has 272K context window - compact at ~75% to preserve context before server truncation
COMPACTION_THRESHOLD = 200_000  # Trigger compaction at 200K tokens
SUMMARY_TARGET_TOKENS = 2_000  # Target summary size
# Legacy constants (kept for backward compatibility, will be removed)
TOKEN_SOFT_LIMIT = COMPACTION_THRESHOLD  # Alias for old code
TOKEN_HARD_LIMIT = 250_000  # Alias for old code
TOKEN_SAFETY_MARGIN = 20_000
SUMMARY_TOKEN_LIMIT = SUMMARY_TARGET_TOKENS
MAX_CONTEXT_LIMIT = 250_000  # Server handles actual limit
# endregion
# region LLM Helpers
_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI()
    return _openai_client


async def _call_llm_with_retry(prompt: str, max_tokens: int = 500) -> str | None:
    """LLM call with timeout/retry/backoff. Returns None on failure."""
    client = _get_openai_client()
    for attempt in range(3):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                ),
                timeout=30.0,
            )
            return response.choices[0].message.content
        except asyncio.TimeoutError:
            if attempt == 2:
                return None
            await asyncio.sleep(2**attempt)
        except Exception as e:
            if "rate_limit" in str(e).lower():
                await asyncio.sleep(5 * (attempt + 1))
            else:
                logging.warning(f"LLM call failed: {e}")
                return None
    return None


def _format_messages(messages: list[Message]) -> str:
    """Format messages for summarization prompt."""
    lines = []
    for m in messages:
        role = m.role.upper()
        content = m.content[:500] if len(m.content) > 500 else m.content
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


async def _generate_summary(messages: list[Message]) -> str | None:
    """Generate summary of messages using LLM."""
    prompt = f"""Summarize this conversation concisely, preserving:
- Key decisions made
- Important context about products/projects
- Preferences or constraints established

Conversation:
{_format_messages(messages)}

Summary (2-3 paragraphs max):"""
    return await _call_llm_with_retry(prompt)


def _fallback_summary(messages: list[Message]) -> str:
    """Extractive fallback when LLM unavailable."""
    lines = []
    for m in messages:
        if m.role == "user":
            first_sent = m.content.split(".")[0][:100]
            lines.append(f"- {first_sent}")
    return "Previous discussion:\n" + "\n".join(lines[:10])


# endregion
# region Compaction Scheduling
_compaction_tasks: dict[str, asyncio.Task] = {}
_compaction_cancel_flags: dict[str, bool] = {}


def schedule_compaction(history: "SessionHistoryManager") -> None:
    """Schedule compaction. Single-flight per session."""
    session_id = history.session_id
    # If already running, just return (single-flight)
    if session_id in _compaction_tasks and not _compaction_tasks[session_id].done():
        return

    async def _run_compaction():
        _compaction_cancel_flags[session_id] = False
        try:
            # Check cancel flag before expensive operations
            if _compaction_cancel_flags.get(session_id):
                return
            with session_lock(history.brand_slug, session_id):
                if _compaction_cancel_flags.get(session_id):
                    return
                await history._compact_with_llm()
        except Exception as e:
            logging.warning(f"Compaction failed for {session_id}: {e}")
        finally:
            _compaction_tasks.pop(session_id, None)
            _compaction_cancel_flags.pop(session_id, None)

    task = asyncio.create_task(_run_compaction())
    _compaction_tasks[session_id] = task


def cancel_compaction(session_id: str) -> None:
    """Request cooperative cancellation of compaction."""
    _compaction_cancel_flags[session_id] = True


# endregion
# region SessionHistoryManager
class SessionHistoryManager:
    """Manages conversation history for a single session.
    Handles message storage, retrieval, and auto-compaction.
    Per IMPLEMENTATION_PLAN.md - this is the session-aware replacement
    for ConversationHistoryManager.
    Usage:
        manager = SessionHistoryManager("brand-slug", "session-id")
        manager.add_message(Message.create("user", "Hello"))
        messages = manager.get_prompt_messages()
    """

    def __init__(
        self, brand_slug: str, session_id: str, session_manager: SessionManager | None = None
    ):
        self.brand_slug = brand_slug
        self.session_id = session_id
        self._session_manager = session_manager or SessionManager(brand_slug)
        self._messages_path = get_messages_path(brand_slug, session_id)
        self._messages: list[Message] = []
        self._settings: SessionSettings = SessionSettings()
        self._summary: str | None = None
        self._summary_token_count: int = 0
        self._prompt_window_start: int = 0
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load from disk if not already loaded."""
        if self._loaded:
            return
        data = safe_read(self._messages_path)
        if data is not None:
            try:
                mf = MessagesFile.from_dict(data)
                self._messages = mf.full_history
                self._settings = mf.settings
                self._summary = mf.summary
                self._summary_token_count = mf.summary_token_count
                self._prompt_window_start = mf.prompt_window_start
            except (TypeError, KeyError) as e:
                logger.warning(f"Failed to load messages for {self.session_id}: {e}")
        self._loaded = True

    def _save(self) -> None:
        """Save current state to disk."""
        mf = MessagesFile(
            session_id=self.session_id,
            settings=self._settings,
            summary=self._summary,
            summary_token_count=self._summary_token_count,
            full_history=self._messages,
            prompt_window_start=self._prompt_window_start,
        )
        atomic_write(self._messages_path, mf.to_dict())

    def save(self) -> None:
        """Public save method for external use."""
        self._ensure_loaded()
        with session_lock(self.brand_slug, self.session_id):
            self._save()

    def _generate_title(self, content: str, max_len: int = 50) -> str:
        """Generate session title from message content."""
        text = content.strip().split("\n")[0]
        if len(text) <= max_len:
            return text
        # Truncate at word boundary
        truncated = text[:max_len].rsplit(" ", 1)[0]
        return truncated + "..." if truncated else text[:max_len] + "..."

    def add_message(self, message: Message) -> None:
        """Add a message and save."""
        self._ensure_loaded()
        with session_lock(self.brand_slug, self.session_id):
            self._messages.append(message)
            self._save()
            # Update session meta
            preview = message.content[:100] if message.content else ""
            new_count = len(self._messages)
            # Auto-generate title on first user message
            title = None
            if message.role == "user" and new_count == 1:
                current = self._session_manager.get_session(self.session_id)
                if current and current.title == "New conversation":
                    title = self._generate_title(message.content)
            self._session_manager.update_session_meta(
                self.session_id, message_count=new_count, preview=preview, title=title
            )
        # Check if compaction needed
        self._check_compaction()

    def add_messages(self, messages: list[Message]) -> None:
        """Add multiple messages at once."""
        self._ensure_loaded()
        with session_lock(self.brand_slug, self.session_id):
            was_empty = len(self._messages) == 0
            self._messages.extend(messages)
            self._save()
            if messages:
                preview = messages[-1].content[:100] if messages[-1].content else ""
                # Auto-generate title from first user message if adding to empty session
                title = None
                if was_empty:
                    first_user = next((m for m in messages if m.role == "user"), None)
                    if first_user:
                        current = self._session_manager.get_session(self.session_id)
                        if current and current.title == "New conversation":
                            title = self._generate_title(first_user.content)
                self._session_manager.update_session_meta(
                    self.session_id, message_count=len(self._messages), preview=preview, title=title
                )
        self._check_compaction()

    def get_messages(self) -> list[Message]:
        """Get all messages (full history)."""
        self._ensure_loaded()
        return list(self._messages)

    def get_prompt_messages(self) -> list[Message]:
        """Get messages for prompt (from prompt_window_start)."""
        self._ensure_loaded()
        return list(self._messages[self._prompt_window_start :])

    def get_summary(self) -> str | None:
        """Get current summary."""
        self._ensure_loaded()
        return self._summary

    def get_settings(self) -> SessionSettings:
        """Get session settings."""
        self._ensure_loaded()
        return self._settings

    def set_settings(self, settings: SessionSettings) -> None:
        """Update session settings."""
        self._ensure_loaded()
        with session_lock(self.brand_slug, self.session_id):
            self._settings = settings
            self._save()

    def get_prompt_window_start(self) -> int:
        """Get current prompt window start index."""
        self._ensure_loaded()
        return self._prompt_window_start

    def set_prompt_window_start(self, index: int) -> None:
        """Set prompt window start index."""
        self._ensure_loaded()
        with session_lock(self.brand_slug, self.session_id):
            self._prompt_window_start = max(0, min(index, len(self._messages)))
            self._save()

    def advance_prompt_window(self, count: int) -> None:
        """Advance prompt window by count messages."""
        self._ensure_loaded()
        with session_lock(self.brand_slug, self.session_id):
            self._prompt_window_start = min(self._prompt_window_start + count, len(self._messages))
            self._save()

    def can_compact(self) -> bool:
        """Check if compaction is possible."""
        self._ensure_loaded()
        messages_in_window = len(self._messages) - self._prompt_window_start
        return messages_in_window >= 10

    def _check_compaction(self) -> None:
        """Check if compaction should be triggered at 200K threshold."""
        self._ensure_loaded()
        # Simple character-based estimation (~4 chars per token)
        total_chars = sum(len(m.content) for m in self._messages)
        if self._summary:
            total_chars += len(self._summary)
        estimated_tokens = total_chars // CHARS_PER_TOKEN
        if estimated_tokens >= COMPACTION_THRESHOLD and self.can_compact():
            schedule_compaction(self)

    def _calculate_compaction_boundary(self) -> int:
        """Determine where to split messages for compaction."""
        current_start = self._prompt_window_start
        messages_in_window = self._messages[current_start:]
        # Keep most recent 25% of messages
        keep_count = max(5, len(messages_in_window) // 4)
        new_start = len(self._messages) - keep_count
        # Minimum 10 messages to compact
        if new_start - current_start < 10:
            return current_start
        return new_start

    async def _compact_with_llm(self) -> None:
        """Compact with summary size management and reset response chain."""
        new_start = self._calculate_compaction_boundary()
        if new_start == self._prompt_window_start:
            return
        messages_to_summarize = self._messages[self._prompt_window_start : new_start]
        new_summary = await _generate_summary(messages_to_summarize)
        if new_summary is None:
            new_summary = _fallback_summary(messages_to_summarize)
        if self._summary:
            combined = f"{self._summary}\n\n---\n\n{new_summary}"
            combined_tokens = count_tokens(combined)
            if combined_tokens > SUMMARY_TOKEN_LIMIT:
                condensed = await self._summarize_summary(combined)
                combined = (
                    condensed if condensed else combined[: SUMMARY_TOKEN_LIMIT * CHARS_PER_TOKEN]
                )
            self._summary = combined
            self._summary_token_count = count_tokens(combined)
        else:
            self._summary = new_summary
            self._summary_token_count = count_tokens(new_summary)
        self._prompt_window_start = new_start
        self._save()
        # Reset response chain - next turn starts fresh with summary in system prompt
        if self._session_manager:
            self._session_manager.update_session_response_id(self.session_id, None)
        logger.info(f"Compacted {self.session_id}, window={new_start}, chain reset")

    async def _summarize_summary(self, long_summary: str) -> str | None:
        """Re-summarize an overly long summary."""
        prompt = f"""Condense this conversation summary to ~500 words:
{long_summary}

Condensed summary:"""
        return await _call_llm_with_retry(prompt)

    async def force_compact(self) -> None:
        """Force immediate compaction (for testing or manual trigger)."""
        self._ensure_loaded()
        with session_lock(self.brand_slug, self.session_id):
            await self._compact_with_llm()

    def estimate_total_tokens(self, system_prompt: str = "") -> int:
        """Estimate total tokens for current context."""
        self._ensure_loaded()
        total = count_tokens(system_prompt) if system_prompt else 0
        if self._summary:
            total += self._summary_token_count
        total += estimate_messages_tokens(self._messages[self._prompt_window_start :])
        return total

    def clear(self) -> None:
        """Clear all messages and summary."""
        self._ensure_loaded()
        with session_lock(self.brand_slug, self.session_id):
            self._messages = []
            self._summary = None
            self._summary_token_count = 0
            self._prompt_window_start = 0
            self._save()
            self._session_manager.update_session_meta(self.session_id, message_count=0, preview="")


# endregion
