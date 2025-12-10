"""Tests for the Music Director agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sip_videogen.agents.music_director import (
    _MUSIC_DIRECTOR_PROMPT_PATH,
    _load_prompt,
    analyze_script_for_music,
    music_director_agent,
)
from sip_videogen.models.music import MusicBrief, MusicGenre, MusicMood


class TestMusicDirectorAgent:
    """Tests for the music director agent configuration."""

    def test_agent_exists(self) -> None:
        """Test that the music director agent is created."""
        assert music_director_agent is not None
        assert music_director_agent.name == "MusicDirector"

    def test_agent_output_type(self) -> None:
        """Test that the agent outputs MusicBrief."""
        assert music_director_agent.output_type == MusicBrief

    def test_prompt_file_exists(self) -> None:
        """Test that the prompt file exists."""
        assert _MUSIC_DIRECTOR_PROMPT_PATH.exists()

    def test_load_prompt_from_file(self) -> None:
        """Test that the prompt is loaded from the markdown file."""
        prompt = _load_prompt()
        assert "Music Director" in prompt
        assert "MusicBrief" in prompt
        assert "prompt" in prompt.lower()
        assert "mood" in prompt.lower()

    def test_prompt_contains_key_instructions(self) -> None:
        """Test that the prompt contains key instructions."""
        prompt = _load_prompt()
        # Check for key sections
        assert "negative_prompt" in prompt
        assert "genre" in prompt
        assert "tempo" in prompt
        assert "instruments" in prompt
        assert "rationale" in prompt
        # Check for guidelines
        assert "COMPLEMENT" in prompt or "complement" in prompt
        assert "vocals" in prompt
        assert "loop" in prompt.lower()


class TestAnalyzeScriptForMusic:
    """Tests for the analyze_script_for_music function."""

    @pytest.fixture
    def sample_script_summary(self) -> str:
        """Create a sample script summary for testing."""
        return """Title: Morning Coffee Ritual
Logline: A barista crafts the perfect morning espresso.
Tone: Calm, warm, inviting

Scenes:
1. Golden morning light streams through cafe window
2. Barista grinds fresh coffee beans
3. Steam rises from the espresso machine
4. Customer smiles receiving their cup"""

    @pytest.fixture
    def mock_music_brief(self) -> MusicBrief:
        """Create a mock MusicBrief response."""
        return MusicBrief(
            prompt="Warm acoustic music with soft guitar and light percussion, "
            "calm and inviting mood, moderate tempo around 90 BPM. "
            "Suitable for cozy cafe atmosphere.",
            negative_prompt="vocals, singing, lyrics, electronic beats",
            mood=MusicMood.CALM,
            genre=MusicGenre.ACOUSTIC,
            tempo="moderate 90 BPM",
            instruments=["acoustic guitar", "soft piano", "light percussion"],
            rationale="Cafe scene benefits from warm acoustic music that enhances "
            "the cozy morning atmosphere without overwhelming the visuals.",
        )

    @pytest.mark.asyncio
    async def test_analyze_script_returns_music_brief(
        self, sample_script_summary: str, mock_music_brief: MusicBrief
    ) -> None:
        """Test that analyze_script_for_music returns a MusicBrief."""
        # Mock the Runner.run call
        mock_result = MagicMock()
        mock_result.final_output = mock_music_brief

        with patch("agents.Runner") as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)

            result = await analyze_script_for_music(sample_script_summary)

            assert isinstance(result, MusicBrief)
            assert result.mood == MusicMood.CALM
            assert result.genre == MusicGenre.ACOUSTIC

    @pytest.mark.asyncio
    async def test_analyze_script_calls_runner_with_agent(
        self, sample_script_summary: str, mock_music_brief: MusicBrief
    ) -> None:
        """Test that analyze_script_for_music uses the correct agent."""
        mock_result = MagicMock()
        mock_result.final_output = mock_music_brief

        with patch("agents.Runner") as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)

            await analyze_script_for_music(sample_script_summary)

            # Verify Runner.run was called with the music_director_agent
            mock_runner.run.assert_called_once()
            call_args = mock_runner.run.call_args
            assert call_args[0][0] == music_director_agent

    @pytest.mark.asyncio
    async def test_analyze_script_includes_script_in_prompt(
        self, sample_script_summary: str, mock_music_brief: MusicBrief
    ) -> None:
        """Test that the script summary is included in the prompt."""
        mock_result = MagicMock()
        mock_result.final_output = mock_music_brief

        with patch("agents.Runner") as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)

            await analyze_script_for_music(sample_script_summary)

            call_args = mock_runner.run.call_args
            prompt_used = call_args[0][1]
            # Script content should be in the prompt
            assert "Morning Coffee Ritual" in prompt_used
            assert "barista" in prompt_used.lower()

    @pytest.mark.asyncio
    async def test_analyze_script_prompt_requirements(
        self, sample_script_summary: str, mock_music_brief: MusicBrief
    ) -> None:
        """Test that the prompt includes key requirements."""
        mock_result = MagicMock()
        mock_result.final_output = mock_music_brief

        with patch("agents.Runner") as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)

            await analyze_script_for_music(sample_script_summary)

            call_args = mock_runner.run.call_args
            prompt_used = call_args[0][1]
            # Check for key requirements in the prompt
            assert "INSTRUMENTAL" in prompt_used or "instrumental" in prompt_used.lower()
            assert "loop" in prompt_used.lower()
            assert "MusicBrief" in prompt_used


class TestMusicDirectorIntegration:
    """Integration tests for the music director agent (require mocking)."""

    @pytest.mark.asyncio
    async def test_music_director_with_action_script(self) -> None:
        """Test music director with an action-oriented script."""
        action_script = """Title: The Chase
