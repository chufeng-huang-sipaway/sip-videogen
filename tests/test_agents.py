"""Tests for agent modules in sip-videogen."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sip_videogen.models.agent_outputs import (
    ScreenwriterOutput,
    ProductionDesignerOutput,
    ContinuitySupervisorOutput,
    ShowrunnerOutput,
)
from sip_videogen.models.script import (
    ElementType,
    SceneAction,
    SharedElement,
    VideoScript,
)


class TestScreenwriterAgent:
    """Tests for the Screenwriter agent."""

    @pytest.mark.asyncio
    async def test_develop_scenes_success(
        self, sample_scene_action: SceneAction
    ) -> None:
        """Test successful scene development."""
        mock_output = ScreenwriterOutput(
            scenes=[sample_scene_action],
            narrative_notes="Test narrative",
        )

        mock_result = MagicMock()
        mock_result.final_output = mock_output

        # Patch at the agents module level since Runner is imported inside the function
        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_videogen.agents.screenwriter import develop_scenes

            result = await develop_scenes(
                idea="A cat astronaut explores Mars",
                num_scenes=3,
            )

            assert isinstance(result, ScreenwriterOutput)
            assert len(result.scenes) == 1


class TestProductionDesignerAgent:
    """Tests for the Production Designer agent."""

    @pytest.mark.asyncio
    async def test_identify_shared_elements_success(
        self,
        sample_scene_action: SceneAction,
        sample_shared_element: SharedElement,
    ) -> None:
        """Test successful shared element identification."""
        mock_output = ProductionDesignerOutput(
            shared_elements=[sample_shared_element],
            design_notes="Test design notes",
        )

        mock_result = MagicMock()
        mock_result.final_output = mock_output

        # Patch at the agents module level since Runner is imported inside the function
        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_videogen.agents.production_designer import (
                identify_shared_elements,
            )

            result = await identify_shared_elements(scenes=[sample_scene_action])

            assert isinstance(result, ProductionDesignerOutput)
            assert len(result.shared_elements) == 1
            assert result.shared_elements[0].element_type == ElementType.CHARACTER


class TestContinuitySupervisorAgent:
    """Tests for the Continuity Supervisor agent."""

    @pytest.mark.asyncio
    async def test_validate_and_optimize_success(
        self,
        sample_video_script: VideoScript,
    ) -> None:
        """Test successful script validation and optimization."""
        mock_output = ContinuitySupervisorOutput(
            validated_script=sample_video_script,
            issues_found=[],
            optimization_notes="Prompts optimized for VEO generation",
        )

        mock_result = MagicMock()
        mock_result.final_output = mock_output

        # Patch at the agents module level since Runner is imported inside the function
        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_videogen.agents.continuity_supervisor import validate_and_optimize

            result = await validate_and_optimize(
                scenes=sample_video_script.scenes,
                shared_elements=sample_video_script.shared_elements,
                title=sample_video_script.title,
                logline=sample_video_script.logline,
                tone=sample_video_script.tone,
            )

            assert isinstance(result, ContinuitySupervisorOutput)
            assert result.validated_script == sample_video_script
            assert len(result.issues_found) == 0


class TestShowrunnerAgent:
    """Tests for the Showrunner orchestrator agent."""

    @pytest.mark.asyncio
    async def test_develop_script_success(
        self, sample_video_script: VideoScript
    ) -> None:
        """Test successful script development."""
        mock_output = ShowrunnerOutput(
            script=sample_video_script,
            creative_brief="An inspiring space adventure",
            production_ready=True,
        )

        mock_result = MagicMock()
        mock_result.final_output = mock_output

        # Patch at the agents module level since Runner is imported at module level
        with patch(
            "agents.Runner.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            from sip_videogen.agents.showrunner import develop_script

            result = await develop_script(
                idea="A cat astronaut explores Mars",
                num_scenes=3,
            )

            assert isinstance(result, VideoScript)
            assert result.title == sample_video_script.title

    @pytest.mark.asyncio
    async def test_develop_script_empty_idea_raises_error(self) -> None:
        """Test that empty idea raises ValueError."""
        from sip_videogen.agents.showrunner import develop_script

        with pytest.raises(ValueError) as exc_info:
            await develop_script(idea="", num_scenes=3)

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_develop_script_whitespace_idea_raises_error(self) -> None:
        """Test that whitespace-only idea raises ValueError."""
        from sip_videogen.agents.showrunner import develop_script

        with pytest.raises(ValueError) as exc_info:
            await develop_script(idea="   ", num_scenes=3)

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_develop_script_too_long_idea_raises_error(self) -> None:
        """Test that too long idea raises ValueError."""
        from sip_videogen.agents.showrunner import develop_script

        long_idea = "A" * 2001
        with pytest.raises(ValueError) as exc_info:
            await develop_script(idea=long_idea, num_scenes=3)

        assert "long" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_develop_script_invalid_num_scenes_raises_error(self) -> None:
        """Test that invalid num_scenes raises ValueError."""
        from sip_videogen.agents.showrunner import develop_script

        with pytest.raises(ValueError):
            await develop_script(idea="A cat astronaut", num_scenes=0)

        with pytest.raises(ValueError):
            await develop_script(idea="A cat astronaut", num_scenes=11)


class TestAgentPrompts:
    """Tests for agent prompt files."""

    def test_screenwriter_prompt_exists(self) -> None:
        """Test screenwriter prompt file exists."""
        from pathlib import Path

        prompt_path = Path(__file__).parent.parent / "src/sip_videogen/agents/prompts/screenwriter.md"
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

    def test_production_designer_prompt_exists(self) -> None:
        """Test production designer prompt file exists."""
        from pathlib import Path

        prompt_path = Path(__file__).parent.parent / "src/sip_videogen/agents/prompts/production_designer.md"
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

    def test_continuity_supervisor_prompt_exists(self) -> None:
        """Test continuity supervisor prompt file exists."""
        from pathlib import Path

        prompt_path = Path(__file__).parent.parent / "src/sip_videogen/agents/prompts/continuity_supervisor.md"
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

    def test_showrunner_prompt_exists(self) -> None:
        """Test showrunner prompt file exists."""
        from pathlib import Path

        prompt_path = Path(__file__).parent.parent / "src/sip_videogen/agents/prompts/showrunner.md"
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"


class TestScriptDevelopmentError:
    """Tests for ScriptDevelopmentError exception."""

    def test_error_message(self) -> None:
        """Test error message is preserved."""
        from sip_videogen.agents.showrunner import ScriptDevelopmentError

        error = ScriptDevelopmentError("Test error message")
        assert str(error) == "Test error message"

    def test_error_inherits_from_exception(self) -> None:
        """Test error inherits from Exception."""
        from sip_videogen.agents.showrunner import ScriptDevelopmentError

        assert issubclass(ScriptDevelopmentError, Exception)
