"""Pydantic data models for scripts, assets, and agent outputs."""

from sip_studio.models.agent_outputs import (
    ContinuityIssue,
    ContinuitySupervisorOutput,
    DirectorsPitch,
    ProductionDesignerOutput,
    ScreenwriterOutput,
    ShowrunnerOutput,
)
from sip_studio.models.aspect_ratio import (
    DEFAULT_ASPECT_RATIO,
    PROVIDER_SUPPORTED_RATIOS,
    SORA_SIZE_MAP,
    AspectRatio,
    get_supported_ratio,
    parse_ratio,
    validate_aspect_ratio,
)
from sip_studio.models.assets import (
    AssetType,
    GeneratedAsset,
    ProductionPackage,
)
from sip_studio.models.image_review import (
    ImageGenerationAttempt,
    ImageGenerationResult,
    ImageReviewResult,
    ReviewDecision,
)
from sip_studio.models.music import (
    GeneratedMusic,
    MusicBrief,
    MusicGenre,
    MusicMood,
)
from sip_studio.models.script import (
    ElementType,
    SceneAction,
    SharedElement,
    VideoScript,
)

__all__ = [
    # Aspect ratio models
    "AspectRatio",
    "DEFAULT_ASPECT_RATIO",
    "PROVIDER_SUPPORTED_RATIOS",
    "SORA_SIZE_MAP",
    "get_supported_ratio",
    "parse_ratio",
    "validate_aspect_ratio",
    # Script models
    "ElementType",
    "SceneAction",
    "SharedElement",
    "VideoScript",
    # Asset models
    "AssetType",
    "GeneratedAsset",
    "ProductionPackage",
    # Image review models
    "ImageGenerationAttempt",
    "ImageGenerationResult",
    "ImageReviewResult",
    "ReviewDecision",
    # Music models
    "GeneratedMusic",
    "MusicBrief",
    "MusicGenre",
    "MusicMood",
    # Agent output models
    "ContinuityIssue",
    "ContinuitySupervisorOutput",
    "DirectorsPitch",
    "ProductionDesignerOutput",
    "ScreenwriterOutput",
    "ShowrunnerOutput",
]