Logline: A thrilling pursuit through city streets.
Tone: Intense, fast-paced, exciting

Scenes:
1. Car speeds around corner, tires screeching
2. Driver checks mirror, sees pursuers
3. Dramatic near-miss with pedestrian
4. Car disappears into tunnel"""

        mock_brief = MusicBrief(
            prompt="High-energy cinematic music with driving percussion and "
            "tense strings, suspenseful and intense mood, fast tempo 130+ BPM.",
            negative_prompt="vocals, singing, lyrics, calm sounds",
            mood=MusicMood.SUSPENSEFUL,
            genre=MusicGenre.CINEMATIC,
            tempo="fast 130 BPM",
            instruments=["orchestra", "percussion", "brass"],
            rationale="Chase scene needs intense, driving music to heighten tension.",
        )

        mock_result = MagicMock()
        mock_result.final_output = mock_brief

        with patch("agents.Runner") as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)

            result = await analyze_script_for_music(action_script)

            assert result.mood == MusicMood.SUSPENSEFUL
            assert result.genre == MusicGenre.CINEMATIC
            assert "vocals" in result.negative_prompt

    @pytest.mark.asyncio
    async def test_music_director_with_peaceful_script(self) -> None:
        """Test music director with a peaceful/nature script."""
        nature_script = """Title: Mountain Sunrise
Logline: Dawn breaks over majestic mountain peaks.
Tone: Serene, contemplative, awe-inspiring

Scenes:
1. First light touches distant peaks
2. Mist slowly rises from the valley
3. Wildflowers sway in gentle breeze
4. Sun fully rises, illuminating the landscape"""

        mock_brief = MusicBrief(
            prompt="Ambient soundscape with soft pads and gentle textures, "
            "peaceful and contemplative mood, very slow tempo.",
            negative_prompt="vocals, singing, lyrics, drums, electronic beats",
            mood=MusicMood.PEACEFUL,
            genre=MusicGenre.AMBIENT,
            tempo="very slow",
            instruments=["ambient pads", "soft strings"],
            rationale="Nature footage benefits from subtle ambient music.",
        )

        mock_result = MagicMock()
        mock_result.final_output = mock_brief

        with patch("agents.Runner") as mock_runner:
            mock_runner.run = AsyncMock(return_value=mock_result)

            result = await analyze_script_for_music(nature_script)

            assert result.mood == MusicMood.PEACEFUL
            assert result.genre == MusicGenre.AMBIENT
