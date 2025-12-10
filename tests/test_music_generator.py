"""Tests for music generator using Lyria 2."""

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from sip_videogen.generators.music_generator import (
    MusicGenerationError,
    MusicGenerator,
)
from sip_videogen.models.music import (
    GeneratedMusic,
    MusicBrief,
    MusicGenre,
    MusicMood,
)


@pytest.fixture
def sample_music_brief() -> MusicBrief:
    """Create a sample MusicBrief for testing."""
    return MusicBrief(
        prompt="Upbeat electronic music with synthesizers and light percussion, "
        "energetic and positive mood, 120 BPM",
        negative_prompt="vocals, singing, lyrics",
        mood=MusicMood.ENERGETIC,
        genre=MusicGenre.ELECTRONIC,
        tempo="fast 120 BPM",
        instruments=["synthesizer", "drums"],
        rationale="Video needs energetic background music",
    )


@pytest.fixture
def mock_audio_content() -> bytes:
    """Create mock WAV audio content."""
    # Minimal valid WAV header + some data
    wav_header = b"RIFF" + b"\x00" * 4 + b"WAVEfmt " + b"\x10\x00\x00\x00"
    wav_header += b"\x01\x00\x02\x00"  # PCM, stereo
    wav_header += b"\x80\xbb\x00\x00"  # 48000 Hz
    wav_header += b"\x00\xee\x02\x00"  # byte rate
    wav_header += b"\x04\x00\x10\x00"  # block align, bits per sample
    wav_header += b"data" + b"\x00" * 4  # data chunk
    return wav_header + b"\x00" * 1000  # Add some audio data


@pytest.fixture
def music_generator() -> MusicGenerator:
    """Create a MusicGenerator instance for testing."""
    return MusicGenerator(
        project_id="test-project",
        location="us-central1",
    )


class TestMusicGeneratorInit:
    """Tests for MusicGenerator initialization."""

    def test_init_default_location(self) -> None:
        """Test MusicGenerator initialization with default location."""
        generator = MusicGenerator(project_id="my-project")
        assert generator.project_id == "my-project"
        assert generator.location == "us-central1"
        assert "my-project" in generator.endpoint
        assert "lyria-002" in generator.endpoint

    def test_init_custom_location(self) -> None:
        """Test MusicGenerator initialization with custom location."""
        generator = MusicGenerator(
            project_id="my-project",
            location="europe-west4",
        )
        assert generator.location == "europe-west4"
        assert "europe-west4" in generator.endpoint


