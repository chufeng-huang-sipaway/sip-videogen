"""Factory for creating video generators.

This module provides a factory pattern for creating the appropriate
video generator based on user preferences or explicit provider selection.
"""

from __future__ import annotations

import logging

from sip_videogen.config.settings import get_settings
from sip_videogen.config.user_preferences import UserPreferences
from sip_videogen.generators.base import BaseVideoGenerator, VideoProvider

logger = logging.getLogger(__name__)


class VideoGeneratorFactory:
    """Factory for creating video generators based on provider selection."""

    @staticmethod
    def create(
        provider: VideoProvider | None = None,
    ) -> BaseVideoGenerator:
        """Create a video generator instance.

        Args:
            provider: Specific provider to use. If None, uses user preference.

        Returns:
            Configured video generator instance (VEO or Kling).

        Raises:
            ValueError: If Kling is requested but credentials are not configured.
            ValueError: If an unknown provider is specified.
        """
        settings = get_settings()
        prefs = UserPreferences.load()

        # Use specified provider or fall back to user preference
        actual_provider = provider or prefs.default_video_provider

        logger.info("Creating video generator for provider: %s", actual_provider.value)

        if actual_provider == VideoProvider.VEO:
            return VideoGeneratorFactory._create_veo_generator(settings)

        elif actual_provider == VideoProvider.KLING:
            return VideoGeneratorFactory._create_kling_generator(settings, prefs)

        else:
            raise ValueError(f"Unknown video provider: {actual_provider}")

    @staticmethod
    def _create_veo_generator(settings) -> BaseVideoGenerator:
        """Create a VEO video generator.

        Args:
            settings: Application settings.

        Returns:
            VEOVideoGenerator instance.
        """
        from sip_videogen.generators.video_generator import VEOVideoGenerator

        return VEOVideoGenerator(
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )

    @staticmethod
    def _create_kling_generator(settings, prefs: UserPreferences) -> BaseVideoGenerator:
        """Create a Kling video generator.

        Args:
            settings: Application settings.
            prefs: User preferences with Kling configuration.

        Returns:
            KlingVideoGenerator instance.

        Raises:
            ValueError: If Kling credentials are not configured.
        """
        if not settings.kling_access_key or not settings.kling_secret_key:
            raise ValueError(
                "Kling API credentials not configured.\n"
                "Set KLING_ACCESS_KEY and KLING_SECRET_KEY in your .env file.\n"
                "Get credentials from: https://app.klingai.com/global/dev/api-key"
            )

        from sip_videogen.generators.kling_generator import KlingConfig, KlingVideoGenerator

        config = KlingConfig(
            model_version=prefs.kling.model_version,
            mode=prefs.kling.mode,
        )

        return KlingVideoGenerator(
            access_key=settings.kling_access_key,
            secret_key=settings.kling_secret_key,
            config=config,
        )

    @staticmethod
    def get_available_providers() -> list[VideoProvider]:
        """Get list of providers that are properly configured.

        Returns:
            List of available VideoProvider values.
        """
        settings = get_settings()
        available = []

        # VEO requires Google Cloud configuration
        config_status = settings.is_configured()
        if config_status.get("google_cloud_project") and config_status.get("sip_gcs_bucket_name"):
            available.append(VideoProvider.VEO)

        # Kling requires access key and secret key
        if config_status.get("kling_api"):
            available.append(VideoProvider.KLING)

        return available

    @staticmethod
    def is_provider_available(provider: VideoProvider) -> bool:
        """Check if a specific provider is properly configured.

        Args:
            provider: The provider to check.

        Returns:
            True if the provider is configured and available.
        """
        return provider in VideoGeneratorFactory.get_available_providers()
