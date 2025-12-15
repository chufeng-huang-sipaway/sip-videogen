"""Context budget management for the advisor agent.

Monitors total token usage across system prompt, skills, history, and user message.
Automatically trims content when approaching model limits.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple

from sip_videogen.config.logging import get_logger

logger = get_logger(__name__)

__all__ = ["ContextBudget", "ContextBudgetManager", "BudgetCheckResult"]


@dataclass
class ContextBudget:
    """Token budget configuration for GPT-5.1 (272K context)."""

    total_limit: int = 272000  # GPT-5.1 context window
    reserved_for_response: int = 16000  # Space for model's response
    reserved_for_tools: int = 8000  # Space for tool definitions

    @property
    def available_for_content(self) -> int:
        """Tokens available for system prompt + skills + history + message."""
        return self.total_limit - self.reserved_for_response - self.reserved_for_tools


@dataclass
class BudgetCheckResult:
    """Result of a budget check."""

    total_tokens: int
    budget_limit: int
    is_over_budget: bool
    trimmed: bool
    warning_message: str | None


class ContextBudgetManager:
    """Manages context token budget and auto-trims when needed.

    Trim priority (lowest priority trimmed first):
    1. Skills context (can be regenerated)
    2. Conversation history (old messages summarized)
    3. System prompt (detailed sections removed)

    Usage:
        manager = ContextBudgetManager()

        result, trimmed = manager.check_and_trim(
            system_prompt="...",
            skills_context="...",
            history="...",
            user_message="..."
        )

        if result.trimmed:
            logger.warning(result.warning_message)
    """

    def __init__(self, budget: ContextBudget | None = None):
        """Initialize with optional custom budget."""
        self._budget = budget or ContextBudget()

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count with conservative heuristic."""
        # Count CJK characters
        cjk_pattern = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af]")
        cjk_count = len(cjk_pattern.findall(text))

        # Count emoji
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
            r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]"
        )
        emoji_count = len(emoji_pattern.findall(text))

        remaining_chars = len(text) - cjk_count - emoji_count
        base_tokens = remaining_chars // 3
        cjk_tokens = int(cjk_count * 1.5)
        emoji_tokens = int(emoji_count * 2.5)

        return base_tokens + cjk_tokens + emoji_tokens + 1

    def check_and_trim(
        self,
        system_prompt: str,
        skills_context: str,
        history: str,
        user_message: str,
    ) -> Tuple[BudgetCheckResult, str, str, str, str]:
        """Check budget and trim content if over limit.

        Trimming priority (lowest priority trimmed first):
        1. Skills context
        2. History
        3. System prompt

        Args:
            system_prompt: The system prompt text
            skills_context: Skills instructions to inject
            history: Formatted conversation history
            user_message: Current user message

        Returns:
            Tuple of (result, trimmed_system, trimmed_skills, trimmed_history, user_message)
        """
        # Calculate current usage
        system_tokens = self.estimate_tokens(system_prompt)
        skills_tokens = self.estimate_tokens(skills_context)
        history_tokens = self.estimate_tokens(history)
        message_tokens = self.estimate_tokens(user_message)
        total_tokens = system_tokens + skills_tokens + history_tokens + message_tokens

        limit = self._budget.available_for_content
        is_over = total_tokens > limit

        if not is_over:
            return (
                BudgetCheckResult(
                    total_tokens=total_tokens,
                    budget_limit=limit,
                    is_over_budget=False,
                    trimmed=False,
                    warning_message=None,
                ),
                system_prompt,
                skills_context,
                history,
                user_message,
            )

        # Need to trim
        trimmed_skills = skills_context
        trimmed_history = history
        trimmed_system = system_prompt
        warning_parts = []

        # Step 1: Trim skills context (lowest priority)
        if skills_tokens > 2000:
            max_skills_chars = 2000 * 3
            if len(skills_context) > max_skills_chars:
                trimmed_skills = skills_context[:max_skills_chars] + "\n[... skills truncated ...]"
                warning_parts.append(f"trimmed skills from ~{skills_tokens} to ~2000 tokens")
                skills_tokens = self.estimate_tokens(trimmed_skills)

        # Recalculate
        total_tokens = system_tokens + skills_tokens + history_tokens + message_tokens

        # Step 2: Trim history
        if total_tokens > limit and history_tokens > limit // 8:
            max_history_chars = (limit // 8) * 3
            if len(history) > max_history_chars:
                trimmed_history = "..." + history[-max_history_chars:]
                warning_parts.append(
                    f"trimmed history from ~{history_tokens} to ~{limit // 8} tokens"
                )
                history_tokens = self.estimate_tokens(trimmed_history)

        # Recalculate
        total_tokens = system_tokens + skills_tokens + history_tokens + message_tokens

        # Step 3: Trim system prompt (last resort)
        if total_tokens > limit:
            max_system_chars = (limit // 2) * 3
            if len(system_prompt) > max_system_chars:
                half = max_system_chars // 2
                trimmed_system = (
                    system_prompt[:half]
                    + "\n\n[... content trimmed ...]\n\n"
                    + system_prompt[-half:]
                )
                warning_parts.append(
                    f"trimmed system prompt from ~{system_tokens} to ~{limit // 2} tokens"
                )
                system_tokens = self.estimate_tokens(trimmed_system)

        # Final calculation
        total_tokens = system_tokens + skills_tokens + history_tokens + message_tokens
        warning_message = (
            "Context budget exceeded: " + ", ".join(warning_parts) if warning_parts else None
        )

        if warning_message:
            logger.warning(warning_message)

        return (
            BudgetCheckResult(
                total_tokens=total_tokens,
                budget_limit=limit,
                is_over_budget=total_tokens > limit,
                trimmed=len(warning_parts) > 0,
                warning_message=warning_message,
            ),
            trimmed_system,
            trimmed_skills,
            trimmed_history,
            user_message,
        )
