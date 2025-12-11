"""Tests for Pydantic models in sip-videogen."""

import pytest
from pydantic import ValidationError

from sip_videogen.models.agent_outputs import (
    ContinuityIssue,
    ContinuitySupervisorOutput,
    ProductionDesignerOutput,
    ScreenwriterOutput,
    ShowrunnerOutput,
)
from sip_videogen.models.assets import AssetType, GeneratedAsset, ProductionPackage
from sip_videogen.models.music import MusicBrief
from sip_videogen.models.script import (
    ElementType,
    SceneAction,
    SharedElement,
    VideoScript,
)


class TestElementType:
    """Tests for ElementType enum."""

    def test_element_type_values(self) -> None:
        """Test that ElementType has expected values."""
        assert ElementType.CHARACTER.value == "character"
        assert ElementType.ENVIRONMENT.value == "environment"
        assert ElementType.PROP.value == "prop"

    def test_element_type_is_string(self) -> None:
        """Test that ElementType values are strings."""
        assert isinstance(ElementType.CHARACTER.value, str)
        # ElementType inherits from str, so .value gives the string
        assert ElementType.CHARACTER.value == "character"


class TestSharedElement:
    """Tests for SharedElement model."""

    def test_create_valid_shared_element(
        self, sample_shared_element: SharedElement
    ) -> None:
        """Test creating a valid SharedElement."""
        assert sample_shared_element.id == "char_protagonist"
        assert sample_shared_element.element_type == ElementType.CHARACTER
        assert sample_shared_element.name == "Space Cat"
        assert "spacesuit" in sample_shared_element.visual_description
        assert sample_shared_element.appears_in_scenes == [1, 2, 3]
        # Empty strings are the default (not None) for OpenAI structured output compatibility
        assert sample_shared_element.reference_image_path == ""
        assert sample_shared_element.reference_image_gcs_uri == ""

    def test_shared_element_with_paths(self) -> None:
        """Test SharedElement with reference image paths."""
        element = SharedElement(
            id="char_hero",
            element_type=ElementType.CHARACTER,
            name="Hero",
            visual_description="A brave hero",
            appears_in_scenes=[1],
            reference_image_path="/path/to/image.png",
            reference_image_gcs_uri="gs://bucket/image.png",
        )
        assert element.reference_image_path == "/path/to/image.png"
        assert element.reference_image_gcs_uri == "gs://bucket/image.png"

    def test_shared_element_missing_required_fields(self) -> None:
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            SharedElement(
                id="test",
                element_type=ElementType.CHARACTER,
                # missing name, visual_description, appears_in_scenes
            )

    def test_shared_element_empty_appears_in_scenes(self) -> None:
        """Test SharedElement can have empty appears_in_scenes list."""
        element = SharedElement(
            id="unused_element",
            element_type=ElementType.PROP,
            name="Unused Prop",
            visual_description="A prop that was cut from the script",
            appears_in_scenes=[],
        )
        assert element.appears_in_scenes == []


class TestSceneAction:
    """Tests for SceneAction model."""

    def test_create_valid_scene_action(self, sample_scene_action: SceneAction) -> None:
        """Test creating a valid SceneAction."""
        assert sample_scene_action.scene_number == 1
        assert sample_scene_action.duration_seconds == 6
        assert "spacecraft cockpit" in sample_scene_action.setting_description
        assert sample_scene_action.dialogue is not None
        assert sample_scene_action.camera_direction is not None
        assert "char_protagonist" in sample_scene_action.shared_element_ids

    def test_scene_action_defaults(self) -> None:
        """Test SceneAction default values."""
        scene = SceneAction(
            scene_number=1,
            setting_description="Test setting",
            action_description="Test action",
        )
        assert scene.duration_seconds == 8  # VEO forces 8s when using reference images (standard)
        # Empty strings are the default (not None) for OpenAI structured output compatibility
        assert scene.dialogue == ""
        assert scene.camera_direction == ""
        assert scene.shared_element_ids == []

    def test_scene_action_duration_validation(self) -> None:
        """Test duration validation (4-8 seconds)."""
        # Valid durations
        for duration in [4, 5, 6, 7, 8]:
            scene = SceneAction(
                scene_number=1,
                duration_seconds=duration,
                setting_description="Test",
                action_description="Test",
            )
            assert scene.duration_seconds == duration

        # Invalid duration - too short
        with pytest.raises(ValidationError):
            SceneAction(
                scene_number=1,
                duration_seconds=3,
                setting_description="Test",
                action_description="Test",
            )

        # Invalid duration - too long
        with pytest.raises(ValidationError):
            SceneAction(
                scene_number=1,
                duration_seconds=9,
                setting_description="Test",
                action_description="Test",
            )

    def test_scene_action_scene_number_validation(self) -> None:
        """Test scene number must be >= 1."""
        with pytest.raises(ValidationError):
            SceneAction(
                scene_number=0,
                setting_description="Test",
                action_description="Test",
            )


