"""Configuration and settings management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# User config directory
USER_CONFIG_DIR = Path.home() / ".sip-videogen"
USER_CONFIG_FILE = USER_CONFIG_DIR / ".env"


def _get_env_files() -> tuple[Path, ...]:
    """Get list of env files to load, in priority order.

    Priority (highest first):
    1. ~/.sip-videogen/.env (user config)
    2. ./.env (local project config)
    """
    files = []
    # Local .env first (lower priority, will be overridden)
    local_env = Path(".env")
    if local_env.exists():
        files.append(local_env)
    # User config second (higher priority)
    if USER_CONFIG_FILE.exists():
        files.append(USER_CONFIG_FILE)
    return tuple(files) if files else (".env",)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI API key for agent orchestration
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for agent orchestration",
    )

    # Google Gemini API key for image generation
    gemini_api_key: str = Field(
        ...,
        description="Google Gemini API key for image generation",
    )

    # Google Cloud Project configuration
    google_cloud_project: str = Field(
        ...,
        description="Google Cloud Project ID",
    )
    google_cloud_location: str = Field(
        default="us-central1",
        description="Google Cloud region for Vertex AI",
    )

    # GCS bucket for VEO video generation
    sip_gcs_bucket_name: str = Field(
        ...,
        description="GCS bucket name for VEO video generation",
    )

    # Google Cloud credentials JSON (base64 encoded service account key)
    # Alternative to running 'gcloud auth application-default login'
    google_cloud_credentials_json: str | None = Field(
        default=None,
        description="Base64-encoded service account JSON key for GCS authentication",
    )

    # Enable Vertex AI for VEO
    google_genai_use_vertexai: bool = Field(
        default=True,
        description="Enable Vertex AI for VEO video generation",
    )

    # Kling API credentials (optional, for Kling video generation)
    kling_access_key: str | None = Field(
        default=None,
        description="Kling API access key (optional)",
    )
    kling_secret_key: str | None = Field(
        default=None,
        description="Kling API secret key (optional)",
    )

    # Local output directory for generated assets
    sip_output_dir: Path = Field(
        default=Path("./output"),
        description="Local output directory for generated assets",
    )

    # Default number of scenes
    sip_default_scenes: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Default number of scenes (1-10)",
    )

    # Default video duration per scene in seconds
    sip_video_duration: Literal[4, 6, 8] = Field(
        default=6,
        description="Default video duration per scene (4, 6, or 8 seconds)",
    )

    # Logging level
    sip_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )

    # Background music settings
    sip_enable_background_music: bool = Field(
        default=True,
        description="Enable background music generation using Lyria 2",
    )
    sip_music_volume: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Background music volume (0.0-1.0)",
    )

    @field_validator("sip_output_dir", mode="before")
    @classmethod
    def validate_output_dir(cls, v: str | Path) -> Path:
        """Convert string to Path."""
        return Path(v) if isinstance(v, str) else v

    @field_validator("sip_video_duration", mode="before")
    @classmethod
    def validate_video_duration(cls, v: int | str) -> int:
        """Validate video duration is 4, 6, or 8 seconds."""
        duration = int(v) if isinstance(v, str) else v
        # VEO only supports 4, 6, or 8 seconds
        # Map 5 to 6 as a reasonable default
        if duration == 5:
            return 6
        if duration not in (4, 6, 8):
            raise ValueError(f"Video duration must be 4, 6, or 8 seconds, got {duration}")
        return duration

    def ensure_output_dir(self) -> Path:
        """Create output directory if it doesn't exist and return it."""
        self.sip_output_dir.mkdir(parents=True, exist_ok=True)
        return self.sip_output_dir

    def is_configured(self) -> dict[str, bool]:
        """Check which settings are properly configured.

        Note: google_cloud_credentials_json is NOT included here because
        it's optional - users can authenticate via ADC (gcloud login) instead.
        """
        return {
            "openai_api_key": bool(self.openai_api_key and self.openai_api_key != "sk-..."),
            "gemini_api_key": bool(self.gemini_api_key and self.gemini_api_key != "..."),
            "google_cloud_project": bool(
                self.google_cloud_project and self.google_cloud_project != "your-project-id"
            ),
            "sip_gcs_bucket_name": bool(
                self.sip_gcs_bucket_name and self.sip_gcs_bucket_name != "your-bucket-name"
            ),
            "kling_api": bool(self.kling_access_key and self.kling_secret_key),
        }

    def has_gcs_credentials(self) -> bool:
        """Check if GCS credentials are available (inline or via ADC)."""
        return bool(self.google_cloud_credentials_json)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    This function uses lru_cache to ensure settings are only loaded once
    from environment variables and .env file.

    Returns:
        Settings: The application settings instance.

    Raises:
        pydantic.ValidationError: If required settings are missing or invalid.
    """
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache.

    Useful for testing when you need to reload settings.
    """
    get_settings.cache_clear()
