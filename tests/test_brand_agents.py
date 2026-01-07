"""Tests for brand management agent modules.

Tests for:
- Brand Strategist: Develops core identity, audience, and positioning
- Visual Designer: Creates the visual design system
- Brand Voice Writer: Establishes voice and messaging guidelines
- Brand Guardian: Validates consistency before generation
- Brand Director: Orchestrates the team and produces final identity
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sip_studio.brands.models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIdentityFull,
    CompetitivePositioning,
    VisualIdentity,
    VoiceGuidelines,
)
from sip_studio.models.brand_agent_outputs import (
    BrandDirectorOutput,
    BrandGuardianOutput,
    BrandStrategyOutput,
    BrandValidationIssue,
    BrandVoiceOutput,
    VisualIdentityOutput,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_core_identity() -> BrandCoreIdentity:
    """Create a sample brand core identity for testing."""
    return BrandCoreIdentity(
        name="Summit Coffee Co.",
        tagline="Fuel your adventure",
        mission="To craft exceptional coffee that inspires everyday adventures.",
        brand_story="Founded by two mountaineers who discovered the perfect bean.",
        values=["Quality", "Adventure", "Sustainability"],
    )


@pytest.fixture
def sample_audience_profile() -> AudienceProfile:
    """Create a sample audience profile for testing."""
    return AudienceProfile(
        primary_summary="Active professionals aged 25-45 seeking premium coffee.",
        age_range="25-45",
        interests=["Outdoor activities", "Travel", "Fitness"],
        values=["Quality", "Experiences"],
        pain_points=["Lack of time", "Mediocre coffee options"],
        desires=["Convenient premium coffee", "Sustainable choices"],
    )


@pytest.fixture
def sample_positioning() -> CompetitivePositioning:
    """Create a sample competitive positioning for testing."""
    return CompetitivePositioning(
        market_category="Premium Coffee",
        unique_value_proposition="Adventure-inspired premium coffee for active lifestyles.",
        primary_competitors=["Starbucks", "Blue Bottle", "Counter Culture"],
        differentiation="Focus on outdoor lifestyle and sustainable sourcing.",
        positioning_statement="Summit Coffee Co. is the premium coffee for active professionals.",
    )


@pytest.fixture
def sample_visual_identity() -> VisualIdentity:
    """Create a sample visual identity for testing."""
    return VisualIdentity(
        imagery_style="Rugged outdoor photography with warm natural light.",
        imagery_keywords=["mountains", "adventure", "warmth", "natural"],
        overall_aesthetic="Rugged yet refined, blending outdoor adventure with premium quality.",
        style_keywords=["rugged", "premium", "natural"],
    )


@pytest.fixture
def sample_voice_guidelines() -> VoiceGuidelines:
    """Create a sample voice guidelines for testing."""
    return VoiceGuidelines(
        personality="Friendly, adventurous, and confident.",
        tone_attributes=["warm", "inspiring", "authentic"],
        key_messages=["Quality you can taste", "Adventure in every cup"],
        messaging_do=["Be authentic", "Inspire action"],
        messaging_dont=["Be pretentious", "Use jargon"],
    )


@pytest.fixture
def sample_brand_strategy_output(
    sample_core_identity: BrandCoreIdentity,
    sample_audience_profile: AudienceProfile,
    sample_positioning: CompetitivePositioning,
) -> BrandStrategyOutput:
    """Create a sample brand strategy output for testing."""
    return BrandStrategyOutput(
        core_identity=sample_core_identity,
        audience_profile=sample_audience_profile,
        positioning=sample_positioning,
        strategy_notes="Focus on the intersection of adventure and premium quality.",
    )


@pytest.fixture
def sample_visual_identity_output(
    sample_visual_identity: VisualIdentity,
) -> VisualIdentityOutput:
    """Create a sample visual identity output for testing."""
    return VisualIdentityOutput(
        visual_identity=sample_visual_identity,
        design_rationale="Colors inspired by mountain sunrises and forest trails.",
        logo_brief="A minimalist mountain peak with coffee steam rising.",
    )


@pytest.fixture
def sample_brand_voice_output(
    sample_voice_guidelines: VoiceGuidelines,
) -> BrandVoiceOutput:
    """Create a sample brand voice output for testing."""
    return BrandVoiceOutput(
        voice_guidelines=sample_voice_guidelines,
        sample_copy=["Rise and grind.", "Adventure starts with a cup."],
        voice_rationale="Voice reflects the active, adventurous spirit of the target audience.",
    )


@pytest.fixture
def sample_brand_guardian_output() -> BrandGuardianOutput:
    """Create a sample brand guardian output for testing."""
    return BrandGuardianOutput(
        is_valid=True,
        issues=[],
        consistency_score=0.95,
        validation_notes="Brand identity is cohesive and well-aligned.",
    )


@pytest.fixture
def sample_brand_guardian_output_with_issues() -> BrandGuardianOutput:
    """Create a sample brand guardian output with issues for testing."""
    return BrandGuardianOutput(
        is_valid=False,
        issues=[
            BrandValidationIssue(
                category="visual",
                severity="warning",
                description="Color palette could better reflect adventure theme.",
                recommendation="Consider adding earth tones to the palette.",
            ),
            BrandValidationIssue(
                category="voice",
                severity="suggestion",
                description="Sample copy is good but could be more distinctive.",
                recommendation="Add more adventure-specific vocabulary.",
            ),
        ],
        consistency_score=0.78,
        validation_notes="Minor inconsistencies found in visual-voice alignment.",
    )


@pytest.fixture
def sample_brand_identity_full(
    sample_core_identity: BrandCoreIdentity,
    sample_visual_identity: VisualIdentity,
    sample_voice_guidelines: VoiceGuidelines,
    sample_audience_profile: AudienceProfile,
    sample_positioning: CompetitivePositioning,
) -> BrandIdentityFull:
    """Create a sample full brand identity for testing."""
    return BrandIdentityFull(
        slug="summit-coffee-co",
        core=sample_core_identity,
        visual=sample_visual_identity,
        voice=sample_voice_guidelines,
        audience=sample_audience_profile,
        positioning=sample_positioning,
    )


@pytest.fixture
def sample_brand_director_output(
    sample_brand_identity_full: BrandIdentityFull,
) -> BrandDirectorOutput:
    """Create a sample brand director output for testing."""
    return BrandDirectorOutput(
        brand_identity=sample_brand_identity_full,
        creative_rationale="Brand built around adventure lifestyle and premium quality.",
        validation_passed=True,
        next_steps=["Generate logo", "Create brand assets", "Launch marketing campaign"],
    )


# ============================================================================
# Output Model Tests
# ============================================================================


class TestBrandStrategyOutput:
    """Tests for BrandStrategyOutput model."""

    def test_instantiation_with_all_fields(
        self, sample_brand_strategy_output: BrandStrategyOutput
    ) -> None:
        """Test that BrandStrategyOutput can be instantiated with all fields."""
        assert sample_brand_strategy_output.core_identity.name == "Summit Coffee Co."
        assert sample_brand_strategy_output.audience_profile.age_range == "25-45"
        assert sample_brand_strategy_output.positioning.market_category == "Premium Coffee"
        assert "adventure" in sample_brand_strategy_output.strategy_notes.lower()

    def test_serialization_to_json(self, sample_brand_strategy_output: BrandStrategyOutput) -> None:
        """Test that BrandStrategyOutput can be serialized to JSON."""
        json_str = sample_brand_strategy_output.model_dump_json()
        data = json.loads(json_str)
        assert "core_identity" in data
        assert "audience_profile" in data
        assert "positioning" in data


class TestVisualIdentityOutput:
    """Tests for VisualIdentityOutput model."""

    def test_instantiation_with_all_fields(
        self, sample_visual_identity_output: VisualIdentityOutput
    ) -> None:
        """Test that VisualIdentityOutput can be instantiated with all fields."""
        assert "outdoor" in sample_visual_identity_output.visual_identity.imagery_style.lower()
        assert sample_visual_identity_output.design_rationale != ""
        assert "mountain" in sample_visual_identity_output.logo_brief.lower()

    def test_serialization_to_json(
        self, sample_visual_identity_output: VisualIdentityOutput
    ) -> None:
        """Test that VisualIdentityOutput can be serialized to JSON."""
        json_str = sample_visual_identity_output.model_dump_json()
        data = json.loads(json_str)
        assert "visual_identity" in data
        assert "design_rationale" in data


class TestBrandVoiceOutput:
    """Tests for BrandVoiceOutput model."""

    def test_instantiation_with_all_fields(
        self, sample_brand_voice_output: BrandVoiceOutput
    ) -> None:
        """Test that BrandVoiceOutput can be instantiated with all fields."""
        assert "adventurous" in sample_brand_voice_output.voice_guidelines.personality.lower()
        assert len(sample_brand_voice_output.sample_copy) == 2
        assert sample_brand_voice_output.voice_rationale != ""

    def test_serialization_to_json(self, sample_brand_voice_output: BrandVoiceOutput) -> None:
        """Test that BrandVoiceOutput can be serialized to JSON."""
        json_str = sample_brand_voice_output.model_dump_json()
        data = json.loads(json_str)
        assert "voice_guidelines" in data
        assert "sample_copy" in data


class TestBrandGuardianOutput:
    """Tests for BrandGuardianOutput model."""

    def test_valid_output(self, sample_brand_guardian_output: BrandGuardianOutput) -> None:
        """Test valid brand guardian output."""
        assert sample_brand_guardian_output.is_valid is True
        assert len(sample_brand_guardian_output.issues) == 0
        assert sample_brand_guardian_output.consistency_score == 0.95

    def test_output_with_issues(
        self, sample_brand_guardian_output_with_issues: BrandGuardianOutput
    ) -> None:
        """Test brand guardian output with issues."""
        assert sample_brand_guardian_output_with_issues.is_valid is False
        assert len(sample_brand_guardian_output_with_issues.issues) == 2
        assert sample_brand_guardian_output_with_issues.consistency_score == 0.78

    def test_issue_categories(
        self, sample_brand_guardian_output_with_issues: BrandGuardianOutput
    ) -> None:
        """Test that issues have proper categories."""
        categories = [issue.category for issue in sample_brand_guardian_output_with_issues.issues]
        assert "visual" in categories
        assert "voice" in categories

    def test_serialization_to_json(self, sample_brand_guardian_output: BrandGuardianOutput) -> None:
        """Test that BrandGuardianOutput can be serialized to JSON."""
        json_str = sample_brand_guardian_output.model_dump_json()
        data = json.loads(json_str)
        assert "is_valid" in data
        assert "issues" in data
        assert "consistency_score" in data


class TestBrandDirectorOutput:
    """Tests for BrandDirectorOutput model."""

    def test_instantiation_with_all_fields(
        self, sample_brand_director_output: BrandDirectorOutput
    ) -> None:
        """Test that BrandDirectorOutput can be instantiated with all fields."""
        assert sample_brand_director_output.brand_identity.slug == "summit-coffee-co"
        assert sample_brand_director_output.validation_passed is True
        assert len(sample_brand_director_output.next_steps) == 3

    def test_serialization_to_json(self, sample_brand_director_output: BrandDirectorOutput) -> None:
        """Test that BrandDirectorOutput can be serialized to JSON."""
        json_str = sample_brand_director_output.model_dump_json()
        data = json.loads(json_str)
        assert "brand_identity" in data
        assert "creative_rationale" in data
        assert "next_steps" in data


# ============================================================================
# Brand Strategist Agent Tests
# ============================================================================


class TestBrandStrategistAgent:
    """Tests for the Brand Strategist agent."""

    @pytest.mark.asyncio
    async def test_develop_brand_strategy_success(
        self, sample_brand_strategy_output: BrandStrategyOutput
    ) -> None:
        """Test successful brand strategy development."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_strategy_output

        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_studio.agents.brand_strategist import develop_brand_strategy

            result = await develop_brand_strategy(
                concept="A premium coffee brand for outdoor enthusiasts",
            )

            assert isinstance(result, BrandStrategyOutput)
            assert result.core_identity.name == "Summit Coffee Co."

    @pytest.mark.asyncio
    async def test_develop_brand_strategy_with_existing_brand(
        self, sample_brand_strategy_output: BrandStrategyOutput
    ) -> None:
        """Test brand strategy development with existing brand context."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_strategy_output
        with (
            patch("agents.Runner.run", new_callable=AsyncMock, return_value=mock_result),
            patch(
                "sip_studio.brands.context.build_brand_context",
                return_value="## Brand Context\nExisting brand info...",
            ),
            patch("sip_studio.brands.storage.set_active_brand") as mock_set_active,
        ):
            from sip_studio.agents.brand_strategist import develop_brand_strategy

            result = await develop_brand_strategy(
                concept="Evolve the brand to target younger audience",
                existing_brand_slug="test-brand",
            )
            assert isinstance(result, BrandStrategyOutput)
            mock_set_active.assert_called_once_with("test-brand")


# ============================================================================
# Visual Designer Agent Tests
# ============================================================================


class TestVisualDesignerAgent:
    """Tests for the Visual Designer agent."""

    @pytest.mark.asyncio
    async def test_develop_visual_identity_success(
        self, sample_visual_identity_output: VisualIdentityOutput
    ) -> None:
        """Test successful visual identity development."""
        mock_result = MagicMock()
        mock_result.final_output = sample_visual_identity_output

        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_studio.agents.visual_designer import develop_visual_identity

            result = await develop_visual_identity(
                brand_strategy="Summit Coffee Co. targets active professionals...",
            )

            assert isinstance(result, VisualIdentityOutput)
            assert result.visual_identity is not None

    @pytest.mark.asyncio
    async def test_develop_visual_identity_with_existing_brand(
        self, sample_visual_identity_output: VisualIdentityOutput
    ) -> None:
        """Test visual identity development with existing brand context."""
        mock_result = MagicMock()
        mock_result.final_output = sample_visual_identity_output
        with (
            patch("agents.Runner.run", new_callable=AsyncMock, return_value=mock_result),
            patch(
                "sip_studio.brands.context.build_brand_context",
                return_value="## Brand Context\nExisting brand info...",
            ),
            patch("sip_studio.brands.storage.set_active_brand") as mock_set_active,
        ):
            from sip_studio.agents.visual_designer import develop_visual_identity

            result = await develop_visual_identity(
                brand_strategy="Update visual identity for summer campaign",
                existing_brand_slug="test-brand",
            )
            assert isinstance(result, VisualIdentityOutput)
            mock_set_active.assert_called_once_with("test-brand")


# ============================================================================
# Brand Voice Agent Tests
# ============================================================================


class TestBrandVoiceAgent:
    """Tests for the Brand Voice Writer agent."""

    @pytest.mark.asyncio
    async def test_develop_brand_voice_success(
        self, sample_brand_voice_output: BrandVoiceOutput
    ) -> None:
        """Test successful brand voice development."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_voice_output

        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_studio.agents.brand_voice import develop_brand_voice

            result = await develop_brand_voice(
                brand_strategy="Summit Coffee Co. is an adventure-inspired brand...",
            )

            assert isinstance(result, BrandVoiceOutput)
            assert len(result.sample_copy) == 2

    @pytest.mark.asyncio
    async def test_develop_brand_voice_with_existing_brand(
        self, sample_brand_voice_output: BrandVoiceOutput
    ) -> None:
        """Test brand voice development with existing brand context."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_voice_output
        with (
            patch("agents.Runner.run", new_callable=AsyncMock, return_value=mock_result),
            patch(
                "sip_studio.brands.context.build_brand_context",
                return_value="## Brand Context\nExisting brand info...",
            ),
            patch("sip_studio.brands.storage.set_active_brand") as mock_set_active,
        ):
            from sip_studio.agents.brand_voice import develop_brand_voice

            result = await develop_brand_voice(
                brand_strategy="Refine voice for social media campaigns",
                existing_brand_slug="test-brand",
            )
            assert isinstance(result, BrandVoiceOutput)
            mock_set_active.assert_called_once_with("test-brand")


# ============================================================================
# Brand Guardian Agent Tests
# ============================================================================


class TestBrandGuardianAgent:
    """Tests for the Brand Guardian agent."""

    @pytest.mark.asyncio
    async def test_validate_brand_identity_success(
        self, sample_brand_guardian_output: BrandGuardianOutput
    ) -> None:
        """Test successful brand identity validation."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_guardian_output

        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_studio.agents.brand_guardian import validate_brand_identity

            result = await validate_brand_identity(
                brand_identity_json='{"slug": "test-brand", "core": {...}}',
            )

            assert isinstance(result, BrandGuardianOutput)
            assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validate_brand_identity_with_issues(
        self, sample_brand_guardian_output_with_issues: BrandGuardianOutput
    ) -> None:
        """Test brand identity validation finding issues."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_guardian_output_with_issues

        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_studio.agents.brand_guardian import validate_brand_identity

            result = await validate_brand_identity(
                brand_identity_json='{"slug": "test-brand"}',
            )

            assert isinstance(result, BrandGuardianOutput)
            assert result.is_valid is False
            assert len(result.issues) == 2

    @pytest.mark.asyncio
    async def test_validate_brand_work_success(
        self, sample_brand_guardian_output: BrandGuardianOutput
    ) -> None:
        """Test successful validation of specialist work."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_guardian_output

        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_studio.agents.brand_guardian import validate_brand_work

            result = await validate_brand_work(
                strategy_output='{"core_identity": {...}}',
                visual_output='{"visual_identity": {...}}',
                voice_output='{"voice_guidelines": {...}}',
            )

            assert isinstance(result, BrandGuardianOutput)
            assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validate_brand_work_no_inputs(self) -> None:
        """Test validation with no specialist work returns error."""
        from sip_studio.agents.brand_guardian import validate_brand_work

        result = await validate_brand_work()

        assert isinstance(result, BrandGuardianOutput)
        assert result.is_valid is False
        assert len(result.issues) == 1
        assert "No specialist work provided" in result.issues[0].description


