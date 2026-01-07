"""Image, video, and music generation services."""

from sip_studio.generators.base import (
    BaseVideoGenerator,
    PromptSafetyError,
    ServiceAgentNotReadyError,
    VideoGenerationError,
    VideoProvider,
)
from sip_studio.generators.factory import VideoGeneratorFactory
from sip_studio.generators.image_generator import (
    ImageGenerationError,
    ImageGenerator,
)
from sip_studio.generators.kling_generator import (
    KlingConfig,
    KlingGenerationResult,
    KlingVideoGenerator,
)
from sip_studio.generators.music_generator import (
    MusicGenerationError,
    MusicGenerator,
)
from sip_studio.generators.sora_generator import (
    SoraConfig,
    SoraGenerationResult,
    SoraVideoGenerator,
)
from sip_studio.generators.video_generator import (
    VEOVideoGenerator,
    VideoGenerationResult,
)

# Backward compatibility alias
VideoGenerator = VEOVideoGenerator

__all__ = [
    # Base classes and exceptions
    "BaseVideoGenerator",
    "VideoGenerationError",
    "PromptSafetyError",
    "ServiceAgentNotReadyError",
    "VideoProvider",
    # Factory
    "VideoGeneratorFactory",
    # VEO (Google Vertex AI)
    "VEOVideoGenerator",
    "VideoGenerator",  # Backward compatibility alias
    "VideoGenerationResult",
    # Kling AI
    "KlingVideoGenerator",
    "KlingConfig",
    "KlingGenerationResult",
    # Sora (OpenAI)
    "SoraVideoGenerator",
    "SoraConfig",
    "SoraGenerationResult",
    # Image generation
    "ImageGenerationError",
    "ImageGenerator",
    # Music generation
    "MusicGenerationError",
    "MusicGenerator",
]
