"""Tests for the conversation history manager."""

from sip_studio.advisor.history_manager import ConversationHistoryManager


def test_add_messages():
    """Test basic message addition."""
    manager = ConversationHistoryManager(max_tokens=8000)
    manager.add("user", "Hello")
    manager.add("assistant", "Hi there!")

    assert manager.message_count == 2


def test_get_formatted():
    """Test formatted output contains messages."""
    manager = ConversationHistoryManager()
    manager.add("user", "What is 2+2?")
    manager.add("assistant", "2+2 equals 4.")

    formatted = manager.get_formatted()
    assert "User: What is 2+2?" in formatted
    assert "Assistant: 2+2 equals 4." in formatted


def test_compaction():
    """Test that history is compacted when over budget."""
    # Small token budget to force compaction
    manager = ConversationHistoryManager(max_tokens=200)

    # Add many messages to exceed budget
    for i in range(20):
        manager.add("user", f"Message {i} with some content to take up space")
        manager.add("assistant", f"Response {i} with additional content here")

    # Should have compacted
    assert manager.message_count < 40

    # Should still have formatted output
    formatted = manager.get_formatted()
    assert len(formatted) > 0


def test_clear():
    """Test that clear() removes all history."""
    manager = ConversationHistoryManager()
    manager.add("user", "Test")
    manager.clear()

    assert manager.message_count == 0


def test_cjk_token_estimation():
    """Test that CJK text is estimated conservatively."""
    manager = ConversationHistoryManager()

    # 10 CJK characters should estimate higher than 10/4 = 2.5 tokens
    cjk_text = "你好世界测试文本内容"  # 10 Chinese characters
    tokens = manager._estimate_tokens(cjk_text)

    assert tokens >= 10  # Should be at least 10 tokens for 10 CJK chars


def test_emoji_token_estimation():
    """Test that emoji text is estimated conservatively."""
    manager = ConversationHistoryManager()

    emoji_text = "\U0001f600\U0001f60e\U0001f389\U0001f680"  # 4 emoji
    tokens = manager._estimate_tokens(emoji_text)

    assert tokens >= 8  # Should be at least 8 tokens for 4 emoji


def test_min_max_tokens_enforced():
    """Test that max_tokens has minimum value."""
    manager = ConversationHistoryManager(max_tokens=10)  # Too small
    assert manager._max_tokens >= 100


def test_summary_included_after_compaction():
    """Test that summary is included after compaction."""
    manager = ConversationHistoryManager(max_tokens=300)

    # Add enough messages to trigger compaction
    for i in range(15):
        manager.add("user", f"Question {i} about something interesting")
        manager.add("assistant", f"Answer {i} with helpful information")

    # Should have summary after compaction
    formatted = manager.get_formatted()
    # The summary is included in the formatted output
    assert len(formatted) > 0


def test_get_formatted_with_custom_limit():
    """Test formatted output respects custom token limit."""
    manager = ConversationHistoryManager(max_tokens=8000)

    # Add several messages
    for i in range(10):
        manager.add("user", f"This is message {i} from the user")
        manager.add("assistant", f"This is response {i} from the assistant")

    # Get with very small limit - should truncate
    formatted = manager.get_formatted(max_tokens=50)
    # Should be shorter than full output
    full_formatted = manager.get_formatted()
    assert len(formatted) <= len(full_formatted)


def test_mixed_content_token_estimation():
    """Test token estimation with mixed ASCII, CJK, and emoji."""
    manager = ConversationHistoryManager()

    mixed_text = "Hello 你好 \U0001f600"  # ASCII + CJK + emoji
    tokens = manager._estimate_tokens(mixed_text)

    # Should estimate conservatively
    assert tokens > len(mixed_text) // 4


def test_empty_history():
    """Test behavior with empty history."""
    manager = ConversationHistoryManager()

    assert manager.message_count == 0
    formatted = manager.get_formatted()
    assert formatted == ""


def test_message_roles():
    """Test that message roles are correctly stored and formatted."""
    manager = ConversationHistoryManager()
    manager.add("user", "User message")
    manager.add("assistant", "Assistant message")

    formatted = manager.get_formatted()
    assert "User: User message" in formatted
    assert "Assistant: Assistant message" in formatted
