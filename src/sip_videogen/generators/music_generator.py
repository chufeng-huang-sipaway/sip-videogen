"""Music Generator for creating background music using Google Vertex AI Lyria 2.

This module provides music generation functionality using Google's Lyria 2 model
to create background music tracks for videos.
"""

import base64
from pathlib import Path

import google.auth
import google.auth.transport.requests
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from sip_videogen.config.logging import get_logger
from sip_videogen.models.music import GeneratedMusic, MusicBrief

logger = get_logger(__name__)


class MusicGenerationError(Exception):
    """Raised when music generation fails."""

    pass


class MusicGenerator:
    """Generates background music using Google Vertex AI Lyria 2.

    This class handles the generation of background music tracks using
    Lyria 2, Google's text-to-music model.
    """

    # Lyria 2 generates approximately 30-second clips
    LYRIA_DURATION_SECONDS = 30.0

    def __init__(self, project_id: str, location: str = "us-central1"):
        """Initialize the music generator.

        Args:
            project_id: Google Cloud Project ID.
            location: Google Cloud region for Vertex AI. Defaults to us-central1.
        """
        self.project_id = project_id
        self.location = location
        self.endpoint = (
            f"https://{location}-aiplatform.googleapis.com/v1/"
            f"projects/{project_id}/locations/{location}/"
            f"publishers/google/models/lyria-002:predict"
        )
        logger.debug(f"Initialized MusicGenerator with project: {project_id}")

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers using Application Default Credentials.

        Returns:
            Dictionary with Authorization and Content-Type headers.

        Raises:
            MusicGenerationError: If authentication fails.
        """
        try:
            creds, _ = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            return {
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
            }
        except Exception as e:
            logger.error(f"Failed to get authentication credentials: {e}")
            raise MusicGenerationError(f"Authentication failed: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    async def generate(
        self,
        brief: MusicBrief,
        output_dir: Path,
        seed: int | None = None,
    ) -> GeneratedMusic:
        """Generate music from a MusicBrief.

        Args:
            brief: The MusicBrief containing generation parameters.
            output_dir: Directory to save the generated audio file.
            seed: Optional seed for reproducible generation.

        Returns:
            GeneratedMusic with the local path to the saved WAV file.

        Raises:
            MusicGenerationError: If music generation fails after retries.
        """
        logger.info(f"Generating music with mood: {brief.mood.value}, genre: {brief.genre.value}")
        logger.debug(f"Music prompt: {brief.prompt}")

        # Build request body
        instance: dict[str, str | int] = {"prompt": brief.prompt}
        if brief.negative_prompt:
            instance["negative_prompt"] = brief.negative_prompt
        if seed is not None:
            instance["seed"] = seed

        request_body = {
            "instances": [instance],
            "parameters": {},
        }

        try:
            headers = self._get_auth_headers()
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=request_body,
                timeout=120,  # Music generation can take time
            )
            response.raise_for_status()
            result = response.json()

            # Extract audio from response
            predictions = result.get("predictions", [])
            if not predictions:
                raise MusicGenerationError(
                    "No predictions returned from Lyria 2. The response was empty."
                )

            # Get the first prediction's audio content
            prediction = predictions[0]
            audio_b64 = prediction.get("bytesBase64Encoded")
            if not audio_b64:
                raise MusicGenerationError(
                    "No audio content in Lyria 2 response. "
                    "The prediction did not contain bytesBase64Encoded data."
                )

            # Decode and save audio
            audio_bytes = base64.b64decode(audio_b64)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "background_music.wav"
            output_path.write_bytes(audio_bytes)

            logger.info(f"Saved background music to: {output_path}")

            return GeneratedMusic(
                file_path=str(output_path),
                duration_seconds=self.LYRIA_DURATION_SECONDS,
                prompt_used=brief.prompt,
                brief=brief,
            )

        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except Exception:
                error_detail = e.response.text
            logger.error(f"Lyria 2 API error: {error_detail}")
            raise MusicGenerationError(
                f"Lyria 2 API request failed: {e}. Details: {error_detail}"
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during music generation: {e}")
            raise MusicGenerationError(f"Network error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during music generation: {e}")
            raise MusicGenerationError(f"Music generation failed: {e}") from e
