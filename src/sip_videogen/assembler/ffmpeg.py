"""FFmpeg wrapper for video assembly.

This module provides functionality to concatenate video clips
into a final video using FFmpeg.
"""

import logging
import shutil
import subprocess
from pathlib import Path

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
            "-f", "concat",
            "-safe", "0",  # Allow absolute paths
            "-i", str(concat_file),
        ]

        if reencode:
            # Re-encode for maximum compatibility
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
            ])
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
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
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
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate,duration",
            "-show_entries", "format=duration,size",
            "-of", "json",
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