# ============================================================================
# Brand Director Agent Tests
# ============================================================================


class TestBrandDirectorAgent:
    """Tests for the Brand Director orchestrator agent."""

    @pytest.mark.asyncio
    async def test_develop_brand_success(
        self, sample_brand_director_output: BrandDirectorOutput
    ) -> None:
        """Test successful brand development."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_director_output

        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_studio.agents.brand_director import develop_brand

            result = await develop_brand(
                concept="A premium coffee brand for outdoor enthusiasts",
            )

            assert isinstance(result, BrandIdentityFull)
            assert result.slug == "summit-coffee-co"

    @pytest.mark.asyncio
    async def test_develop_brand_with_output(
        self, sample_brand_director_output: BrandDirectorOutput
    ) -> None:
        """Test brand development returning full output."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_director_output

        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_studio.agents.brand_director import develop_brand_with_output

            result = await develop_brand_with_output(
                concept="A premium coffee brand for outdoor enthusiasts",
            )

            assert isinstance(result, BrandDirectorOutput)
            assert result.brand_identity.slug == "summit-coffee-co"
            assert result.validation_passed is True

    @pytest.mark.asyncio
    async def test_develop_brand_empty_concept_raises_error(self) -> None:
        """Test that empty concept raises ValueError."""
        from sip_studio.agents.brand_director import develop_brand

        with pytest.raises(ValueError) as exc_info:
            await develop_brand(concept="")

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_develop_brand_whitespace_concept_raises_error(self) -> None:
        """Test that whitespace-only concept raises ValueError."""
        from sip_studio.agents.brand_director import develop_brand

        with pytest.raises(ValueError) as exc_info:
            await develop_brand(concept="   ")

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_develop_brand_too_long_concept_raises_error(self) -> None:
        """Test that too long concept raises ValueError."""
        from sip_studio.agents.brand_director import develop_brand

        long_concept = "A" * 5001
        with pytest.raises(ValueError) as exc_info:
            await develop_brand(concept=long_concept)

        assert "long" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_develop_brand_with_progress_callback(
        self, sample_brand_director_output: BrandDirectorOutput
    ) -> None:
        """Test brand development with progress callback."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_director_output

        progress_events = []

        def progress_callback(progress):
            progress_events.append(progress)

        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_studio.agents.brand_director import develop_brand

            result = await develop_brand(
                concept="A premium coffee brand",
                progress_callback=progress_callback,
            )

            assert isinstance(result, BrandIdentityFull)
            # Note: Progress events would be recorded during actual agent execution
            # The mock bypasses the hooks, so we just verify the callback was passed

    @pytest.mark.asyncio
    async def test_develop_brand_with_existing_brand(
        self, sample_brand_director_output: BrandDirectorOutput
    ) -> None:
        """Test brand development with existing brand context."""
        mock_result = MagicMock()
        mock_result.final_output = sample_brand_director_output
        with (
            patch("agents.Runner.run", new_callable=AsyncMock, return_value=mock_result),
            patch(
                "sip_studio.brands.context.build_brand_context",
                return_value="## Brand Context\nExisting brand info...",
            ),
            patch("sip_studio.brands.storage.set_active_brand") as mock_set_active,
        ):
            from sip_studio.agents.brand_director import develop_brand

            result = await develop_brand(
                concept="Evolve the brand for younger audience", existing_brand_slug="test-brand"
            )
            assert isinstance(result, BrandIdentityFull)
            mock_set_active.assert_called_once_with("test-brand")


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestBrandDevelopmentError:
    """Tests for BrandDevelopmentError exception."""

    def test_error_message(self) -> None:
        """Test error message is preserved."""
        from sip_studio.agents.brand_director import BrandDevelopmentError

        error = BrandDevelopmentError("Test error message")
        assert str(error) == "Test error message"

    def test_error_inherits_from_exception(self) -> None:
        """Test error inherits from Exception."""
        from sip_studio.agents.brand_director import BrandDevelopmentError

        assert issubclass(BrandDevelopmentError, Exception)


class TestBrandAgentProgress:
    """Tests for BrandAgentProgress dataclass."""

    def test_progress_creation(self) -> None:
        """Test progress dataclass creation."""
        from sip_studio.agents.brand_director import BrandAgentProgress

        progress = BrandAgentProgress(
            event_type="agent_start",
            agent_name="Brand Strategist",
            message="Starting brand strategy development",
        )

        assert progress.event_type == "agent_start"
        assert progress.agent_name == "Brand Strategist"
        assert progress.message == "Starting brand strategy development"
        assert progress.detail == ""  # Default value

    def test_progress_with_detail(self) -> None:
        """Test progress dataclass with detail."""
        from sip_studio.agents.brand_director import BrandAgentProgress

        progress = BrandAgentProgress(
            event_type="tool_end",
            agent_name="Brand Director",
            message="Tool completed",
            detail="Result preview...",
        )

        assert progress.detail == "Result preview..."


# ============================================================================
# Progress Tracking Hooks Tests
# ============================================================================


class TestBrandProgressTrackingHooks:
    """Tests for BrandProgressTrackingHooks."""

    def test_hooks_creation_without_callback(self) -> None:
        """Test hooks creation without callback."""
        from sip_studio.agents.brand_director import BrandProgressTrackingHooks

        hooks = BrandProgressTrackingHooks()
        assert hooks.callback is None

    def test_hooks_creation_with_callback(self) -> None:
        """Test hooks creation with callback."""
        from sip_studio.agents.brand_director import BrandProgressTrackingHooks

        callback = MagicMock()
        hooks = BrandProgressTrackingHooks(callback=callback)
        assert hooks.callback is callback

    @pytest.mark.asyncio
    async def test_on_agent_start(self) -> None:
        """Test on_agent_start hook."""
        from sip_studio.agents.brand_director import BrandProgressTrackingHooks

        callback = MagicMock()
        hooks = BrandProgressTrackingHooks(callback=callback)

        mock_context = MagicMock()
        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"

        await hooks.on_agent_start(mock_context, mock_agent)

        callback.assert_called_once()
        progress = callback.call_args[0][0]
        assert progress.event_type == "agent_start"
        assert progress.agent_name == "Test Agent"

    @pytest.mark.asyncio
    async def test_on_agent_end(self) -> None:
        """Test on_agent_end hook."""
        from sip_studio.agents.brand_director import BrandProgressTrackingHooks

        callback = MagicMock()
        hooks = BrandProgressTrackingHooks(callback=callback)

        mock_context = MagicMock()
        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"

        await hooks.on_agent_end(mock_context, mock_agent, {"result": "test"})

        callback.assert_called_once()
        progress = callback.call_args[0][0]
        assert progress.event_type == "agent_end"

    @pytest.mark.asyncio
    async def test_on_tool_start(self) -> None:
        """Test on_tool_start hook."""
        from sip_studio.agents.brand_director import BrandProgressTrackingHooks

        callback = MagicMock()
        hooks = BrandProgressTrackingHooks(callback=callback)

        mock_context = MagicMock()
        mock_agent = MagicMock()
        mock_agent.name = "Brand Director"
        mock_tool = MagicMock()
        mock_tool.name = "brand_strategist"

        await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        callback.assert_called_once()
        progress = callback.call_args[0][0]
        assert progress.event_type == "tool_start"
        assert "Brand Strategist" in progress.message

    @pytest.mark.asyncio
    async def test_on_llm_start(self) -> None:
        """Test on_llm_start hook."""
        from sip_studio.agents.brand_director import BrandProgressTrackingHooks

        callback = MagicMock()
        hooks = BrandProgressTrackingHooks(callback=callback)

        mock_context = MagicMock()
        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"

        await hooks.on_llm_start(mock_context, mock_agent)

        callback.assert_called_once()
        progress = callback.call_args[0][0]
        assert progress.event_type == "thinking"


# ============================================================================
# Prompt File Tests
# ============================================================================


class TestBrandAgentPrompts:
    """Tests for brand agent prompt files."""

    def test_brand_strategist_prompt_exists(self) -> None:
        """Test brand strategist prompt file exists."""
        prompt_path = (
            Path(__file__).parent.parent / "src/sip_studio/agents/prompts/brand_strategist.md"
        )
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

    def test_visual_designer_prompt_exists(self) -> None:
        """Test visual designer prompt file exists."""
        prompt_path = (
            Path(__file__).parent.parent / "src/sip_studio/agents/prompts/visual_designer.md"
        )
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

    def test_brand_voice_prompt_exists(self) -> None:
        """Test brand voice prompt file exists."""
        prompt_path = Path(__file__).parent.parent / "src/sip_studio/agents/prompts/brand_voice.md"
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

    def test_brand_guardian_prompt_exists(self) -> None:
        """Test brand guardian prompt file exists."""
        prompt_path = (
            Path(__file__).parent.parent / "src/sip_studio/agents/prompts/brand_guardian.md"
        )
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

    def test_brand_director_prompt_exists(self) -> None:
        """Test brand director prompt file exists."""
        prompt_path = (
            Path(__file__).parent.parent / "src/sip_studio/agents/prompts/brand_director.md"
        )
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"


# ============================================================================
# Agent Definition Tests
# ============================================================================


class TestAgentDefinitions:
    """Tests for agent definitions (agents have correct configuration)."""

    def test_brand_strategist_agent_has_output_type(self) -> None:
        """Test brand strategist agent has correct output type."""
        from sip_studio.agents.brand_strategist import brand_strategist_agent

        assert brand_strategist_agent.output_type == BrandStrategyOutput

    def test_visual_designer_agent_has_output_type(self) -> None:
        """Test visual designer agent has correct output type."""
        from sip_studio.agents.visual_designer import visual_designer_agent

        assert visual_designer_agent.output_type == VisualIdentityOutput

    def test_brand_voice_agent_has_output_type(self) -> None:
        """Test brand voice agent has correct output type."""
        from sip_studio.agents.brand_voice import brand_voice_agent

        assert brand_voice_agent.output_type == BrandVoiceOutput

    def test_brand_guardian_agent_has_output_type(self) -> None:
        """Test brand guardian agent has correct output type."""
        from sip_studio.agents.brand_guardian import brand_guardian_agent

        assert brand_guardian_agent.output_type == BrandGuardianOutput

    def test_brand_director_agent_has_output_type(self) -> None:
        """Test brand director agent has correct output type."""
        from sip_studio.agents.brand_director import brand_director_agent

        assert brand_director_agent.output_type == BrandDirectorOutput

    def test_brand_strategist_agent_has_tools(self) -> None:
        """Test brand strategist agent has memory tools."""
        from sip_studio.agents.brand_strategist import brand_strategist_agent

        # Tools can be functions (use __name__) or FunctionTool objects (use .name)
        tool_names = [
            getattr(t, "name", getattr(t, "__name__", None)) for t in brand_strategist_agent.tools
        ]
        assert "fetch_brand_detail" in tool_names
        assert "browse_brand_assets" in tool_names

    def test_brand_director_agent_has_specialist_tools(self) -> None:
        """Test brand director agent has specialist agents as tools."""
        from sip_studio.agents.brand_director import brand_director_agent

        # Tools can be functions (use __name__) or FunctionTool objects (use .name)
        tool_names = [
            getattr(t, "name", getattr(t, "__name__", None)) for t in brand_director_agent.tools
        ]
        assert "brand_strategist" in tool_names
        assert "visual_designer" in tool_names
        assert "brand_voice" in tool_names
        assert "brand_guardian" in tool_names
        assert "fetch_brand_detail" in tool_names
        assert "browse_brand_assets" in tool_names
