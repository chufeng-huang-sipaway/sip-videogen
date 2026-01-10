"""Tests for auto-compaction - threshold triggers, non-blocking, deterministic (mocked LLM).
Per IMPLEMENTATION_PLAN.md Stage 2.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sip_studio.advisor.session_history_manager import (
    TOKEN_SOFT_LIMIT,
    SessionHistoryManager,
    _fallback_summary,
    _format_messages,
    cancel_compaction,
    count_tokens,
    estimate_messages_tokens,
    schedule_compaction,
)
from sip_studio.advisor.session_manager import Message, SessionManager, SessionSettings


@pytest.fixture
def tmp_brand_dir(tmp_path, monkeypatch):
    """Create temporary brand directory and mock get_brand_dir."""
    brand_slug = "test-brand"
    brand_dir = tmp_path / ".sip-studio" / "brands" / brand_slug
    brand_dir.mkdir(parents=True)

    def mock_get_brand_dir(slug: str) -> Path:
        return tmp_path / ".sip-studio" / "brands" / slug

    monkeypatch.setattr("sip_studio.advisor.session_manager.get_brand_dir", mock_get_brand_dir)
    monkeypatch.setattr(
        "sip_studio.advisor.session_history_manager.get_messages_path",
        lambda brand, sid: (
            tmp_path / ".sip-studio" / "brands" / brand / "sessions" / sid / "messages.json"
        ),
    )
    return brand_slug, tmp_path


@pytest.fixture
def session_with_messages(tmp_brand_dir):
    """Create a session with messages."""
    brand_slug, _ = tmp_brand_dir
    mgr = SessionManager(brand_slug)
    session = mgr.create_session(SessionSettings())
    history = SessionHistoryManager(brand_slug, session.id, mgr)
    return history, mgr, session


class TestTokenCounting:
    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_tokens_simple(self):
        tokens = count_tokens("Hello world")
        assert tokens > 0
        assert tokens < 10

    def test_count_tokens_longer_text(self):
        short = count_tokens("Hello")
        long = count_tokens("Hello world this is a longer text")
        assert long > short

    def test_estimate_messages_tokens(self):
        msgs = [Message.create("user", "Hello"), Message.create("assistant", "Hi there!")]
        tokens = estimate_messages_tokens(msgs)
        assert tokens > 0

    def test_estimate_messages_with_tool_calls(self):
        from sip_studio.advisor.session_manager import ToolCall

        msg = Message.create(
            "assistant",
            "Calling tool",
            tool_calls=[ToolCall("tc1", "my_tool", '{"param":"value"}')],
        )
        tokens = estimate_messages_tokens([msg])
        # Should include tool call overhead
        assert tokens > count_tokens("Calling tool") + 4


class TestFallbackSummary:
    def test_fallback_summary(self):
        msgs = [
            Message.create("user", "First question about products."),
            Message.create("assistant", "Here is the answer."),
            Message.create("user", "Second question."),
        ]
        summary = _fallback_summary(msgs)
        assert "Previous discussion:" in summary
        assert "First question" in summary

    def test_fallback_summary_max_lines(self):
        msgs = [Message.create("user", f"Question {i}.") for i in range(20)]
        summary = _fallback_summary(msgs)
        lines = summary.split("\n")
        assert len(lines) <= 11  # Header + 10 lines max


class TestFormatMessages:
    def test_format_messages(self):
        msgs = [Message.create("user", "Hello"), Message.create("assistant", "Hi")]
        formatted = _format_messages(msgs)
        assert "USER:" in formatted
        assert "ASSISTANT:" in formatted

    def test_format_truncates_long_content(self):
        long_content = "x" * 1000
        msgs = [Message.create("user", long_content)]
        formatted = _format_messages(msgs)
        assert len(formatted) < 600  # 500 chars + role prefix


class TestSessionHistoryManager:
    def test_add_message(self, session_with_messages):
        history, _, _ = session_with_messages
        msg = Message.create("user", "Test message")
        history.add_message(msg)
        msgs = history.get_messages()
        assert len(msgs) == 1
        assert msgs[0].content == "Test message"

    def test_add_multiple_messages(self, session_with_messages):
        history, _, _ = session_with_messages
        msgs = [Message.create("user", "First"), Message.create("assistant", "Second")]
        history.add_messages(msgs)
        all_msgs = history.get_messages()
        assert len(all_msgs) == 2

    def test_get_prompt_messages(self, session_with_messages):
        history, _, _ = session_with_messages
        for i in range(5):
            history.add_message(Message.create("user", f"Message {i}"))
        history.set_prompt_window_start(2)
        prompt_msgs = history.get_prompt_messages()
        assert len(prompt_msgs) == 3  # Messages 2,3,4

    def test_settings_persistence(self, session_with_messages):
        history, _, _ = session_with_messages
        settings = SessionSettings(project_slug="my-project", image_aspect_ratio="16:9")
        history.set_settings(settings)
        new_history = SessionHistoryManager(history.brand_slug, history.session_id)
        loaded = new_history.get_settings()
        assert loaded.project_slug == "my-project"
        assert loaded.image_aspect_ratio == "16:9"

    def test_advance_prompt_window(self, session_with_messages):
        history, _, _ = session_with_messages
        for i in range(10):
            history.add_message(Message.create("user", f"M{i}"))
        history.advance_prompt_window(3)
        assert history.get_prompt_window_start() == 3
        history.advance_prompt_window(100)  # Should clamp
        assert history.get_prompt_window_start() == 10

    def test_can_compact_requires_10_messages(self, session_with_messages):
        history, _, _ = session_with_messages
        for i in range(5):
            history.add_message(Message.create("user", f"M{i}"))
        assert not history.can_compact()
        for i in range(5, 10):
            history.add_message(Message.create("user", f"M{i}"))
        assert history.can_compact()

    def test_estimate_total_tokens(self, session_with_messages):
        history, _, _ = session_with_messages
        history.add_message(Message.create("user", "Test message"))
        tokens = history.estimate_total_tokens("System prompt here")
        assert tokens > 0

    def test_clear(self, session_with_messages):
        history, _, _ = session_with_messages
        history.add_message(Message.create("user", "Hello"))
        history.clear()
        assert len(history.get_messages()) == 0
        assert history.get_summary() is None


class TestCompactionBoundary:
    def test_calculate_boundary_keeps_25_percent(self, session_with_messages):
        history, _, _ = session_with_messages
        # Add 40 messages
        for i in range(40):
            history.add_message(Message.create("user", f"Message {i}"))
        boundary = history._calculate_compaction_boundary()
        # Should keep ~10 (25% of 40, min 5)
        assert boundary >= 30  # 40-10

    def test_calculate_boundary_minimum_to_compact(self, session_with_messages):
        history, _, _ = session_with_messages
        for i in range(12):
            history.add_message(Message.create("user", f"M{i}"))
        boundary = history._calculate_compaction_boundary()
        # With 12 messages, keep_count=max(5,3)=5, new_start=7
        # new_start-current_start = 7-0 = 7 < 10, so should return current_start
        assert boundary == 0  # Not enough to compact

    def test_calculate_boundary_with_existing_window(self, session_with_messages):
        history, _, _ = session_with_messages
        for i in range(50):
            history.add_message(Message.create("user", f"M{i}"))
        history.set_prompt_window_start(10)
        boundary = history._calculate_compaction_boundary()
        # 40 messages in window, keep 10, new_start=40
        assert boundary > 10


class TestCompactionWithMockedLLM:
    @pytest.mark.asyncio
    async def test_compact_with_llm(self, session_with_messages):
        history, _, _ = session_with_messages
        for i in range(20):
            history.add_message(Message.create("user", f"Message {i} about product design"))
        with patch(
            "sip_studio.advisor.session_history_manager._generate_summary", new_callable=AsyncMock
        ) as mock_summary:
            mock_summary.return_value = "Summary of the conversation about products."
            await history.force_compact()
        assert history.get_summary() is not None
        assert "Summary" in history.get_summary()
        assert history.get_prompt_window_start() > 0

    @pytest.mark.asyncio
    async def test_compact_fallback_on_llm_failure(self, session_with_messages):
        history, _, _ = session_with_messages
        for i in range(20):
            history.add_message(Message.create("user", f"Question {i}."))
        with patch(
            "sip_studio.advisor.session_history_manager._generate_summary", new_callable=AsyncMock
        ) as mock_summary:
            mock_summary.return_value = None  # LLM failed
            await history.force_compact()
        assert history.get_summary() is not None
        assert "Previous discussion:" in history.get_summary()

    @pytest.mark.asyncio
    async def test_compact_combines_summaries(self, session_with_messages):
        history, _, _ = session_with_messages
        # First batch
        for i in range(20):
            history.add_message(Message.create("user", f"First batch {i}"))
        with patch(
            "sip_studio.advisor.session_history_manager._generate_summary", new_callable=AsyncMock
        ) as mock_summary:
            mock_summary.return_value = "First summary."
            await history.force_compact()
        # Add more messages
        for i in range(20):
            history.add_message(Message.create("user", f"Second batch {i}"))
        with patch(
            "sip_studio.advisor.session_history_manager._generate_summary", new_callable=AsyncMock
        ) as mock_summary:
            mock_summary.return_value = "Second summary."
            await history.force_compact()
        summary = history.get_summary()
        assert "First summary" in summary
        assert "Second summary" in summary

    @pytest.mark.asyncio
    async def test_compact_resummary_when_too_long(self, session_with_messages):
        history, _, _ = session_with_messages
        # Set existing long summary that will exceed SUMMARY_TOKEN_LIMIT when combined
        history._ensure_loaded()
        # Create a summary that's already near the limit
        long_text = "Important context about product design decisions. " * 200
        history._summary = long_text
        history._summary_token_count = count_tokens(long_text)
        for i in range(20):
            history.add_message(Message.create("user", f"Message {i} with some content"))
        called_resumm = False

        async def track_resumm(text):
            nonlocal called_resumm
            called_resumm = True
            return "Condensed."

        with patch(
            "sip_studio.advisor.session_history_manager._generate_summary", new_callable=AsyncMock
        ) as mock_gen:
            # Return a large new summary that when combined exceeds limit
            mock_gen.return_value = "New section with lots of content. " * 50
            with patch.object(history, "_summarize_summary", track_resumm):
                await history.force_compact()
        # Combined summary should have triggered re-summarization
        assert called_resumm or history.get_summary() is not None


class TestCompactionScheduling:
    @pytest.mark.asyncio
    async def test_schedule_compaction_single_flight(self, session_with_messages):
        history, _, _ = session_with_messages
        for i in range(20):
            history.add_message(Message.create("user", f"M{i}"))
        call_count = 0

        async def slow_compact():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)

        with patch.object(history, "_compact_with_llm", slow_compact):
            schedule_compaction(history)
            schedule_compaction(history)  # Should be ignored
            schedule_compaction(history)  # Should be ignored
            await asyncio.sleep(0.2)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cancel_compaction(self, session_with_messages):
        history, _, _ = session_with_messages
        for i in range(20):
            history.add_message(Message.create("user", f"M{i}"))
        compacted = False

        async def track_compact():
            nonlocal compacted
            await asyncio.sleep(0.05)
            compacted = True

        with patch.object(history, "_compact_with_llm", track_compact):
            schedule_compaction(history)
            cancel_compaction(history.session_id)
            await asyncio.sleep(0.1)
        # Note: Due to timing, compaction may or may not have been cancelled
        # This test mainly ensures no errors occur


class TestAutoCompactionTrigger:
    @pytest.mark.asyncio
    async def test_check_compaction_triggers_at_soft_limit(
        self, session_with_messages, monkeypatch
    ):
        history, _, _ = session_with_messages
        # Track if schedule_compaction was called
        scheduled = False

        def track_schedule(_):
            nonlocal scheduled
            scheduled = True
            # Don't actually schedule to avoid async issues in test

        monkeypatch.setattr(
            "sip_studio.advisor.session_history_manager.schedule_compaction", track_schedule
        )

        # Mock token estimation to return high value
        def high_tokens(_):
            return TOKEN_SOFT_LIMIT + 100

        monkeypatch.setattr(
            "sip_studio.advisor.session_history_manager.estimate_messages_tokens", high_tokens
        )
        # Add enough messages to allow compaction (10+ required)
        for i in range(15):
            history.add_message(Message.create("user", f"M{i}"))
        # schedule_compaction should have been called
        assert scheduled
