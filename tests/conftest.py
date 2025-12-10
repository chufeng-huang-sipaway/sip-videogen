"""Pytest configuration and shared fixtures for sip-videogen tests."""

import os
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from sip_videogen.models.assets import AssetType, GeneratedAsset, ProductionPackage
from sip_videogen.models.music import MusicBrief, MusicGenre, MusicMood
from sip_videogen.models.script import (
    ElementType,
    SceneAction,
    SharedElement,
    VideoScript,
)


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def mock_env_vars() -> Generator[None, None, None]:
    """Mock environment variables for testing."""
    env_vars = {
        "OPENAI_API_KEY": "test-openai-key",
        "GEMINI_API_KEY": "test-gemini-key",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "SIP_GCS_BUCKET_NAME": "test-bucket",
        "SIP_OUTPUT_DIR": "/tmp/sip-test-output",
        "SIP_DEFAULT_SCENES": "3",
        "SIP_VIDEO_DURATION": "6",
        "SIP_LOG_LEVEL": "WARNING",
    }
    with patch.dict(os.environ, env_vars):
        # Clear cached settings
        from sip_videogen.config.settings import get_settings

        get_settings.cache_clear()
        yield
        get_settings.cache_clear()


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


# ============================================================================
# Model Fixtures
# ============================================================================


@pytest.fixture
def sample_shared_element() -> SharedElement:
    """Create a sample SharedElement for testing."""
    return SharedElement(
        id="char_protagonist",
        element_type=ElementType.CHARACTER,
        name="Space Cat",
        visual_description="An orange tabby cat wearing a white spacesuit with a clear helmet.",
        appears_in_scenes=[1, 2, 3],
    )


@pytest.fixture
def sample_environment_element() -> SharedElement:
    """Create a sample environment SharedElement."""
    return SharedElement(
        id="env_mars_surface",
        element_type=ElementType.ENVIRONMENT,
        name="Mars Surface",
        visual_description="Red dusty Martian landscape with distant mountains and pink sky.",
        appears_in_scenes=[2, 3],
    )


@pytest.fixture
def sample_prop_element() -> SharedElement:
    """Create a sample prop SharedElement."""
    return SharedElement(
        id="prop_rover",
        element_type=ElementType.PROP,
        name="Mars Rover",
        visual_description="A small wheeled robot with solar panels and a camera arm.",
        appears_in_scenes=[3],
    )


@pytest.fixture
def sample_scene_action() -> SceneAction:
    """Create a sample SceneAction for testing."""
    return SceneAction(
        scene_number=1,
        duration_seconds=6,
        setting_description="Inside a spacecraft cockpit",
        action_description="A cat astronaut sits at the controls, looking at a view screen showing Mars.",
        dialogue="Mission Control, we're approaching Mars orbit.",
        camera_direction="Close-up on cat's face, then pan to view screen",
        shared_element_ids=["char_protagonist"],
    )


@pytest.fixture
def sample_music_brief() -> MusicBrief:
    """Create a sample MusicBrief for testing."""
    return MusicBrief(
        prompt="Epic orchestral music with sweeping strings and brass, adventurous and inspiring mood, moderate tempo around 100 BPM, suitable for space exploration scenes",
        negative_prompt="vocals, singing, lyrics, heavy metal",
        mood=MusicMood.DRAMATIC,
        genre=MusicGenre.CINEMATIC,
        tempo="moderate 100 BPM",
        instruments=["strings", "brass", "percussion"],
        rationale="Cinematic orchestral music enhances the epic space adventure feel",
    )