class TestMusicGeneratorGenerate:
    """Tests for MusicGenerator.generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        music_generator: MusicGenerator,
        sample_music_brief: MusicBrief,
        mock_audio_content: bytes,
        tmp_path: Path,
    ) -> None:
        """Test successful music generation."""
        encoded_audio = base64.b64encode(mock_audio_content).decode("utf-8")
        mock_response = {
            "predictions": [
                {
                    "bytesBase64Encoded": encoded_audio,
                    "mimeType": "audio/wav",
                }
            ]
        }

        with (
            patch.object(music_generator, "_get_auth_headers") as mock_auth,
            patch("sip_videogen.generators.music_generator.requests.post") as mock_post,
        ):
            mock_auth.return_value = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            }
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_post.return_value = mock_response_obj

            result = await music_generator.generate(sample_music_brief, tmp_path)

            assert isinstance(result, GeneratedMusic)
            assert result.file_path == str(tmp_path / "background_music.wav")
            assert result.duration_seconds == 30.0
            assert result.prompt_used == sample_music_brief.prompt
            assert result.brief == sample_music_brief

            # Verify file was written
            output_file = tmp_path / "background_music.wav"
            assert output_file.exists()
            assert output_file.read_bytes() == mock_audio_content

    @pytest.mark.asyncio
    async def test_generate_with_seed(
        self,
        music_generator: MusicGenerator,
        sample_music_brief: MusicBrief,
        mock_audio_content: bytes,
        tmp_path: Path,
    ) -> None:
        """Test music generation with seed for reproducibility."""
        encoded_audio = base64.b64encode(mock_audio_content).decode("utf-8")
        mock_response = {
            "predictions": [{"bytesBase64Encoded": encoded_audio}]
        }

        with (
            patch.object(music_generator, "_get_auth_headers") as mock_auth,
            patch("sip_videogen.generators.music_generator.requests.post") as mock_post,
        ):
            mock_auth.return_value = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            }
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_post.return_value = mock_response_obj

            await music_generator.generate(sample_music_brief, tmp_path, seed=12345)

            # Verify seed was included in request
            call_args = mock_post.call_args
            request_body = call_args.kwargs["json"]
            assert request_body["instances"][0]["seed"] == 12345

    @pytest.mark.asyncio
    async def test_generate_empty_predictions(
        self,
        music_generator: MusicGenerator,
        sample_music_brief: MusicBrief,
        tmp_path: Path,
    ) -> None:
        """Test handling of empty predictions response."""
        mock_response = {"predictions": []}

        with (
            patch.object(music_generator, "_get_auth_headers") as mock_auth,
            patch("sip_videogen.generators.music_generator.requests.post") as mock_post,
        ):
            mock_auth.return_value = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            }
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_post.return_value = mock_response_obj

            with pytest.raises(MusicGenerationError, match="No predictions returned"):
                await music_generator.generate(sample_music_brief, tmp_path)

    @pytest.mark.asyncio
    async def test_generate_missing_audio_content(
        self,
        music_generator: MusicGenerator,
        sample_music_brief: MusicBrief,
        tmp_path: Path,
    ) -> None:
        """Test handling of response without audio content."""
        mock_response = {"predictions": [{"mimeType": "audio/wav"}]}

        with (
            patch.object(music_generator, "_get_auth_headers") as mock_auth,
            patch("sip_videogen.generators.music_generator.requests.post") as mock_post,
        ):
            mock_auth.return_value = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            }
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_post.return_value = mock_response_obj

            with pytest.raises(MusicGenerationError, match="No audio content"):
                await music_generator.generate(sample_music_brief, tmp_path)

    @pytest.mark.asyncio
    async def test_generate_http_error(
        self,
        music_generator: MusicGenerator,
        sample_music_brief: MusicBrief,
        tmp_path: Path,
    ) -> None:
        """Test handling of HTTP error from API."""
        with (
            patch.object(music_generator, "_get_auth_headers") as mock_auth,
            patch("sip_videogen.generators.music_generator.requests.post") as mock_post,
        ):
            mock_auth.return_value = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            }
            mock_response_obj = MagicMock()
            mock_response_obj.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=MagicMock(text="Bad Request", json=lambda: {"error": "Invalid prompt"})
            )
            mock_post.return_value = mock_response_obj

            with pytest.raises(MusicGenerationError, match="API request failed"):
                await music_generator.generate(sample_music_brief, tmp_path)

    @pytest.mark.asyncio
    async def test_generate_network_error(
        self,
        music_generator: MusicGenerator,
        sample_music_brief: MusicBrief,
        tmp_path: Path,
    ) -> None:
        """Test handling of network error."""
        with (
            patch.object(music_generator, "_get_auth_headers") as mock_auth,
            patch("sip_videogen.generators.music_generator.requests.post") as mock_post,
        ):
            mock_auth.return_value = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            }
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

            with pytest.raises(MusicGenerationError, match="Network error"):
                await music_generator.generate(sample_music_brief, tmp_path)

    @pytest.mark.asyncio
    async def test_generate_creates_output_directory(
        self,
        music_generator: MusicGenerator,
        sample_music_brief: MusicBrief,
        mock_audio_content: bytes,
        tmp_path: Path,
    ) -> None:
        """Test that output directory is created if it doesn't exist."""
        output_dir = tmp_path / "nested" / "output" / "dir"
        encoded_audio = base64.b64encode(mock_audio_content).decode("utf-8")
        mock_response = {
            "predictions": [{"bytesBase64Encoded": encoded_audio}]
        }

        with (
            patch.object(music_generator, "_get_auth_headers") as mock_auth,
            patch("sip_videogen.generators.music_generator.requests.post") as mock_post,
        ):
            mock_auth.return_value = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            }
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_post.return_value = mock_response_obj

            result = await music_generator.generate(sample_music_brief, output_dir)

            assert output_dir.exists()
            assert (output_dir / "background_music.wav").exists()
            assert result.file_path == str(output_dir / "background_music.wav")


