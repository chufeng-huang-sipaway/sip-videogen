"""Tests for the Brand Marketing Advisor agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sip_videogen.advisor.agent import AdvisorHooks, AdvisorProgress, BrandAdvisor
from sip_videogen.advisor.prompt_builder import (
    _group_assets,
)
from sip_videogen.advisor.prompt_builder import (
    build_system_prompt as _build_system_prompt,
)
from sip_videogen.advisor.prompt_builder import (
    format_brand_context as _format_brand_context,
)


class TestAdvisorProgress:
    """Tests for AdvisorProgress dataclass."""

    def test_progress_creation(self) -> None:
        """Test creating a progress update."""
        progress = AdvisorProgress(
            event_type="tool_start",
            message="Using generate_image",
            detail="Generating mascot",
        )

        assert progress.event_type == "tool_start"
        assert progress.message == "Using generate_image"
        assert progress.detail == "Generating mascot"

    def test_progress_default_detail(self) -> None:
        """Test that detail defaults to empty string."""
        progress = AdvisorProgress(
            event_type="thinking",
            message="Thinking...",
        )

        assert progress.detail == ""


class TestAdvisorHooks:
    """Tests for AdvisorHooks class."""

    def test_hooks_with_callback(self) -> None:
        """Test that hooks call the callback."""
        callback = MagicMock()
        hooks = AdvisorHooks(callback=callback)

        hooks._report(
            AdvisorProgress(
                event_type="thinking",
                message="Test message",
            )
        )

        callback.assert_called_once()
        progress = callback.call_args[0][0]
        assert progress.event_type == "thinking"
        assert progress.message == "Test message"

    def test_hooks_without_callback(self) -> None:
        """Test that hooks work without callback."""
        hooks = AdvisorHooks(callback=None)

        # Should not raise
        hooks._report(
            AdvisorProgress(
                event_type="thinking",
                message="Test message",
            )
        )


class TestSystemPromptBuilder:
    """Tests for system prompt building."""

    def test_build_system_prompt_no_brand(self) -> None:
        """Test building system prompt without a brand."""
        with patch("sip_videogen.advisor.prompt_builder.get_skills_registry") as mock_registry:
            mock_registry.return_value.format_for_prompt.return_value = (
                "## Available Skills\n- skill1"
            )

            prompt = _build_system_prompt(brand_slug=None)

        # Prompt should load from advisor.md; ensure it contains a Brand header and skills
        assert "# Brand" in prompt
        assert "## Available Skills" in prompt
        assert "skill1" in prompt

    def test_build_system_prompt_with_brand(self) -> None:
        """Test building system prompt with a brand."""
        mock_identity = MagicMock()
        mock_identity.core.name = "Test Brand"
        mock_identity.core.tagline = "Test Tagline"
        mock_identity.positioning.market_category = "Test Category"
        mock_identity.visual.primary_colors = []
        mock_identity.visual.style_keywords = []
        mock_identity.voice.tone_attributes = []
        mock_identity.audience.primary_summary = "Test audience"

        with (
            patch("sip_videogen.advisor.prompt_builder.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.prompt_builder.load_brand", return_value=mock_identity),
            patch("sip_videogen.advisor.prompt_builder.list_brand_assets", return_value=[]),
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Available Skills"

            prompt = _build_system_prompt(brand_slug="test-brand")

        # Should include brand context heading and brand name
        assert "## Current Brand Context" in prompt
        assert "Test Brand" in prompt


class TestFormatBrandContext:
    """Tests for brand context formatting."""

    def test_format_basic_context(self) -> None:
        """Test formatting basic brand context."""
        mock_identity = MagicMock()
        mock_identity.core.name = "Summit Coffee"
        mock_identity.core.tagline = "Elevate Your Morning"
        mock_identity.positioning.market_category = "Premium Coffee"
        mock_identity.visual.primary_colors = []
        mock_identity.visual.style_keywords = []
        mock_identity.voice.tone_attributes = []
        mock_identity.audience.primary_summary = "Urban professionals"

        with patch("sip_videogen.advisor.prompt_builder.list_brand_assets", return_value=[]):
            context = _format_brand_context("summit-coffee", mock_identity)

        assert "## Current Brand Context" in context
        assert "Summit Coffee" in context
        assert "Elevate Your Morning" in context
        assert "Premium Coffee" in context
        assert "Urban professionals" in context

    def test_format_context_with_colors(self) -> None:
        """Test formatting context with colors."""
        mock_identity = MagicMock()
        mock_identity.core.name = "Test Brand"
        mock_identity.core.tagline = "Test"
        mock_identity.positioning.market_category = "Test"
        mock_identity.audience.primary_summary = "Test"

        # Mock colors
        mock_color = MagicMock()
        mock_color.name = "Forest Green"
        mock_color.hex = "#228B22"
        mock_identity.visual.primary_colors = [mock_color]
        mock_identity.visual.style_keywords = ["modern", "clean"]
        mock_identity.voice.tone_attributes = ["friendly", "professional"]

        with patch("sip_videogen.advisor.prompt_builder.list_brand_assets", return_value=[]):
            context = _format_brand_context("test", mock_identity)

        assert "Forest Green (#228B22)" in context
        assert "modern, clean" in context
        assert "friendly, professional" in context


class TestGroupAssets:
    """Tests for asset grouping helper."""

    def test_group_assets(self) -> None:
        """Test grouping assets by category."""
        assets = [
            {"category": "logo", "name": "primary"},
            {"category": "logo", "name": "secondary"},
            {"category": "mascot", "name": "benny"},
        ]

        grouped = _group_assets(assets)

        assert len(grouped["logo"]) == 2
        assert len(grouped["mascot"]) == 1

    def test_group_empty_assets(self) -> None:
        """Test grouping empty assets list."""
        grouped = _group_assets([])
        assert grouped == {}

    def test_group_with_missing_category(self) -> None:
        """Test grouping assets with missing category."""
        assets = [
            {"name": "unknown"},  # No category
        ]

        grouped = _group_assets(assets)
        assert "other" in grouped
        assert len(grouped["other"]) == 1


class TestBrandAdvisor:
    """Tests for BrandAdvisor class."""

    def test_init_no_brand(self) -> None:
        """Test initializing advisor without a brand."""
        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"

            advisor = BrandAdvisor()

        assert advisor.brand_slug is None
        assert advisor._history_manager.message_count == 0

    def test_init_with_brand(self) -> None:
        """Test initializing advisor with a brand."""
        with (
            patch("sip_videogen.advisor.agent.get_active_brand") as mock_get,
            patch("sip_videogen.advisor.prompt_builder.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.prompt_builder.load_brand", return_value=None),
        ):
            mock_get.return_value = None  # Not called since we provide slug
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"

            advisor = BrandAdvisor(brand_slug="test-brand")

        assert advisor.brand_slug == "test-brand"

    def test_set_brand(self) -> None:
        """Test switching brands."""
        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.set_active_brand") as mock_set,
            patch("sip_videogen.advisor.prompt_builder.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.prompt_builder.load_brand", return_value=None),
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"

            advisor = BrandAdvisor()
            advisor.set_brand("new-brand")

        assert advisor.brand_slug == "new-brand"
        mock_set.assert_called_once_with("new-brand")

    def test_clear_history(self) -> None:
        """Test clearing conversation history."""
        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"

            advisor = BrandAdvisor()
            advisor._history_manager.add("user", "test")

            advisor.clear_history()

        assert advisor._history_manager.message_count == 0

    def test_format_history(self) -> None:
        """Test formatting conversation history."""
        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"

            advisor = BrandAdvisor()
            advisor._history_manager.add("user", "Hello")
            advisor._history_manager.add("assistant", "Hi there!")

            formatted = advisor._format_history()

        assert "User: Hello" in formatted
        assert "Assistant: Hi there!" in formatted

    @pytest.mark.asyncio
    async def test_chat_mocked(self) -> None:
        """Test chat method with mocked runner."""
        mock_result = MagicMock()
        mock_result.final_output = "I'm here to help with your brand!"

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.agent.Runner") as mock_runner,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_runner.run = AsyncMock(return_value=mock_result)

            advisor = BrandAdvisor()
            response = await advisor.chat("Create a mascot")

        assert response == "I'm here to help with your brand!"
        assert advisor._history_manager.message_count == 2
        formatted = advisor._history_manager.get_formatted()
        assert "User: Create a mascot" in formatted

    def test_agent_property(self) -> None:
        """Test accessing the underlying agent."""
        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"

            advisor = BrandAdvisor()

        assert advisor.agent is not None
        assert advisor.agent.name == "Brand Marketing Advisor"

    def test_set_brand_clears_history(self) -> None:
        """Test that switching brands clears conversation history by default."""
        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.set_active_brand"),
            patch("sip_videogen.advisor.prompt_builder.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.prompt_builder.load_brand", return_value=None),
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"

            advisor = BrandAdvisor()
            advisor._history_manager.add("user", "test message")
            advisor._history_manager.add("assistant", "test response")

            advisor.set_brand("new-brand")

        assert advisor._history_manager.message_count == 0
        assert advisor.brand_slug == "new-brand"

    def test_set_brand_preserve_history(self) -> None:
        """Test that preserve_history=True keeps conversation history."""
        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.set_active_brand"),
            patch("sip_videogen.advisor.prompt_builder.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.prompt_builder.load_brand", return_value=None),
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"

            advisor = BrandAdvisor()
            advisor._history_manager.add("user", "test message")

            advisor.set_brand("new-brand", preserve_history=True)

        assert advisor._history_manager.message_count == 1

    @pytest.mark.asyncio
    async def test_chat_injects_skill_instructions(self) -> None:
        """Test that chat() injects relevant skill instructions into prompt."""
        from sip_videogen.advisor.skills.registry import Skill

        mock_result = MagicMock()
        mock_result.final_output = "Here's your logo!"

        mock_skill = Skill(
            name="logo-design",
            description="Design logos",
            triggers=["logo"],
            instructions="# Logo Design\n\nFollow these guidelines for logos.",
        )

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.agent.Runner") as mock_runner,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = [mock_skill]
            mock_runner.run = AsyncMock(return_value=mock_result)

            advisor = BrandAdvisor()
            await advisor.chat("Create a logo for my brand")

        # Verify Runner.run was called with prompt containing skill instructions
        call_args = mock_runner.run.call_args
        prompt = call_args[0][1]  # Second positional argument is the prompt
        assert "## Relevant Skill Instructions" in prompt
        assert "logo-design" in prompt
        assert "Logo Design" in prompt

    def test_get_relevant_skills_context(self) -> None:
        """Test that _get_relevant_skills_context returns formatted skill instructions."""
        from sip_videogen.advisor.skills.registry import Skill

        mock_skill = Skill(
            name="mascot-generation",
            description="Create mascots",
            triggers=["mascot", "character"],
            instructions="# Mascot Generation\n\nCreate fun mascots.",
        )

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = [mock_skill]

            advisor = BrandAdvisor()
            context, matched_skills = advisor._get_relevant_skills_context("I want a mascot")

        assert "## Relevant Skill Instructions" in context
        assert "mascot-generation" in context
        assert "Mascot Generation" in context
        assert len(matched_skills) == 1
        assert matched_skills[0] == ("mascot-generation", "Create mascots")

    def test_get_relevant_skills_context_no_matches(self) -> None:
        """Test that _get_relevant_skills_context returns empty tuple when no skills match."""
        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = []

            advisor = BrandAdvisor()
            context, matched_skills = advisor._get_relevant_skills_context("Hello, how are you?")

        assert context == ""
        assert matched_skills == []


class TestPerTurnContextInjection:
    """Tests for per-turn context injection (Phase 3.5)."""

    @pytest.mark.asyncio
    async def test_chat_with_project_context(self) -> None:
        """Test that project context is injected when project_slug is provided."""
        mock_result = MagicMock()
        mock_result.final_output = "Using project context!"

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.agent.Runner") as mock_runner,
            patch("sip_videogen.advisor.agent.HierarchicalContextBuilder") as mock_builder_class,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = []
            mock_runner.run = AsyncMock(return_value=mock_result)

            # Setup builder mock
            mock_builder = MagicMock()
            mock_builder.build_turn_context.return_value = (
                "### Active Project: Holiday Campaign\n**Instructions**: Use festive themes"
            )
            mock_builder_class.return_value = mock_builder

            advisor = BrandAdvisor(brand_slug="test-brand")
            await advisor.chat(
                "Create a banner",
                project_slug="holiday-campaign",
            )

        # Verify builder was called with correct params
        mock_builder_class.assert_called_once_with(
            brand_slug="test-brand",
            product_slugs=None,
            project_slug="holiday-campaign",
            attached_style_references=None,
        )

        # Verify prompt contains project context
        call_args = mock_runner.run.call_args
        prompt = call_args[0][1]
        assert "## Current Context" in prompt
        assert "Active Project: Holiday Campaign" in prompt
        assert "## User Request" in prompt
        assert "Create a banner" in prompt

    @pytest.mark.asyncio
    async def test_chat_with_attached_products(self) -> None:
        """Test that product context is injected when attached_products is provided."""
        mock_result = MagicMock()
        mock_result.final_output = "Using product context!"

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.agent.Runner") as mock_runner,
            patch("sip_videogen.advisor.agent.HierarchicalContextBuilder") as mock_builder_class,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = []
            mock_runner.run = AsyncMock(return_value=mock_result)

            # Setup builder mock
            mock_builder = MagicMock()
            mock_builder.build_turn_context.return_value = (
                "### Attached Products\n\n"
                "### Product: Night Cream\n**Description**: Anti-aging formula"
            )
            mock_builder_class.return_value = mock_builder

            advisor = BrandAdvisor(brand_slug="test-brand")
            await advisor.chat(
                "Generate product image",
                attached_products=["night-cream", "day-serum"],
            )

        # Verify builder was called with correct params
        mock_builder_class.assert_called_once_with(
            brand_slug="test-brand",
            product_slugs=["night-cream", "day-serum"],
            project_slug=None,
            attached_style_references=None,
        )

        # Verify prompt contains product context
        call_args = mock_runner.run.call_args
        prompt = call_args[0][1]
        assert "## Current Context" in prompt
        assert "Attached Products" in prompt
        assert "Night Cream" in prompt

    @pytest.mark.asyncio
    async def test_chat_with_project_and_products(self) -> None:
        """Test that both project and product context are injected together."""
        mock_result = MagicMock()
        mock_result.final_output = "Using all context!"

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.agent.Runner") as mock_runner,
            patch("sip_videogen.advisor.agent.HierarchicalContextBuilder") as mock_builder_class,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = []
            mock_runner.run = AsyncMock(return_value=mock_result)

            # Setup builder mock
            mock_builder = MagicMock()
            mock_builder.build_turn_context.return_value = (
                "### Active Project: Summer Sale\n\n---\n\n"
                "### Attached Products\n\n### Product: Sunscreen"
            )
            mock_builder_class.return_value = mock_builder

            advisor = BrandAdvisor(brand_slug="test-brand")
            await advisor.chat(
                "Create campaign image",
                project_slug="summer-sale",
                attached_products=["sunscreen"],
            )

        # Verify builder was called with both
        mock_builder_class.assert_called_once_with(
            brand_slug="test-brand",
            product_slugs=["sunscreen"],
            project_slug="summer-sale",
            attached_style_references=None,
        )

    @pytest.mark.asyncio
    async def test_chat_without_project_products_still_injects_generation_mode(self) -> None:
        """Test that chat always injects generation mode even without project/products."""
        mock_result = MagicMock()
        mock_result.final_output = "No context needed!"

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.agent.Runner") as mock_runner,
            patch("sip_videogen.advisor.agent.HierarchicalContextBuilder") as mock_builder_class,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = []
            mock_runner.run = AsyncMock(return_value=mock_result)

            advisor = BrandAdvisor(brand_slug="test-brand")
            await advisor.chat("Just a simple question")

        # Builder should not be called when no project/products params
        mock_builder_class.assert_not_called()

        # Prompt should contain generation mode (always injected by chat_with_metadata)
        call_args = mock_runner.run.call_args
        prompt = call_args[0][1]
        assert "Generation Mode" in prompt
        assert "Just a simple question" in prompt

    @pytest.mark.asyncio
    async def test_skill_matching_uses_raw_message(self) -> None:
        """Test that skill matching uses the raw user message, not augmented."""
        from sip_videogen.advisor.skills.registry import Skill

        mock_result = MagicMock()
        mock_result.final_output = "Response"

        mock_skill = Skill(
            name="logo-design",
            description="Design logos",
            triggers=["logo"],
            instructions="# Logo Guidelines",
        )

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.agent.Runner") as mock_runner,
            patch("sip_videogen.advisor.agent.HierarchicalContextBuilder") as mock_builder_class,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = [mock_skill]
            mock_runner.run = AsyncMock(return_value=mock_result)

            mock_builder = MagicMock()
            mock_builder.build_turn_context.return_value = "### Project Context\nSome project info"
            mock_builder_class.return_value = mock_builder

            advisor = BrandAdvisor(brand_slug="test-brand")
            await advisor.chat(
                "Create a logo",
                project_slug="brand-refresh",
            )

        # find_relevant_skills should be called with raw message (not including context)
        mock_registry.return_value.find_relevant_skills.assert_called_once_with("Create a logo")

    @pytest.mark.asyncio
    async def test_history_stores_raw_message(self) -> None:
        """Test that conversation history stores raw user message, not augmented."""
        mock_result = MagicMock()
        mock_result.final_output = "Response to raw message"

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.agent.Runner") as mock_runner,
            patch("sip_videogen.advisor.agent.HierarchicalContextBuilder") as mock_builder_class,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = []
            mock_runner.run = AsyncMock(return_value=mock_result)

            mock_builder = MagicMock()
            mock_builder.build_turn_context.return_value = (
                "### Project: Big Campaign\nLots of context here that shouldn't be in history"
            )
            mock_builder_class.return_value = mock_builder

            advisor = BrandAdvisor(brand_slug="test-brand")
            await advisor.chat(
                "Short user message",
                project_slug="big-campaign",
            )

        # Check history contains raw message, not augmented with context
        history = advisor._history_manager.get_formatted()
        assert "User: Short user message" in history
        assert "Big Campaign" not in history  # Context should NOT be in history
        assert "Lots of context" not in history

    @pytest.mark.asyncio
    async def test_chat_with_metadata_accepts_context_params(self) -> None:
        """Test that chat_with_metadata accepts project_slug and attached_products."""
        mock_result = MagicMock()
        mock_result.final_output = "Response with metadata"

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.agent.Runner") as mock_runner,
            patch("sip_videogen.advisor.agent.HierarchicalContextBuilder") as mock_builder_class,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = []
            mock_runner.run = AsyncMock(return_value=mock_result)

            mock_builder = MagicMock()
            mock_builder.build_turn_context.return_value = "### Context"
            mock_builder_class.return_value = mock_builder

            advisor = BrandAdvisor(brand_slug="test-brand")
            result = await advisor.chat_with_metadata(
                "Test message",
                project_slug="my-project",
                attached_products=["product-a", "product-b"],
            )

        # Verify builder received both params
        mock_builder_class.assert_called_once_with(
            brand_slug="test-brand",
            product_slugs=["product-a", "product-b"],
            project_slug="my-project",
            attached_style_references=None,
        )

        # Verify response structure
        assert "response" in result
        assert result["response"] == "Response with metadata"

    @pytest.mark.asyncio
    async def test_no_brand_slug_skips_context_injection(self) -> None:
        """Test that context injection is skipped when no brand_slug is set."""
        mock_result = MagicMock()
        mock_result.final_output = "Response"

        with (
            patch("sip_videogen.advisor.agent.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.agent.get_skills_registry") as mock_registry,
            patch("sip_videogen.advisor.agent.Runner") as mock_runner,
            patch("sip_videogen.advisor.agent.HierarchicalContextBuilder") as mock_builder_class,
        ):
            mock_registry.return_value.format_for_prompt.return_value = "## Skills"
            mock_registry.return_value.find_relevant_skills.return_value = []
            mock_runner.run = AsyncMock(return_value=mock_result)

            # No brand_slug
            advisor = BrandAdvisor(brand_slug=None)
            await advisor.chat(
                "Message",
                project_slug="some-project",
                attached_products=["some-product"],
            )

        # Builder should not be called when brand_slug is None
        mock_builder_class.assert_not_called()