@pytest.fixture
def sample_video_script(
    sample_shared_element: SharedElement,
    sample_environment_element: SharedElement,
    sample_scene_action: SceneAction,
    sample_music_brief: MusicBrief,
) -> VideoScript:
    """Create a sample VideoScript for testing."""
    scene2 = SceneAction(
        scene_number=2,
        duration_seconds=8,
        setting_description="Mars surface near the landing site",
        action_description="The cat astronaut steps out of the lander onto Mars.",
        camera_direction="Wide shot of the Martian landscape",
        shared_element_ids=["char_protagonist", "env_mars_surface"],
    )
    scene3 = SceneAction(
        scene_number=3,
        duration_seconds=6,
        setting_description="Mars surface exploration",
        action_description="The cat astronaut discovers an ancient alien artifact.",
        shared_element_ids=["char_protagonist", "env_mars_surface"],
    )

    return VideoScript(
        title="Space Cat: Mars Mission",
        logline="A brave cat astronaut embarks on humanity's first mission to Mars.",
        tone="adventurous and awe-inspiring",
        shared_elements=[sample_shared_element, sample_environment_element],
        scenes=[sample_scene_action, scene2, scene3],
        music_brief=sample_music_brief,
    )


@pytest.fixture
def minimal_video_script(sample_music_brief: MusicBrief) -> VideoScript:
    """Create a minimal VideoScript for basic testing."""
    return VideoScript(
        title="Test Video",
        logline="A test video",
        tone="neutral",
        shared_elements=[],
        scenes=[
            SceneAction(
                scene_number=1,
                duration_seconds=4,
                setting_description="Test setting",
                action_description="Test action",
            )
        ],
        music_brief=sample_music_brief,
    )


# ============================================================================
# Asset Fixtures
# ============================================================================


@pytest.fixture
def sample_reference_image_asset() -> GeneratedAsset:
    """Create a sample reference image asset."""
    return GeneratedAsset(
        asset_type=AssetType.REFERENCE_IMAGE,
        element_id="char_protagonist",
        local_path="/tmp/test/char_protagonist.png",
        gcs_uri="gs://test-bucket/sip-videogen/test/char_protagonist.png",
    )


@pytest.fixture
def sample_video_clip_asset() -> GeneratedAsset:
    """Create a sample video clip asset."""
    return GeneratedAsset(
        asset_type=AssetType.VIDEO_CLIP,
        scene_number=1,
        local_path="/tmp/test/scene_001.mp4",
        gcs_uri="gs://test-bucket/sip-videogen/test/scene_001.mp4",
    )


@pytest.fixture
def sample_production_package(
    sample_video_script: VideoScript,
    sample_reference_image_asset: GeneratedAsset,
    sample_video_clip_asset: GeneratedAsset,
) -> ProductionPackage:
    """Create a sample ProductionPackage for testing."""
    # Create additional assets to match the script
    ref_image_2 = GeneratedAsset(
        asset_type=AssetType.REFERENCE_IMAGE,
        element_id="env_mars_surface",
        local_path="/tmp/test/env_mars_surface.png",
        gcs_uri="gs://test-bucket/sip-videogen/test/env_mars_surface.png",
    )

    clip_2 = GeneratedAsset(
        asset_type=AssetType.VIDEO_CLIP,
        scene_number=2,
        local_path="/tmp/test/scene_002.mp4",
        gcs_uri="gs://test-bucket/sip-videogen/test/scene_002.mp4",
    )

    clip_3 = GeneratedAsset(
        asset_type=AssetType.VIDEO_CLIP,
        scene_number=3,
        local_path="/tmp/test/scene_003.mp4",
        gcs_uri="gs://test-bucket/sip-videogen/test/scene_003.mp4",
    )

    return ProductionPackage(
        script=sample_video_script,
        reference_images=[sample_reference_image_asset, ref_image_2],
        video_clips=[sample_video_clip_asset, clip_2, clip_3],
        final_video_path="/tmp/test/final.mp4",
    )


# ============================================================================
# Mock Fixtures for External Services
# ============================================================================


@pytest.fixture
def mock_genai_client() -> MagicMock:
    """Create a mock Google GenAI client."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def mock_gcs_client() -> MagicMock:
    """Create a mock Google Cloud Storage client."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    return mock_client