class TestMusicGeneratorAuth:
    """Tests for MusicGenerator authentication."""

    def test_get_auth_headers_success(self) -> None:
        """Test successful authentication header retrieval."""
        generator = MusicGenerator(project_id="test-project")

        with patch("sip_videogen.generators.music_generator.google.auth.default") as mock_default:
            mock_creds = MagicMock()
            mock_creds.token = "test-token"
            mock_default.return_value = (mock_creds, "test-project")

            headers = generator._get_auth_headers()

            assert headers["Authorization"] == "Bearer test-token"
            assert headers["Content-Type"] == "application/json"

    def test_get_auth_headers_failure(self) -> None:
        """Test authentication failure handling."""
        generator = MusicGenerator(project_id="test-project")

        with patch("sip_videogen.generators.music_generator.google.auth.default") as mock_default:
            mock_default.side_effect = Exception("Auth failed")

            with pytest.raises(MusicGenerationError, match="Authentication failed"):
                generator._get_auth_headers()


class TestMusicGeneratorConstants:
    """Tests for MusicGenerator constants."""

    def test_lyria_duration_constant(self) -> None:
        """Test that LYRIA_DURATION_SECONDS constant is correct."""
        assert MusicGenerator.LYRIA_DURATION_SECONDS == 30.0


class TestMusicGeneratorRequestBody:
    """Tests for MusicGenerator request body construction."""

    @pytest.mark.asyncio
    async def test_request_includes_prompt(
        self,
        music_generator: MusicGenerator,
        sample_music_brief: MusicBrief,
        mock_audio_content: bytes,
        tmp_path: Path,
    ) -> None:
        """Test that request body includes prompt."""
        encoded_audio = base64.b64encode(mock_audio_content).decode("utf-8")
        mock_response = {"predictions": [{"bytesBase64Encoded": encoded_audio}]}

        with (
            patch.object(music_generator, "_get_auth_headers") as mock_auth,
            patch("sip_videogen.generators.music_generator.requests.post") as mock_post,
        ):
            mock_auth.return_value = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            }
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_post.return_value = mock_response_obj

            await music_generator.generate(sample_music_brief, tmp_path)

            call_args = mock_post.call_args
            request_body = call_args.kwargs["json"]
            assert request_body["instances"][0]["prompt"] == sample_music_brief.prompt
            neg_prompt = request_body["instances"][0]["negative_prompt"]
            assert neg_prompt == sample_music_brief.negative_prompt

    @pytest.mark.asyncio
    async def test_request_without_negative_prompt(
        self,
        music_generator: MusicGenerator,
        mock_audio_content: bytes,
        tmp_path: Path,
    ) -> None:
        """Test request body when no negative prompt is provided."""
        brief = MusicBrief(
            prompt="Calm ambient music",
            negative_prompt="",  # Empty string
            mood=MusicMood.CALM,
            genre=MusicGenre.AMBIENT,
            rationale="Background music",
        )
        encoded_audio = base64.b64encode(mock_audio_content).decode("utf-8")
        mock_response = {"predictions": [{"bytesBase64Encoded": encoded_audio}]}

        with (
            patch.object(music_generator, "_get_auth_headers") as mock_auth,
            patch("sip_videogen.generators.music_generator.requests.post") as mock_post,
        ):
            mock_auth.return_value = {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            }
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_post.return_value = mock_response_obj

            await music_generator.generate(brief, tmp_path)

            call_args = mock_post.call_args
            request_body = call_args.kwargs["json"]
            # Empty string is falsy, so negative_prompt should not be included
            assert "negative_prompt" not in request_body["instances"][0]
