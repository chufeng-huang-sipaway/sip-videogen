"""Tests for Pydantic models in sip-videogen."""

import pytest
from pydantic import ValidationError

from sip_studio.models.agent_outputs import (
    ContinuityIssue,
    ContinuitySupervisorOutput,
    ProductionDesignerOutput,
    ScreenwriterOutput,
    ShowrunnerOutput,
)
from sip_studio.models.aspect_ratio import (
    DEFAULT_ASPECT_RATIO,
    PROVIDER_SUPPORTED_RATIOS,
    AspectRatio,
    get_supported_ratio,
    parse_ratio,
    validate_aspect_ratio,
)
from sip_studio.models.assets import AssetType, GeneratedAsset, ProductionPackage
from sip_studio.models.script import (
    VALID_CLIP_PATTERNS,
    ElementType,
    SceneAction,
    SharedElement,
    SubShot,
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

    def test_create_valid_shared_element(self, sample_shared_element: SharedElement) -> None:
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


class TestClipPatterns:
    """Tests for clip pattern validation."""

    def test_valid_single_shot_pattern(self) -> None:
        """Test valid [8] pattern with no sub_shots."""
        scene = SceneAction(
            scene_number=1,
            clip_pattern=[8],
            setting_description="Test setting",
            action_description="Test action",
        )
        assert scene.clip_pattern == [8]
        assert scene.sub_shots == []

    def test_valid_multi_shot_pattern_with_sub_shots(self) -> None:
        """Test valid [4, 4] pattern with matching sub_shots."""
        scene = SceneAction(
            scene_number=1,
            clip_pattern=[4, 4],
            setting_description="Test setting",
            action_description="Test action",
            sub_shots=[
                SubShot(
                    start_second=0,
                    end_second=4,
                    camera_direction="Wide shot",
                    action_description="First action",
                ),
                SubShot(
                    start_second=4,
                    end_second=8,
                    camera_direction="Close-up",
                    action_description="Second action",
                ),
            ],
        )
        assert scene.clip_pattern == [4, 4]
        assert len(scene.sub_shots) == 2

    def test_valid_four_quick_pattern(self) -> None:
        """Test valid [2, 2, 2, 2] pattern with matching sub_shots."""
        scene = SceneAction(
            scene_number=1,
            clip_pattern=[2, 2, 2, 2],
            setting_description="Test setting",
            action_description="Test action",
            sub_shots=[
                SubShot(
                    start_second=0,
                    end_second=2,
                    camera_direction="Wide",
                    action_description="Shot 1",
                ),
                SubShot(
                    start_second=2,
                    end_second=4,
                    camera_direction="Medium",
                    action_description="Shot 2",
                ),
                SubShot(
                    start_second=4,
                    end_second=6,
                    camera_direction="Close-up",
                    action_description="Shot 3",
                ),
                SubShot(
                    start_second=6,
                    end_second=8,
                    camera_direction="Wide",
                    action_description="Shot 4",
                ),
            ],
        )
        assert scene.clip_pattern == [2, 2, 2, 2]
        assert len(scene.sub_shots) == 4

    def test_invalid_pattern_rejected(self) -> None:
        """Test invalid pattern [3, 5] raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SceneAction(
                scene_number=1,
                clip_pattern=[3, 5],  # Invalid - not in VALID_CLIP_PATTERNS
                setting_description="Test",
                action_description="Test",
            )
        assert "Invalid clip pattern" in str(exc_info.value)

    def test_pattern_not_summing_to_eight_rejected(self) -> None:
        """Test pattern [4, 2] (sums to 6) raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SceneAction(
                scene_number=1,
                clip_pattern=[4, 2],  # Invalid - sums to 6, not 8
                setting_description="Test",
                action_description="Test",
            )
        assert "Invalid clip pattern" in str(exc_info.value)

    def test_sub_shot_count_mismatch_rejected(self) -> None:
        """Test sub_shot count mismatch raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SceneAction(
                scene_number=1,
                clip_pattern=[4, 4],  # Expects 2 sub_shots
                setting_description="Test",
                action_description="Test",
                sub_shots=[
                    SubShot(
                        start_second=0,
                        end_second=8,
                        camera_direction="Wide",
                        action_description="Only one shot",
                    ),
                ],
            )
        assert "Number of sub_shots" in str(exc_info.value)

    def test_sub_shot_duration_mismatch_rejected(self) -> None:
        """Test sub_shot duration mismatch raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SceneAction(
                scene_number=1,
                clip_pattern=[4, 4],
                setting_description="Test",
                action_description="Test",
                sub_shots=[
                    SubShot(
                        start_second=0,
                        end_second=2,  # 2s instead of 4s
                        camera_direction="Wide",
                        action_description="Too short",
                    ),
                    SubShot(
                        start_second=2,
                        end_second=8,  # 6s instead of 4s
                        camera_direction="Close",
                        action_description="Too long",
                    ),
                ],
            )
        assert "duration" in str(exc_info.value).lower()

    def test_sub_shot_gap_rejected(self) -> None:
        """Test non-contiguous sub_shots raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SceneAction(
                scene_number=1,
                clip_pattern=[4, 4],
                setting_description="Test",
                action_description="Test",
                sub_shots=[
                    SubShot(
                        start_second=0,
                        end_second=4,
                        camera_direction="Wide",
                        action_description="First shot",
                    ),
                    SubShot(
                        start_second=5,  # Gap - should be 4
                        end_second=8,  # Duration is only 3s
                        camera_direction="Close",
                        action_description="Second shot",
                    ),
                ],
            )
        # Should fail on either start mismatch or duration mismatch
        error_str = str(exc_info.value).lower()
        assert "start" in error_str or "duration" in error_str

    def test_all_valid_patterns_accepted(self) -> None:
        """Test all valid patterns from VALID_CLIP_PATTERNS are accepted."""
        for pattern in VALID_CLIP_PATTERNS:
            # Build matching sub_shots for multi-shot patterns
            sub_shots = []
            if len(pattern) > 1:
                current = 0
                for duration in pattern:
                    sub_shots.append(
                        SubShot(
                            start_second=current,
                            end_second=current + duration,
                            camera_direction="Test camera",
                            action_description="Test action",
                        )
                    )
                    current += duration

            scene = SceneAction(
                scene_number=1,
                clip_pattern=list(pattern),
                setting_description="Test",
                action_description="Test",
                sub_shots=sub_shots,
            )
            assert tuple(scene.clip_pattern) == pattern

    def test_default_clip_pattern(self) -> None:
        """Test default clip_pattern is [8]."""
        scene = SceneAction(
            scene_number=1,
            setting_description="Test",
            action_description="Test",
        )
        assert scene.clip_pattern == [8]

    def test_multi_shot_pattern_without_sub_shots_is_valid(self) -> None:
        """Test multi-shot pattern without sub_shots is valid (generator warns)."""
        # The model validation allows empty sub_shots even for multi-shot patterns
        # because the screenwriter might set pattern first, then add sub_shots
        # The video generator has a safety check that falls back to standard prompt
        scene = SceneAction(
            scene_number=1,
            clip_pattern=[4, 4],
            setting_description="Test",
            action_description="Test",
            sub_shots=[],  # Empty is allowed - generator will warn and fallback
        )
        assert scene.clip_pattern == [4, 4]
        assert scene.sub_shots == []


class TestVideoScript:
    """Tests for VideoScript model."""

    def test_create_valid_video_script(self, sample_video_script: VideoScript) -> None:
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

    def test_get_element_by_id_found(self, sample_video_script: VideoScript) -> None:
        """Test get_element_by_id returns correct element."""
        element = sample_video_script.get_element_by_id("char_protagonist")
        assert element is not None
        assert element.name == "Space Cat"

    def test_get_element_by_id_not_found(self, sample_video_script: VideoScript) -> None:
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

    def test_get_elements_for_nonexistent_scene(self, sample_video_script: VideoScript) -> None:
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

    def test_create_video_clip_asset(self, sample_video_clip_asset: GeneratedAsset) -> None:
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

    def test_create_production_package(self, sample_production_package: ProductionPackage) -> None:
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
        asset = sample_production_package.get_reference_image_for_element("char_protagonist")
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

    def test_is_complete_true(self, sample_production_package: ProductionPackage) -> None:
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

    def test_is_complete_false_missing_video_clips(self, sample_video_script: VideoScript) -> None:
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

    def test_screenwriter_output_without_notes(self, sample_scene_action: SceneAction) -> None:
        """Test ScreenwriterOutput without narrative notes."""
        output = ScreenwriterOutput(scenes=[sample_scene_action])
        assert output.narrative_notes is None

    def test_production_designer_output(self, sample_shared_element: SharedElement) -> None:
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

    def test_continuity_supervisor_output(self, sample_video_script: VideoScript) -> None:
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

    def test_showrunner_output_not_ready(self, sample_video_script: VideoScript) -> None:
        """Test ShowrunnerOutput with production_ready=False."""
        output = ShowrunnerOutput(
            script=sample_video_script,
            production_ready=False,
        )
        assert output.production_ready is False
        assert output.creative_brief is None


class TestAspectRatio:
    """Tests for AspectRatio enum and utilities."""

    def test_aspect_ratio_enum_values(self) -> None:
        """Test AspectRatio enum has expected values."""
        assert AspectRatio.SQUARE.value == "1:1"
        assert AspectRatio.LANDSCAPE_16_9.value == "16:9"
        assert AspectRatio.PORTRAIT_9_16.value == "9:16"
        assert AspectRatio.CLASSIC_4_3.value == "4:3"
        assert AspectRatio.PORTRAIT_CLASSIC_3_4.value == "3:4"
        assert AspectRatio.PHOTO_3_2.value == "3:2"
        assert AspectRatio.PORTRAIT_PHOTO_2_3.value == "2:3"
        assert AspectRatio.PORTRAIT_4_5.value == "4:5"
        assert AspectRatio.LANDSCAPE_5_4.value == "5:4"

    def test_default_aspect_ratio(self) -> None:
        """Test DEFAULT_ASPECT_RATIO is LANDSCAPE_16_9."""
        assert DEFAULT_ASPECT_RATIO == AspectRatio.LANDSCAPE_16_9

    def test_parse_ratio_valid(self) -> None:
        """Test parse_ratio with valid inputs."""
        assert parse_ratio("16:9") == (16, 9)
        assert parse_ratio("9:16") == (9, 16)
        assert parse_ratio("1:1") == (1, 1)
        assert parse_ratio("4:3") == (4, 3)

    def test_parse_ratio_invalid(self) -> None:
        """Test parse_ratio raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            parse_ratio("invalid")
        with pytest.raises(ValueError):
            parse_ratio("16-9")
        with pytest.raises(ValueError):
            parse_ratio("")

    def test_validate_aspect_ratio_valid(self) -> None:
        """Test validate_aspect_ratio with valid ratio strings."""
        assert validate_aspect_ratio("1:1") == AspectRatio.SQUARE
        assert validate_aspect_ratio("16:9") == AspectRatio.LANDSCAPE_16_9
        assert validate_aspect_ratio("9:16") == AspectRatio.PORTRAIT_9_16
        assert validate_aspect_ratio("4:3") == AspectRatio.CLASSIC_4_3
        assert validate_aspect_ratio("3:4") == AspectRatio.PORTRAIT_CLASSIC_3_4
        assert validate_aspect_ratio("3:2") == AspectRatio.PHOTO_3_2
        assert validate_aspect_ratio("2:3") == AspectRatio.PORTRAIT_PHOTO_2_3
        assert validate_aspect_ratio("4:5") == AspectRatio.PORTRAIT_4_5
        assert validate_aspect_ratio("5:4") == AspectRatio.LANDSCAPE_5_4

    def test_validate_aspect_ratio_none(self) -> None:
        """Test validate_aspect_ratio returns default for None."""
        assert validate_aspect_ratio(None) == AspectRatio.LANDSCAPE_16_9

    def test_validate_aspect_ratio_invalid(self) -> None:
        """Test validate_aspect_ratio returns default for invalid inputs."""
        assert validate_aspect_ratio("invalid") == AspectRatio.LANDSCAPE_16_9
        assert validate_aspect_ratio("2:1") == AspectRatio.LANDSCAPE_16_9
        assert validate_aspect_ratio("") == AspectRatio.LANDSCAPE_16_9

    def test_provider_supported_ratios_defined(self) -> None:
        """Test all providers have supported ratios defined."""
        assert "veo" in PROVIDER_SUPPORTED_RATIOS
        assert "kling" in PROVIDER_SUPPORTED_RATIOS
        assert "sora" in PROVIDER_SUPPORTED_RATIOS

    def test_get_supported_ratio_exact_match(self) -> None:
        """Test get_supported_ratio returns exact match when supported."""
        # VEO only supports 16:9 and 9:16
        ratio, fallback = get_supported_ratio(AspectRatio.LANDSCAPE_16_9, "veo")
        assert ratio == AspectRatio.LANDSCAPE_16_9
        assert fallback is False
        ratio, fallback = get_supported_ratio(AspectRatio.PORTRAIT_9_16, "veo")
        assert ratio == AspectRatio.PORTRAIT_9_16
        assert fallback is False

    def test_get_supported_ratio_fallback_portrait(self) -> None:
        """Test portrait ratio fallback to 9:16."""
        # Sora doesn't support 3:4, should fallback to 9:16
        ratio, fallback = get_supported_ratio(AspectRatio.PORTRAIT_CLASSIC_3_4, "sora")
        assert ratio == AspectRatio.PORTRAIT_9_16
        assert fallback is True

    def test_get_supported_ratio_fallback_landscape(self) -> None:
        """Test landscape ratio fallback to 16:9."""
        # Sora doesn't support 4:3, should fallback to 16:9
        ratio, fallback = get_supported_ratio(AspectRatio.CLASSIC_4_3, "sora")
        assert ratio == AspectRatio.LANDSCAPE_16_9
        assert fallback is True

    def test_get_supported_ratio_fallback_square(self) -> None:
        """Test square ratio fallback when unsupported."""
        # Sora doesn't support 1:1, should fallback to 16:9 (first supported)
        ratio, fallback = get_supported_ratio(AspectRatio.SQUARE, "sora")
        assert ratio == AspectRatio.LANDSCAPE_16_9
        assert fallback is True

    def test_get_supported_ratio_unknown_provider(self) -> None:
        """Test unknown provider assumes all ratios supported."""
        ratio, fallback = get_supported_ratio(AspectRatio.CLASSIC_4_3, "unknown_provider")
        assert ratio == AspectRatio.CLASSIC_4_3
        assert fallback is False

    def test_kling_supported_ratios(self) -> None:
        """Test Kling supports expected ratios."""
        for r in ["1:1", "16:9", "9:16"]:
            ar = AspectRatio(r)
            ratio, fallback = get_supported_ratio(ar, "kling")
            assert ratio == ar
            assert fallback is False
        # Kling doesn't support 4:3 or 3:4
        ratio, fallback = get_supported_ratio(AspectRatio.CLASSIC_4_3, "kling")
        assert ratio == AspectRatio.LANDSCAPE_16_9
        assert fallback is True

    def test_veo_fallback_for_unsupported_ratios(self) -> None:
        """Test VEO falls back for unsupported ratios (only 16:9/9:16 supported)."""
        # Non-standard ratios should fall back
        ratio, fallback = get_supported_ratio(AspectRatio.LANDSCAPE_5_4, "veo")
        assert ratio == AspectRatio.LANDSCAPE_16_9
        assert fallback is True
        ratio, fallback = get_supported_ratio(AspectRatio.PORTRAIT_4_5, "veo")
        assert ratio == AspectRatio.PORTRAIT_9_16
        assert fallback is True

    def test_non_standard_fallback_on_kling(self) -> None:
        """Test 5:4 and 4:5 fallback on Kling."""
        # 5:4 (landscape) should fallback to 16:9
        ratio, fallback = get_supported_ratio(AspectRatio.LANDSCAPE_5_4, "kling")
        assert ratio == AspectRatio.LANDSCAPE_16_9
        assert fallback is True
        # 4:5 (portrait) should fallback to 9:16
        ratio, fallback = get_supported_ratio(AspectRatio.PORTRAIT_4_5, "kling")
        assert ratio == AspectRatio.PORTRAIT_9_16
        assert fallback is True

    def test_photo_fallback_on_sora(self) -> None:
        """Test 3:2 and 2:3 fallback on Sora."""
        # 3:2 (landscape) should fallback to 16:9
        ratio, fallback = get_supported_ratio(AspectRatio.PHOTO_3_2, "sora")
        assert ratio == AspectRatio.LANDSCAPE_16_9
        assert fallback is True
        # 2:3 (portrait) should fallback to 9:16
        ratio, fallback = get_supported_ratio(AspectRatio.PORTRAIT_PHOTO_2_3, "sora")
        assert ratio == AspectRatio.PORTRAIT_9_16
        assert fallback is True
