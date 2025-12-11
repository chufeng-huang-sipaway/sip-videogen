"""FFmpeg wrapper for video assembly.

This module provides functionality to concatenate video clips
into a final video using FFmpeg, including background music mixing.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sip_videogen.models.music import GeneratedMusic

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Exception raised for FFmpeg-related errors."""


class FFmpegAssembler:
    """FFmpeg wrapper for concatenating video clips.

    Requires FFmpeg to be installed on the system.
    Install via: brew install ffmpeg (macOS) or apt install ffmpeg (Linux).
    """

    def __init__(self):
        """Initialize FFmpeg assembler and verify FFmpeg is available."""
        self._verify_ffmpeg_installed()

    def _verify_ffmpeg_installed(self) -> None:
        """Verify that FFmpeg is installed and accessible.

        Raises:
            FFmpegError: If FFmpeg is not found in PATH.
        """
        if shutil.which("ffmpeg") is None:
            raise FFmpegError(
                "FFmpeg not found. Please install FFmpeg:\n"
                "  macOS: brew install ffmpeg\n"
                "  Linux: apt install ffmpeg\n"
                "  Windows: https://ffmpeg.org/download.html"
            )
        logger.debug("FFmpeg found in PATH")

    def concatenate_clips(
        self,
        clip_paths: list[Path],
        output_path: Path,
        reencode: bool = False,
    ) -> Path:
        """Concatenate video clips into a single video.

        Args:
            clip_paths: List of paths to video clips, in order.
            output_path: Path for the final concatenated video.
            reencode: If True, re-encode the video (slower but more compatible).
                     If False, use stream copy (faster but requires same codecs).

        Returns:
            Path to the concatenated video file.

        Raises:
            FFmpegError: If concatenation fails or no clips provided.
        """
        if not clip_paths:
            raise FFmpegError("No video clips provided for concatenation")

        # Verify all clips exist
        for clip in clip_paths:
            if not clip.exists():
                raise FFmpegError(f"Video clip not found: {clip}")

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create concat file listing all clips
        concat_file = output_path.parent / f".concat_list_{output_path.stem}.txt"
        try:
            with open(concat_file, "w") as f:
                for clip in clip_paths:
                    # Escape single quotes in path
                    escaped_path = str(clip.absolute()).replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            logger.info(
                "Concatenating %d clips into %s",
                len(clip_paths),
                output_path,
            )

            # Build FFmpeg command
            cmd = self._build_concat_command(concat_file, output_path, reencode)

            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )

            logger.debug("FFmpeg stdout: %s", result.stdout)
            if result.stderr:
                logger.debug("FFmpeg stderr: %s", result.stderr)

            logger.info("Successfully created: %s", output_path)
            return output_path

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise FFmpegError(f"FFmpeg concatenation failed: {error_msg}") from e
        finally:
            # Cleanup concat file
            if concat_file.exists():
                concat_file.unlink()

    def _build_concat_command(
        self,
        concat_file: Path,
        output_path: Path,
        reencode: bool,
    ) -> list[str]:
        """Build the FFmpeg command for concatenation.

        Args:
            concat_file: Path to the concat list file.
            output_path: Path for the output video.
            reencode: Whether to re-encode the video.

        Returns:
            List of command arguments.
        """
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file if exists
            "-f",
            "concat",
            "-safe",
            "0",  # Allow absolute paths
            "-i",
            str(concat_file),
        ]

        if reencode:
            # Re-encode for maximum compatibility
            cmd.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                ]
            )
        else:
            # Stream copy (fast, but requires same codecs)
            cmd.extend(["-c", "copy"])

        cmd.append(str(output_path))
        return cmd

    def get_video_duration(self, video_path: Path) -> float:
        """Get the duration of a video file in seconds.

        Args:
            video_path: Path to the video file.

        Returns:
            Duration in seconds.

        Raises:
            FFmpegError: If ffprobe fails or video not found.
        """
        if not video_path.exists():
            raise FFmpegError(f"Video file not found: {video_path}")

        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            return float(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            raise FFmpegError(f"Failed to get video duration: {e.stderr}") from e
        except ValueError as e:
            raise FFmpegError(f"Invalid duration value: {e}") from e

    def get_video_info(self, video_path: Path) -> dict:
        """Get detailed information about a video file.

        Args:
            video_path: Path to the video file.

        Returns:
            Dictionary with video information (codec, resolution, duration, etc.).

        Raises:
            FFmpegError: If ffprobe fails or video not found.
        """
        if not video_path.exists():
            raise FFmpegError(f"Video file not found: {video_path}")

        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,r_frame_rate,duration",
            "-show_entries",
            "format=duration,size",
            "-of",
            "json",
            str(video_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            import json

            data = json.loads(result.stdout)

            info = {"path": str(video_path)}

            # Extract stream info
            if data.get("streams"):
                stream = data["streams"][0]
                info["codec"] = stream.get("codec_name")
                info["width"] = stream.get("width")
                info["height"] = stream.get("height")
                if stream.get("r_frame_rate"):
                    # Parse frame rate (e.g., "30/1" -> 30.0)
                    fps_parts = stream["r_frame_rate"].split("/")
                    if len(fps_parts) == 2 and int(fps_parts[1]) != 0:
                        info["fps"] = int(fps_parts[0]) / int(fps_parts[1])

            # Extract format info
            if data.get("format"):
                fmt = data["format"]
                if fmt.get("duration"):
                    info["duration"] = float(fmt["duration"])
                if fmt.get("size"):
                    info["size_bytes"] = int(fmt["size"])

            return info
        except subprocess.CalledProcessError as e:
            raise FFmpegError(f"Failed to get video info: {e.stderr}") from e
        except (ValueError, KeyError) as e:
            raise FFmpegError(f"Failed to parse video info: {e}") from e

    def has_audio_stream(self, video_path: Path) -> bool:
        """Check if a video file has an audio stream.

        Args:
            video_path: Path to the video file.

        Returns:
            True if the video has at least one audio stream, False otherwise.
        """
        if not video_path.exists():
            return False

        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",  # Select audio streams only
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(video_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            # If there's any output, there's at least one audio stream
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def assemble_with_music(
        self,
        clip_paths: list[Path],
        music: GeneratedMusic,
        output_path: Path,
        music_volume: float = 0.2,
        fade_duration: float = 2.0,
    ) -> Path:
        """Assemble video clips and overlay background music.

        Concatenates video clips, then mixes in background music with
        fade in/out effects. The music is looped to match the video
        duration if needed.

        Args:
            clip_paths: List of paths to video clips, in order.
            music: Generated music track to overlay.
            output_path: Path for the final video with music.
            music_volume: Volume level for background music (0.0-1.0).
                         Default is 0.2 (20%) to not overpower dialogue.
            fade_duration: Duration of fade in/out effects in seconds.
                          Default is 2.0 seconds.

        Returns:
            Path to the assembled video file with music.

        Raises:
            FFmpegError: If assembly or mixing fails.
        """
        if not clip_paths:
            raise FFmpegError("No video clips provided for assembly")

        # Validate music file exists
        music_path = Path(music.file_path)
        if not music_path.exists():
            raise FFmpegError(f"Music file not found: {music.file_path}")

        # Validate volume
        if not 0.0 <= music_volume <= 1.0:
            raise FFmpegError(f"music_volume must be between 0.0 and 1.0, got {music_volume}")

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Step 1: Concatenate video clips to a temp file
        concat_temp = output_path.parent / f".concat_temp_{output_path.stem}.mp4"
        try:
            self.concatenate_clips(clip_paths, concat_temp, reencode=False)

            # Step 2: Get video duration for fade calculation
            duration = self.get_video_duration(concat_temp)
            fade_out_start = max(0, duration - fade_duration)

            # Step 2.5: Check if video has audio stream
            has_audio = self.has_audio_stream(concat_temp)

            logger.info(
                "Mixing music into video (duration: %.1fs, volume: %.0f%%, has_audio: %s)",
                duration,
                music_volume * 100,
                has_audio,
            )

            # Step 3: Build and run FFmpeg command for audio mixing
            cmd = self._build_music_mix_command(
                video_path=concat_temp,
                music_path=music_path,
                output_path=output_path,
                music_volume=music_volume,
                fade_duration=fade_duration,
                fade_out_start=fade_out_start,
                has_video_audio=has_audio,
            )

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )

            logger.debug("FFmpeg stdout: %s", result.stdout)
            if result.stderr:
                logger.debug("FFmpeg stderr: %s", result.stderr)

            logger.info("Successfully created video with music: %s", output_path)
            return output_path

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise FFmpegError(f"FFmpeg music mixing failed: {error_msg}") from e
        finally:
            # Cleanup temp file
            if concat_temp.exists():
                concat_temp.unlink()

    def _build_music_mix_command(
        self,
        video_path: Path,
        music_path: Path,
        output_path: Path,
        music_volume: float,
        fade_duration: float,
        fade_out_start: float,
        has_video_audio: bool = True,
    ) -> list[str]:
        """Build FFmpeg command for mixing music with video.

        The command:
        1. Takes video input with its audio (if present)
        2. Loops the music track to match video duration
        3. Applies fade in/out to the music
        4. Adjusts music volume
        5. Mixes video audio and music together (if video has audio)
        6. Uses shortest stream to determine output length

        Args:
            video_path: Path to the concatenated video.
            music_path: Path to the music file.
            output_path: Path for the output video.
            music_volume: Volume level for music (0.0-1.0).
            fade_duration: Duration of fade effects in seconds.
            fade_out_start: When to start fade out (in seconds).
            has_video_audio: Whether the video has an audio stream.

        Returns:
            List of command arguments for FFmpeg.
        """
        if has_video_audio:
            # Build the filter complex for audio mixing
            # [1:a] = music input (looped)
            # - afade: fade in at start, fade out before end
            # - volume: reduce music volume
            # [0:a] = video audio
            # - volume: slightly reduce to make room for music
            # amix: combine both audio streams
            video_audio_volume = 1.0 - (music_volume * 0.3)  # Slight reduction

            filter_complex = (
                f"[1:a]afade=t=in:st=0:d={fade_duration},"
                f"afade=t=out:st={fade_out_start}:d={fade_duration},"
                f"volume={music_volume}[music];"
                f"[0:a]volume={video_audio_volume}[video_audio];"
                f"[video_audio][music]amix=inputs=2:duration=first:dropout_transition=2[audio_out]"
            )
        else:
            # Video has no audio - just use the music track
            logger.info("Video has no audio stream, using music only")
            filter_complex = (
                f"[1:a]afade=t=in:st=0:d={fade_duration},"
                f"afade=t=out:st={fade_out_start}:d={fade_duration},"
                f"volume={music_volume}[audio_out]"
            )

        return [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i",
            str(video_path),  # Video input (index 0)
            "-stream_loop",
            "-1",  # Loop music indefinitely
            "-i",
            str(music_path),  # Music input (index 1)
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",  # Use video from input 0
            "-map",
            "[audio_out]",  # Use mixed/music-only audio
            "-shortest",  # Stop when shortest input ends
            "-c:v",
            "copy",  # Copy video stream (no re-encode)
            "-c:a",
            "aac",  # Encode audio as AAC
            "-b:a",
            "192k",  # Audio bitrate
            str(output_path),
        ]
