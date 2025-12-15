"""Tests for context budget management module."""

from sip_videogen.advisor.context_budget import (
    BudgetCheckResult,
    ContextBudget,
    ContextBudgetManager,
)


class TestContextBudget:
    """Tests for ContextBudget dataclass."""

    def test_default_values(self) -> None:
        """Test default budget values for GPT-5.1."""
        budget = ContextBudget()
        assert budget.total_limit == 272000
        assert budget.reserved_for_response == 16000
        assert budget.reserved_for_tools == 8000

    def test_available_for_content(self) -> None:
        """Test available_for_content calculation."""
        budget = ContextBudget()
        expected = 272000 - 16000 - 8000  # 248000
        assert budget.available_for_content == expected

    def test_custom_budget(self) -> None:
        """Test custom budget values."""
        budget = ContextBudget(
            total_limit=100000,
            reserved_for_response=10000,
            reserved_for_tools=5000,
        )
        assert budget.available_for_content == 85000


class TestContextBudgetManager:
    """Tests for ContextBudgetManager class."""

    def test_under_budget(self) -> None:
        """Test that content under budget is not trimmed."""
        manager = ContextBudgetManager()

        result, sys, skills, hist, msg = manager.check_and_trim(
            system_prompt="Short prompt",
            skills_context="Short skills",
            history="Short history",
            user_message="Hello",
        )

        assert not result.is_over_budget
        assert not result.trimmed
        assert result.warning_message is None
        assert sys == "Short prompt"
        assert skills == "Short skills"
        assert hist == "Short history"
        assert msg == "Hello"

    def test_over_budget_trims_skills_first(self) -> None:
        """Test that skills context is trimmed first when over budget."""
        # Create a small budget for testing
        budget = ContextBudget(total_limit=500, reserved_for_response=50, reserved_for_tools=50)
        manager = ContextBudgetManager(budget)

        # Create content that exceeds budget - skills is large (> 2000 tokens)
        large_skills = "Skills content here " * 500  # ~10000 chars
        result, sys, skills, hist, msg = manager.check_and_trim(
            system_prompt="System " * 10,
            skills_context=large_skills,
            history="History " * 10,
            user_message="Hello",
        )

        assert result.trimmed
        assert result.warning_message is not None
        assert "trimmed skills" in result.warning_message
        assert len(skills) < len(large_skills)

    def test_over_budget_trims_history_second(self) -> None:
        """Test that history is trimmed after skills."""
        # Very small budget to force history trimming
        budget = ContextBudget(total_limit=1000, reserved_for_response=100, reserved_for_tools=100)
        manager = ContextBudgetManager(budget)

        # Small skills, large history
        result, sys, skills, hist, msg = manager.check_and_trim(
            system_prompt="System " * 20,
            skills_context="Skills",  # Small
            history="History content here " * 200,  # Large
            user_message="Hello",
        )

        assert result.trimmed
        assert result.warning_message is not None
        assert "trimmed history" in result.warning_message

    def test_over_budget_trims_system_last(self) -> None:
        """Test that system prompt is trimmed as last resort."""
        # Very small budget to force system trimming
        budget = ContextBudget(total_limit=500, reserved_for_response=50, reserved_for_tools=50)
        manager = ContextBudgetManager(budget)

        # Large system prompt
        result, sys, skills, hist, msg = manager.check_and_trim(
            system_prompt="System content here " * 200,
            skills_context="",  # Empty
            history="",  # Empty
            user_message="Hello",
        )

        assert result.trimmed
        assert result.warning_message is not None
        assert "trimmed system prompt" in result.warning_message
        assert "[... content trimmed ...]" in sys

    def test_token_estimation_basic(self) -> None:
        """Test basic token estimation."""
        manager = ContextBudgetManager()

        # Simple ASCII text - roughly 3 chars per token
        text = "Hello world"  # 11 chars -> ~4-5 tokens
        tokens = manager.estimate_tokens(text)

        # Should be reasonable estimate (3-4 chars per token + 1 safety)
        assert tokens >= 3
        assert tokens <= 10

    def test_token_estimation_cjk_conservative(self) -> None:
        """Test that CJK text is estimated conservatively."""
        manager = ContextBudgetManager()

        # 10 CJK characters should estimate higher than 10/4 = 2.5 tokens
        cjk_text = "你好世界测试文本内容"  # 10 Chinese characters
        tokens = manager.estimate_tokens(cjk_text)

        # Should be at least 10 tokens for 10 CJK chars (1.5x factor)
        assert tokens >= 10

    def test_token_estimation_emoji_conservative(self) -> None:
        """Test that emoji text is estimated conservatively."""
        manager = ContextBudgetManager()

        emoji_text = "😀😎🎉🚀"  # 4 emoji
        tokens = manager.estimate_tokens(emoji_text)

        # Should be at least 8 tokens for 4 emoji (2.5x factor)
        assert tokens >= 8

    def test_token_estimation_mixed_content(self) -> None:
        """Test token estimation with mixed content."""
        manager = ContextBudgetManager()

        # Mixed content
        text = "Hello 你好 😀"
        tokens = manager.estimate_tokens(text)

        # Should be conservative (higher estimate than naive len/4)
        assert tokens > len(text) // 4

    def test_budget_check_result_values(self) -> None:
        """Test that BudgetCheckResult contains correct values."""
        manager = ContextBudgetManager()

        result, *_ = manager.check_and_trim(
            system_prompt="Test prompt",
            skills_context="Skills",
            history="History",
            user_message="Hello",
        )

        assert isinstance(result.total_tokens, int)
        assert result.total_tokens > 0
        assert result.budget_limit == 248000  # 272000 - 16000 - 8000
        assert isinstance(result.is_over_budget, bool)
        assert isinstance(result.trimmed, bool)

    def test_empty_inputs(self) -> None:
        """Test handling of empty inputs."""
        manager = ContextBudgetManager()

        result, sys, skills, hist, msg = manager.check_and_trim(
            system_prompt="",
            skills_context="",
            history="",
            user_message="",
        )

        assert not result.is_over_budget
        assert not result.trimmed
        # Still has some tokens due to safety margin
        assert result.total_tokens >= 4  # 4 empty strings, each +1 safety

    def test_user_message_never_trimmed(self) -> None:
        """Test that user message is never trimmed."""
        budget = ContextBudget(total_limit=500, reserved_for_response=50, reserved_for_tools=50)
        manager = ContextBudgetManager(budget)

        original_message = "This is the user message that should never be trimmed"

        result, sys, skills, hist, msg = manager.check_and_trim(
            system_prompt="System " * 100,
            skills_context="Skills " * 100,
            history="History " * 100,
            user_message=original_message,
        )

        # User message should be unchanged
        assert msg == original_message


class TestBudgetCheckResult:
    """Tests for BudgetCheckResult dataclass."""

    def test_result_creation(self) -> None:
        """Test creating a BudgetCheckResult."""
        result = BudgetCheckResult(
            total_tokens=1000,
            budget_limit=2000,
            is_over_budget=False,
            trimmed=False,
            warning_message=None,
        )

        assert result.total_tokens == 1000
        assert result.budget_limit == 2000
        assert not result.is_over_budget
        assert not result.trimmed
        assert result.warning_message is None

    def test_result_with_warning(self) -> None:
        """Test BudgetCheckResult with warning message."""
        result = BudgetCheckResult(
            total_tokens=3000,
            budget_limit=2000,
            is_over_budget=True,
            trimmed=True,
            warning_message="Context budget exceeded: trimmed skills",
        )

        assert result.is_over_budget
        assert result.trimmed
        assert "trimmed skills" in result.warning_message
