"""User preferences management for sip-videogen.

This module handles persistent user preferences stored in
~/.sip-videogen/config.json, allowing users to configure
default video providers and provider-specific settings.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from sip_videogen.generators.base import VideoProvider
from sip_videogen.utils.file_utils import write_atomically

logger = logging.getLogger(__name__)


class KlingPreferences(BaseModel):
    """Kling-specific user preferences."""

    model_version: str = Field(
        default="2.6",
        description=(
            "Kling model version: 1.5, 1.6, 2.0, 2.1, 2.5-turbo, 2.6 "
            "(aliases: 2.5, v2.5-turbo, v2.5, v2.6)"
        ),
    )
    mode: str = Field(
        default="std",
        description="Generation mode: 'std' (standard, faster) or 'pro' (higher quality)",
    )


class SoraPreferences(BaseModel):
    """Sora-specific user preferences."""

    model: str = Field(
        default="sora-2",
        description="Sora model: 'sora-2' (faster, cheaper) or 'sora-2-pro' (higher quality)",
    )
    resolution: str = Field(
        default="1080p",
        description="Video resolution: '720p' (1280x720) or '1080p' (1920x1080)",
    )


class UserPreferences(BaseModel):
    """User preferences stored in ~/.sip-videogen/config.json."""

    # Brand Studio also stores API keys and other settings in the same config file.
    # We must tolerate extra keys on load and preserve them on save.
    model_config = ConfigDict(extra="ignore")

    default_video_provider: VideoProvider = Field(
        default=VideoProvider.VEO,
        description="Default video generation provider",
    )
    kling: KlingPreferences = Field(
        default_factory=KlingPreferences,
        description="Kling-specific preferences",
    )
    sora: SoraPreferences = Field(
        default_factory=SoraPreferences,
        description="Sora-specific preferences",
    )

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the config directory path."""
        return Path.home() / ".sip-videogen"

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the full path to the config file."""
        return cls.get_config_dir() / "config.json"

    @classmethod
    def load(cls) -> UserPreferences:
        """Load preferences from disk, or return defaults if not found.

        Returns:
            UserPreferences instance with loaded or default values.
        """
        config_path = cls.get_config_path()

        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                prefs = cls.model_validate(data)
                logger.debug("Loaded user preferences from %s", config_path)
                return prefs
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON in config file: %s", e)
            except Exception as e:
                logger.warning("Failed to load preferences: %s", e)

        logger.debug("Using default preferences")
        return cls()

    def save(self) -> None:
        """Save preferences to disk.

        Creates the config directory if it doesn't exist.
        """
        config_path = self.get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Merge into existing config to avoid overwriting Brand Studio settings
        # (e.g., api_keys, update preferences) stored in the same file.
        existing: dict = {}
        if config_path.exists():
            try:
                raw = json.loads(config_path.read_text())
                if isinstance(raw, dict):
                    existing = raw
            except json.JSONDecodeError:
                existing = {}

        merged = dict(existing)
        merged.update(self.model_dump(mode="json"))
        # Config file may contain API keys; ensure restrictive permissions.
        write_atomically(config_path, json.dumps(merged, indent=2), mode=0o600)
        logger.info("Saved user preferences to %s", config_path)

    @classmethod
    def reset(cls) -> UserPreferences:
        """Reset preferences to defaults and save.

        Returns:
            Fresh UserPreferences instance with default values.
        """
        prefs = cls()
        prefs.save()
        logger.info("Reset user preferences to defaults")
        return prefs

    @classmethod
    def delete(cls) -> bool:
        """Delete the config file if it exists.

        Returns:
            True if file was deleted, False if it didn't exist.
        """
        config_path = cls.get_config_path()
        if config_path.exists():
            config_path.unlink()
            logger.info("Deleted config file: %s", config_path)
            return True
        return False