class TestVideoScript:
    """Tests for VideoScript model."""

    def test_create_valid_video_script(
        self, sample_video_script: VideoScript
    ) -> None:
        """Test creating a valid VideoScript."""
        assert sample_video_script.title == "Space Cat: Mars Mission"
        assert "cat astronaut" in sample_video_script.logline
        assert len(sample_video_script.scenes) == 3
        assert len(sample_video_script.shared_elements) == 2

    def test_total_duration_property(self, sample_video_script: VideoScript) -> None:
        """Test total_duration calculates sum of scene durations."""
        # Scene durations: 6 + 8 + 6 = 20
        assert sample_video_script.total_duration == 20

    def test_total_duration_empty_scenes(self, sample_music_brief) -> None:
        """Test total_duration with empty scenes list."""
        script = VideoScript(
            title="Empty",
            logline="Empty",
            tone="neutral",
            scenes=[],
            music_brief=sample_music_brief,
        )
        assert script.total_duration == 0

    def test_get_element_by_id_found(
        self, sample_video_script: VideoScript
    ) -> None:
        """Test get_element_by_id returns correct element."""
        element = sample_video_script.get_element_by_id("char_protagonist")
        assert element is not None
        assert element.name == "Space Cat"

    def test_get_element_by_id_not_found(
        self, sample_video_script: VideoScript
    ) -> None:
        """Test get_element_by_id returns None for unknown ID."""
        element = sample_video_script.get_element_by_id("nonexistent")
        assert element is None

    def test_get_elements_for_scene(self, sample_video_script: VideoScript) -> None:
        """Test get_elements_for_scene returns correct elements."""
        # Scene 1 should have character only
        elements_scene1 = sample_video_script.get_elements_for_scene(1)
        assert len(elements_scene1) == 1
        assert elements_scene1[0].id == "char_protagonist"

        # Scene 2 should have character and environment
        elements_scene2 = sample_video_script.get_elements_for_scene(2)
        assert len(elements_scene2) == 2

    def test_get_elements_for_nonexistent_scene(
        self, sample_video_script: VideoScript
    ) -> None:
        """Test get_elements_for_scene returns empty for nonexistent scene."""
        elements = sample_video_script.get_elements_for_scene(99)
        assert elements == []


class TestAssetType:
    """Tests for AssetType enum."""

    def test_asset_type_values(self) -> None:
        """Test AssetType enum values."""
        assert AssetType.REFERENCE_IMAGE.value == "reference_image"
        assert AssetType.VIDEO_CLIP.value == "video_clip"


class TestGeneratedAsset:
    """Tests for GeneratedAsset model."""

    def test_create_reference_image_asset(
        self, sample_reference_image_asset: GeneratedAsset
    ) -> None:
        """Test creating a reference image asset."""
        asset = sample_reference_image_asset
        assert asset.asset_type == AssetType.REFERENCE_IMAGE
        assert asset.element_id == "char_protagonist"
        assert asset.scene_number is None
        assert "char_protagonist.png" in asset.local_path
        assert asset.gcs_uri is not None

    def test_create_video_clip_asset(
        self, sample_video_clip_asset: GeneratedAsset
    ) -> None:
        """Test creating a video clip asset."""
        asset = sample_video_clip_asset
        assert asset.asset_type == AssetType.VIDEO_CLIP
        assert asset.element_id is None
        assert asset.scene_number == 1
        assert "scene_001.mp4" in asset.local_path

    def test_asset_without_gcs_uri(self) -> None:
        """Test asset can be created without GCS URI."""
        asset = GeneratedAsset(
            asset_type=AssetType.REFERENCE_IMAGE,
            element_id="test",
            local_path="/local/path.png",
        )
        assert asset.gcs_uri is None


