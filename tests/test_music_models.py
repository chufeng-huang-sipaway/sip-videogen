"""Tests for music data models."""

import pytest
from pydantic import ValidationError

from sip_videogen.models.music import (
    GeneratedMusic,
    MusicBrief,
    MusicGenre,
    MusicMood,
)


class TestMusicMood:
    """Tests for MusicMood enum."""

    def test_music_mood_values(self) -> None:
        """Test that MusicMood has expected values."""
        assert MusicMood.UPBEAT.value == "upbeat"
        assert MusicMood.CALM.value == "calm"
        assert MusicMood.DRAMATIC.value == "dramatic"
        assert MusicMood.SUSPENSEFUL.value == "suspenseful"
        assert MusicMood.JOYFUL.value == "joyful"
        assert MusicMood.MELANCHOLIC.value == "melancholic"
        assert MusicMood.ENERGETIC.value == "energetic"
        assert MusicMood.PEACEFUL.value == "peaceful"

    def test_music_mood_is_string(self) -> None:
        """Test that MusicMood values are strings."""
        assert isinstance(MusicMood.UPBEAT.value, str)
        assert MusicMood.UPBEAT == "upbeat"


class TestMusicGenre:
    """Tests for MusicGenre enum."""

    def test_music_genre_values(self) -> None:
        """Test that MusicGenre has expected values."""
        assert MusicGenre.ORCHESTRAL.value == "orchestral"
        assert MusicGenre.ELECTRONIC.value == "electronic"
        assert MusicGenre.ACOUSTIC.value == "acoustic"
        assert MusicGenre.AMBIENT.value == "ambient"
        assert MusicGenre.CINEMATIC.value == "cinematic"
        assert MusicGenre.POP.value == "pop"
        assert MusicGenre.JAZZ.value == "jazz"
        assert MusicGenre.CLASSICAL.value == "classical"

    def test_music_genre_is_string(self) -> None:
        """Test that MusicGenre values are strings."""
        assert isinstance(MusicGenre.CINEMATIC.value, str)
        assert MusicGenre.CINEMATIC == "cinematic"


class TestMusicBrief:
    """Tests for MusicBrief model."""

    def test_create_valid_music_brief(self) -> None:
        """Test creating a valid MusicBrief with all fields."""
        brief = MusicBrief(
            prompt="Upbeat electronic music with synthesizers and light percussion, "
            "energetic and positive mood, 120 BPM, suitable for tech product showcase",
            negative_prompt="vocals, singing, lyrics, heavy bass",
            mood=MusicMood.ENERGETIC,
            genre=MusicGenre.ELECTRONIC,
            tempo="fast 120 BPM",
            instruments=["synthesizer", "drums", "bass"],
            rationale="The tech showcase video needs energetic music to match the fast pacing",
        )
        assert "synthesizers" in brief.prompt
        assert brief.mood == MusicMood.ENERGETIC
        assert brief.genre == MusicGenre.ELECTRONIC
        assert brief.tempo == "fast 120 BPM"
        assert len(brief.instruments) == 3
        assert "synthesizer" in brief.instruments

    def test_music_brief_defaults(self) -> None:
        """Test MusicBrief default values."""
        brief = MusicBrief(
            prompt="Calm ambient music for meditation",
            mood=MusicMood.CALM,
            genre=MusicGenre.AMBIENT,
            rationale="Meditation video needs peaceful music",
        )
        assert brief.negative_prompt == "vocals, singing, lyrics"
        # Empty/default values for OpenAI structured output compatibility
        assert brief.tempo == "moderate"
        assert brief.instruments == []

    def test_music_brief_missing_required_fields(self) -> None:
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            MusicBrief(
                prompt="Test prompt",
                mood=MusicMood.CALM,
                # missing genre and rationale
            )

    def test_music_brief_custom_negative_prompt(self) -> None:
        """Test MusicBrief with custom negative prompt."""
        brief = MusicBrief(
            prompt="Orchestral cinematic music",
            negative_prompt="drums, electronic sounds, synthesizers",
            mood=MusicMood.DRAMATIC,
            genre=MusicGenre.ORCHESTRAL,
            rationale="Epic scene needs dramatic orchestral music",
        )
        assert brief.negative_prompt == "drums, electronic sounds, synthesizers"

    def test_music_brief_empty_instruments(self) -> None:
        """Test MusicBrief with empty instruments list."""
        brief = MusicBrief(
            prompt="Ambient soundscape",
            mood=MusicMood.PEACEFUL,
            genre=MusicGenre.AMBIENT,
            instruments=[],
            rationale="Background ambience",
        )
        assert brief.instruments == []


class TestGeneratedMusic:
    """Tests for GeneratedMusic model."""

    @pytest.fixture
    def sample_music_brief(self) -> MusicBrief:
        """Create a sample MusicBrief for testing."""
        return MusicBrief(
            prompt="Upbeat electronic music with light percussion",
            mood=MusicMood.UPBEAT,
            genre=MusicGenre.ELECTRONIC,
            rationale="Video needs energetic background music",
        )

    def test_create_generated_music(self, sample_music_brief: MusicBrief) -> None:
        """Test creating a GeneratedMusic with all fields."""
        music = GeneratedMusic(
            file_path="/tmp/output/background_music.wav",
            duration_seconds=32.8,
            prompt_used="Upbeat electronic music with light percussion",
            brief=sample_music_brief,
        )
        assert music.file_path == "/tmp/output/background_music.wav"
        assert music.duration_seconds == 32.8
        assert music.prompt_used == "Upbeat electronic music with light percussion"
        assert music.brief.mood == MusicMood.UPBEAT

    def test_generated_music_default_duration(self, sample_music_brief: MusicBrief) -> None:
        """Test GeneratedMusic default duration value."""
        music = GeneratedMusic(
            file_path="/tmp/music.wav",
            prompt_used="Test prompt",
            brief=sample_music_brief,
        )
        assert music.duration_seconds == 32.8  # Lyria default

    def test_generated_music_custom_duration(self, sample_music_brief: MusicBrief) -> None:
        """Test GeneratedMusic with custom duration."""
        music = GeneratedMusic(
            file_path="/tmp/music.wav",
            duration_seconds=30.5,
            prompt_used="Test prompt",
            brief=sample_music_brief,
        )
        assert music.duration_seconds == 30.5

    def test_generated_music_missing_required_fields(self, sample_music_brief: MusicBrief) -> None:
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            GeneratedMusic(
                file_path="/tmp/music.wav",
                # missing prompt_used and brief
            )

    def test_generated_music_json_serialization(self, sample_music_brief: MusicBrief) -> None:
        """Test that GeneratedMusic can be serialized to JSON."""
        music = GeneratedMusic(
            file_path="/tmp/music.wav",
            duration_seconds=32.8,
            prompt_used="Test prompt",
            brief=sample_music_brief,
        )
        json_dict = music.model_dump()
        assert json_dict["file_path"] == "/tmp/music.wav"
        assert json_dict["duration_seconds"] == 32.8
        assert json_dict["brief"]["mood"] == "upbeat"
        assert json_dict["brief"]["genre"] == "electronic"
