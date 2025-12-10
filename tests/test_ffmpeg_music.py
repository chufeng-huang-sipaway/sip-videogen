"""Tests for FFmpeg audio mixing with background music."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sip_videogen.assembler.ffmpeg import FFmpegAssembler, FFmpegError
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
        prompt="Upbeat electronic music with synthesizers",
        negative_prompt="vocals, singing, lyrics",
        mood=MusicMood.ENERGETIC,
        genre=MusicGenre.ELECTRONIC,
        tempo="fast 120 BPM",
        instruments=["synthesizer", "drums"],
        rationale="Video needs energetic background music",
    )


@pytest.fixture
def sample_generated_music(
    tmp_path: Path,
    sample_music_brief: MusicBrief,
) -> GeneratedMusic:
    """Create a sample GeneratedMusic with a real file."""
    # Create a minimal WAV file for testing
    music_file = tmp_path / "test_music.wav"
    wav_header = b"RIFF" + b"\x00" * 4 + b"WAVEfmt " + b"\x10\x00\x00\x00"
    wav_header += b"\x01\x00\x02\x00"  # PCM, stereo
    wav_header += b"\x80\xbb\x00\x00"  # 48000 Hz
    wav_header += b"\x00\xee\x02\x00"  # byte rate
    wav_header += b"\x04\x00\x10\x00"  # block align, bits per sample
    wav_header += b"data" + b"\x00" * 4
    music_file.write_bytes(wav_header + b"\x00" * 1000)

    return GeneratedMusic(
        file_path=str(music_file),
        duration_seconds=30.0,
        prompt_used=sample_music_brief.prompt,
        brief=sample_music_brief,
    )


@pytest.fixture
def sample_video_clips(tmp_path: Path) -> list[Path]:
    """Create sample video clip paths for testing."""
    clips = []
    for i in range(3):
        clip = tmp_path / f"clip_{i}.mp4"
        clip.write_bytes(b"fake video content")
        clips.append(clip)
    return clips


@pytest.fixture
def assembler() -> FFmpegAssembler:
    """Create an FFmpegAssembler with mocked FFmpeg check."""
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        return FFmpegAssembler()


class TestAssembleWithMusicValidation:
    """Tests for input validation in assemble_with_music."""

    def test_empty_clips_raises_error(
        self,
        assembler: FFmpegAssembler,
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test that empty clips list raises an error."""
        output_path = tmp_path / "output.mp4"

        with pytest.raises(FFmpegError, match="No video clips provided"):
            assembler.assemble_with_music([], sample_generated_music, output_path)

    def test_missing_music_file_raises_error(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_music_brief: MusicBrief,
        tmp_path: Path,
    ) -> None:
        """Test that missing music file raises an error."""
        music = GeneratedMusic(
            file_path="/nonexistent/music.wav",
            duration_seconds=30.0,
            prompt_used="test",
            brief=sample_music_brief,
        )
        output_path = tmp_path / "output.mp4"

        with pytest.raises(FFmpegError, match="Music file not found"):
            assembler.assemble_with_music(sample_video_clips, music, output_path)

    def test_invalid_volume_too_high(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test that volume > 1.0 raises an error."""
        output_path = tmp_path / "output.mp4"

        with pytest.raises(FFmpegError, match="music_volume must be between"):
            assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
                music_volume=1.5,
            )

    def test_invalid_volume_negative(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test that negative volume raises an error."""
        output_path = tmp_path / "output.mp4"

        with pytest.raises(FFmpegError, match="music_volume must be between"):
            assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
                music_volume=-0.1,
            )

    def test_valid_volume_boundaries(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test that volume at boundaries (0.0 and 1.0) is accepted."""
        output_path = tmp_path / "output.mp4"

        # Mock the internal calls to avoid actual FFmpeg execution
        with (
            patch.object(assembler, "concatenate_clips"),
            patch.object(assembler, "get_video_duration", return_value=30.0),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            # Create the temp concat file
            concat_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"
            concat_temp.write_bytes(b"temp")

            # Volume 0.0 should work
            assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
                music_volume=0.0,
            )

            # Volume 1.0 should work
            assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
                music_volume=1.0,
            )


class TestAssembleWithMusicExecution:
    """Tests for the execution flow of assemble_with_music."""

    def test_successful_assembly(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test successful video assembly with music."""
        output_path = tmp_path / "output.mp4"

        with (
            patch.object(assembler, "concatenate_clips") as mock_concat,
            patch.object(assembler, "get_video_duration", return_value=60.0),
            patch.object(assembler, "has_audio_stream", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            # Create the temp concat file that concatenate_clips would create
            concat_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"
            concat_temp.write_bytes(b"temp video content")
            mock_concat.return_value = concat_temp

            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            result = assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
            )

            assert result == output_path
            mock_concat.assert_called_once()
            mock_run.assert_called_once()

    def test_concatenate_clips_called_first(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test that concatenate_clips is called with correct arguments."""
        output_path = tmp_path / "output.mp4"
        expected_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"

        with (
            patch.object(assembler, "concatenate_clips") as mock_concat,
            patch.object(assembler, "get_video_duration", return_value=30.0),
            patch("subprocess.run") as mock_run,
        ):
            expected_temp.write_bytes(b"temp")
            mock_concat.return_value = expected_temp
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
            )

            mock_concat.assert_called_once_with(
                sample_video_clips,
                expected_temp,
                reencode=False,
            )

    def test_creates_output_directory(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test that output directory is created if it doesn't exist."""
        output_path = tmp_path / "nested" / "dir" / "output.mp4"

        with (
            patch.object(assembler, "concatenate_clips") as mock_concat,
            patch.object(assembler, "get_video_duration", return_value=30.0),
            patch("subprocess.run") as mock_run,
        ):
            concat_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            concat_temp.write_bytes(b"temp")
            mock_concat.return_value = concat_temp
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
            )

            assert output_path.parent.exists()

    def test_temp_file_cleanup_on_success(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test that temp concat file is cleaned up after success."""
        output_path = tmp_path / "output.mp4"
        concat_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"

        with (
            patch.object(assembler, "concatenate_clips") as mock_concat,
            patch.object(assembler, "get_video_duration", return_value=30.0),
            patch("subprocess.run") as mock_run,
        ):
            concat_temp.write_bytes(b"temp")
            mock_concat.return_value = concat_temp
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
            )

            # Temp file should be deleted
            assert not concat_temp.exists()

    def test_temp_file_cleanup_on_error(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test that temp concat file is cleaned up even on error."""
        output_path = tmp_path / "output.mp4"
        concat_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"

        with (
            patch.object(assembler, "concatenate_clips") as mock_concat,
            patch.object(assembler, "get_video_duration", return_value=30.0),
            patch("subprocess.run") as mock_run,
        ):
            import subprocess

            concat_temp.write_bytes(b"temp")
            mock_concat.return_value = concat_temp
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="error")

            with pytest.raises(FFmpegError):
                assembler.assemble_with_music(
                    sample_video_clips,
                    sample_generated_music,
                    output_path,
                )

            # Temp file should still be deleted
            assert not concat_temp.exists()


class TestBuildMusicMixCommand:
    """Tests for _build_music_mix_command."""

    def test_command_structure(self, assembler: FFmpegAssembler, tmp_path: Path) -> None:
        """Test that command has correct structure."""
        video_path = tmp_path / "video.mp4"
        music_path = tmp_path / "music.wav"
        output_path = tmp_path / "output.mp4"

        cmd = assembler._build_music_mix_command(
            video_path=video_path,
            music_path=music_path,
            output_path=output_path,
            music_volume=0.2,
            fade_duration=2.0,
            fade_out_start=28.0,
        )

        assert cmd[0] == "ffmpeg"
        assert "-y" in cmd
        assert str(video_path) in cmd
        assert str(music_path) in cmd
        assert str(output_path) in cmd

    def test_stream_loop_for_music(self, assembler: FFmpegAssembler, tmp_path: Path) -> None:
        """Test that music is set to loop indefinitely."""
        cmd = assembler._build_music_mix_command(
            video_path=tmp_path / "video.mp4",
            music_path=tmp_path / "music.wav",
            output_path=tmp_path / "output.mp4",
            music_volume=0.2,
            fade_duration=2.0,
            fade_out_start=28.0,
        )

        # -stream_loop -1 should appear before the music input
        stream_loop_idx = cmd.index("-stream_loop")
        assert cmd[stream_loop_idx + 1] == "-1"

    def test_filter_complex_includes_fade(self, assembler: FFmpegAssembler, tmp_path: Path) -> None:
        """Test that filter complex includes fade effects."""
        cmd = assembler._build_music_mix_command(
            video_path=tmp_path / "video.mp4",
            music_path=tmp_path / "music.wav",
            output_path=tmp_path / "output.mp4",
            music_volume=0.2,
            fade_duration=2.0,
            fade_out_start=28.0,
        )

        filter_idx = cmd.index("-filter_complex")
        filter_complex = cmd[filter_idx + 1]

        assert "afade=t=in" in filter_complex
        assert "afade=t=out" in filter_complex
        assert "st=28.0" in filter_complex  # fade_out_start

    def test_filter_complex_includes_volume(
        self, assembler: FFmpegAssembler, tmp_path: Path
    ) -> None:
        """Test that filter complex includes volume adjustments."""
        cmd = assembler._build_music_mix_command(
            video_path=tmp_path / "video.mp4",
            music_path=tmp_path / "music.wav",
            output_path=tmp_path / "output.mp4",
            music_volume=0.5,
            fade_duration=2.0,
            fade_out_start=28.0,
        )

        filter_idx = cmd.index("-filter_complex")
        filter_complex = cmd[filter_idx + 1]

        assert "volume=0.5" in filter_complex  # music volume
        assert "amix=" in filter_complex

    def test_video_copy_audio_encode(self, assembler: FFmpegAssembler, tmp_path: Path) -> None:
        """Test that video is copied and audio is encoded."""
        cmd = assembler._build_music_mix_command(
            video_path=tmp_path / "video.mp4",
            music_path=tmp_path / "music.wav",
            output_path=tmp_path / "output.mp4",
            music_volume=0.2,
            fade_duration=2.0,
            fade_out_start=28.0,
        )

        # Video should be copied (no re-encode)
        cv_idx = cmd.index("-c:v")
        assert cmd[cv_idx + 1] == "copy"

        # Audio should be encoded as AAC
        ca_idx = cmd.index("-c:a")
        assert cmd[ca_idx + 1] == "aac"

    def test_shortest_flag_present(self, assembler: FFmpegAssembler, tmp_path: Path) -> None:
        """Test that -shortest flag is present to stop at video end."""
        cmd = assembler._build_music_mix_command(
            video_path=tmp_path / "video.mp4",
            music_path=tmp_path / "music.wav",
            output_path=tmp_path / "output.mp4",
            music_volume=0.2,
            fade_duration=2.0,
            fade_out_start=28.0,
        )

        assert "-shortest" in cmd

    def test_different_volume_levels(self, assembler: FFmpegAssembler, tmp_path: Path) -> None:
        """Test filter complex with different volume levels."""
        for volume in [0.1, 0.3, 0.5, 0.8, 1.0]:
            cmd = assembler._build_music_mix_command(
                video_path=tmp_path / "video.mp4",
                music_path=tmp_path / "music.wav",
                output_path=tmp_path / "output.mp4",
                music_volume=volume,
                fade_duration=2.0,
                fade_out_start=28.0,
            )

            filter_idx = cmd.index("-filter_complex")
            filter_complex = cmd[filter_idx + 1]

            assert f"volume={volume}" in filter_complex

    def test_different_fade_durations(self, assembler: FFmpegAssembler, tmp_path: Path) -> None:
        """Test filter complex with different fade durations."""
        for fade_dur in [0.5, 1.0, 2.0, 5.0]:
            cmd = assembler._build_music_mix_command(
                video_path=tmp_path / "video.mp4",
                music_path=tmp_path / "music.wav",
                output_path=tmp_path / "output.mp4",
                music_volume=0.2,
                fade_duration=fade_dur,
                fade_out_start=28.0,
            )

            filter_idx = cmd.index("-filter_complex")
            filter_complex = cmd[filter_idx + 1]

            assert f"d={fade_dur}" in filter_complex


class TestAssembleWithMusicEdgeCases:
    """Tests for edge cases in assemble_with_music."""

    def test_very_short_video(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test assembly with very short video (shorter than fade)."""
        output_path = tmp_path / "output.mp4"

        with (
            patch.object(assembler, "concatenate_clips") as mock_concat,
            patch.object(assembler, "get_video_duration", return_value=1.0),  # 1 second
            patch("subprocess.run") as mock_run,
        ):
            concat_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"
            concat_temp.write_bytes(b"temp")
            mock_concat.return_value = concat_temp
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            # Should not raise - fade_out_start will be max(0, 1.0 - 2.0) = 0
            result = assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
            )

            assert result == output_path

    def test_single_clip(
        self,
        assembler: FFmpegAssembler,
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test assembly with single video clip."""
        clip = tmp_path / "single_clip.mp4"
        clip.write_bytes(b"video content")
        output_path = tmp_path / "output.mp4"

        with (
            patch.object(assembler, "concatenate_clips") as mock_concat,
            patch.object(assembler, "get_video_duration", return_value=10.0),
            patch("subprocess.run") as mock_run,
        ):
            concat_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"
            concat_temp.write_bytes(b"temp")
            mock_concat.return_value = concat_temp
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            result = assembler.assemble_with_music(
                [clip],
                sample_generated_music,
                output_path,
            )

            assert result == output_path
            mock_concat.assert_called_once()

    def test_zero_fade_duration(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test assembly with zero fade duration."""
        output_path = tmp_path / "output.mp4"

        with (
            patch.object(assembler, "concatenate_clips") as mock_concat,
            patch.object(assembler, "get_video_duration", return_value=30.0),
            patch("subprocess.run") as mock_run,
        ):
            concat_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"
            concat_temp.write_bytes(b"temp")
            mock_concat.return_value = concat_temp
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            result = assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
                fade_duration=0.0,
            )

            assert result == output_path

    def test_zero_volume(
        self,
        assembler: FFmpegAssembler,
        sample_video_clips: list[Path],
        sample_generated_music: GeneratedMusic,
        tmp_path: Path,
    ) -> None:
        """Test assembly with zero music volume (effectively muted)."""
        output_path = tmp_path / "output.mp4"

        with (
            patch.object(assembler, "concatenate_clips") as mock_concat,
            patch.object(assembler, "get_video_duration", return_value=30.0),
            patch("subprocess.run") as mock_run,
        ):
            concat_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"
            concat_temp.write_bytes(b"temp")
            mock_concat.return_value = concat_temp
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            # Volume 0.0 should work (music will be silent)
            result = assembler.assemble_with_music(
                sample_video_clips,
                sample_generated_music,
                output_path,
                music_volume=0.0,
            )

            assert result == output_path