class TestProductionPackage:
    """Tests for ProductionPackage model."""

    def test_create_production_package(
        self, sample_production_package: ProductionPackage
    ) -> None:
        """Test creating a ProductionPackage."""
        pkg = sample_production_package
        assert pkg.script.title == "Space Cat: Mars Mission"
        assert len(pkg.reference_images) == 2
        assert len(pkg.video_clips) == 3
        assert pkg.final_video_path == "/tmp/test/final.mp4"

    def test_get_reference_image_for_element_found(
        self, sample_production_package: ProductionPackage
    ) -> None:
        """Test finding reference image by element ID."""
        asset = sample_production_package.get_reference_image_for_element(
            "char_protagonist"
        )
        assert asset is not None
        assert asset.element_id == "char_protagonist"

    def test_get_reference_image_for_element_not_found(
        self, sample_production_package: ProductionPackage
    ) -> None:
        """Test get_reference_image_for_element returns None for unknown ID."""
        asset = sample_production_package.get_reference_image_for_element("unknown")
        assert asset is None

    def test_get_video_clip_for_scene_found(
        self, sample_production_package: ProductionPackage
    ) -> None:
        """Test finding video clip by scene number."""
        clip = sample_production_package.get_video_clip_for_scene(2)
        assert clip is not None
        assert clip.scene_number == 2

    def test_get_video_clip_for_scene_not_found(
        self, sample_production_package: ProductionPackage
    ) -> None:
        """Test get_video_clip_for_scene returns None for unknown scene."""
        clip = sample_production_package.get_video_clip_for_scene(99)
        assert clip is None

    def test_is_complete_true(
        self, sample_production_package: ProductionPackage
    ) -> None:
        """Test is_complete returns True when all assets are present."""
        assert sample_production_package.is_complete is True

    def test_is_complete_false_missing_reference_image(
        self, sample_video_script: VideoScript
    ) -> None:
        """Test is_complete returns False when missing reference images."""
        pkg = ProductionPackage(
            script=sample_video_script,
            reference_images=[],  # Missing images
            video_clips=[
                GeneratedAsset(
                    asset_type=AssetType.VIDEO_CLIP,
                    scene_number=i,
                    local_path=f"/tmp/scene_{i}.mp4",
                )
                for i in [1, 2, 3]
            ],
        )
        assert pkg.is_complete is False

    def test_is_complete_false_missing_video_clips(
        self, sample_video_script: VideoScript
    ) -> None:
        """Test is_complete returns False when missing video clips."""
        pkg = ProductionPackage(
            script=sample_video_script,
            reference_images=[
                GeneratedAsset(
                    asset_type=AssetType.REFERENCE_IMAGE,
                    element_id="char_protagonist",
                    local_path="/tmp/char.png",
                ),
                GeneratedAsset(
                    asset_type=AssetType.REFERENCE_IMAGE,
                    element_id="env_mars_surface",
                    local_path="/tmp/env.png",
                ),
            ],
            video_clips=[],  # Missing clips
        )
        assert pkg.is_complete is False


class TestAgentOutputs:
    """Tests for agent output models."""

    def test_screenwriter_output(self, sample_scene_action: SceneAction) -> None:
        """Test ScreenwriterOutput model."""
        output = ScreenwriterOutput(
            scenes=[sample_scene_action],
            narrative_notes="The story follows a classic hero's journey.",
        )
        assert len(output.scenes) == 1
        assert output.narrative_notes is not None

    def test_screenwriter_output_without_notes(
        self, sample_scene_action: SceneAction
    ) -> None:
        """Test ScreenwriterOutput without narrative notes."""
        output = ScreenwriterOutput(scenes=[sample_scene_action])
        assert output.narrative_notes is None

    def test_production_designer_output(
        self, sample_shared_element: SharedElement
    ) -> None:
        """Test ProductionDesignerOutput model."""
        output = ProductionDesignerOutput(
            shared_elements=[sample_shared_element],
            design_notes="Retro sci-fi aesthetic with warm colors.",
        )
        assert len(output.shared_elements) == 1
        assert output.design_notes is not None

    def test_continuity_issue(self) -> None:
        """Test ContinuityIssue model."""
        issue = ContinuityIssue(
            scene_number=2,
            element_id="char_protagonist",
            issue_description="Character costume color inconsistent",
            resolution="Updated description to specify white spacesuit",
        )
        assert issue.scene_number == 2
        assert issue.element_id == "char_protagonist"

    def test_continuity_supervisor_output(
        self, sample_video_script: VideoScript
    ) -> None:
        """Test ContinuitySupervisorOutput model."""
        issue = ContinuityIssue(
            scene_number=1,
            issue_description="Minor lighting inconsistency",
            resolution="Added lighting direction to prompt",
        )
        output = ContinuitySupervisorOutput(
            validated_script=sample_video_script,
            issues_found=[issue],
            optimization_notes="Added more specific visual descriptors",
        )
        assert output.validated_script == sample_video_script
        assert len(output.issues_found) == 1
        assert output.optimization_notes is not None

    def test_showrunner_output(self, sample_video_script: VideoScript) -> None:
        """Test ShowrunnerOutput model."""
        output = ShowrunnerOutput(
            script=sample_video_script,
            creative_brief="An inspiring space adventure for all ages.",
            production_ready=True,
        )
        assert output.script == sample_video_script
        assert output.production_ready is True

    def test_showrunner_output_not_ready(
        self, sample_video_script: VideoScript
    ) -> None:
        """Test ShowrunnerOutput with production_ready=False."""
        output = ShowrunnerOutput(
            script=sample_video_script,
            production_ready=False,
        )
        assert output.production_ready is False
        assert output.creative_brief is None
