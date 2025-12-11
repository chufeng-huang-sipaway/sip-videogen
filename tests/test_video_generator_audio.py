"""Tests for VEO audio prompt engineering in VideoGenerator.

These tests verify the audio instruction generation that excludes background music
while preserving ambient sounds and dialogue for external music overlay.
"""

from unittest.mock import patch

import pytest

from sip_videogen.generators import VideoGenerator
from sip_videogen.models.script import SceneAction


class TestAudioInstructionGeneration:
    """Tests for _build_audio_instruction method."""

    @pytest.fixture
    def generator(self):
        """Create a VideoGenerator with mocked client."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            return VideoGenerator(project="test", location="us-central1")

    def test_audio_instruction_with_dialogue(self, generator):
        """Test audio instruction includes character dialogue when present."""
        scene = SceneAction(
            scene_number=1,
            setting_description="An office room",
            action_description="Two people discuss a plan",
            dialogue="We need to act now",
        )
        instruction = generator._build_audio_instruction(scene)

        assert "character dialogue" in instruction
        assert "No background music" in instruction
        assert "no soundtrack" in instruction

    def test_audio_instruction_without_dialogue(self, generator):
        """Test audio instruction works without dialogue."""
        scene = SceneAction(
            scene_number=1,
            setting_description="A forest path",
            action_description="A deer walks through the trees",
        )
        instruction = generator._build_audio_instruction(scene)

        assert "character dialogue" not in instruction
        assert "No background music" in instruction

    def test_audio_instruction_minimal_scene(self, generator):
        """Test audio instruction with minimal scene info."""
        scene = SceneAction(
            scene_number=1,
            setting_description="",
            action_description="A moment passes",  # No action keywords
        )
        instruction = generator._build_audio_instruction(scene)

        # New format uses "Ambient: natural environmental sounds" for minimal scenes
        assert "Ambient: natural environmental sounds" in instruction
        assert "No background music" in instruction

    def test_audio_instruction_deduplicates_sounds(self, generator):
        """Test that duplicate sounds are removed."""
        scene = SceneAction(
            scene_number=1,
            setting_description="A park with birds and wind",
            action_description="Person walks through a park with birds singing",
        )
        instruction = generator._build_audio_instruction(scene)

        # Should not have duplicate "birds"
        assert instruction.count("birds") <= 2  # May appear in different forms


class TestInferAmbientSounds:
    """Tests for _infer_ambient_sounds method."""

    @pytest.fixture
    def generator(self):
        """Create a VideoGenerator with mocked client."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            return VideoGenerator(project="test", location="us-central1")

    def test_beach_setting(self, generator):
        """Test beach setting infers ocean sounds."""
        sounds = generator._infer_ambient_sounds("A sunny beach at sunset")
        assert "waves crashing" in sounds
        assert "seagulls" in sounds

    def test_ocean_setting(self, generator):
        """Test ocean setting infers water sounds."""
        sounds = generator._infer_ambient_sounds("Out on the open ocean")
        assert "waves crashing" in sounds

    def test_forest_setting(self, generator):
        """Test forest setting infers nature sounds."""
        sounds = generator._infer_ambient_sounds("Deep in the ancient forest")
        assert "birds chirping" in sounds
        assert "rustling leaves" in sounds
        assert "wind through trees" in sounds

    def test_city_setting(self, generator):
        """Test city setting infers urban sounds."""
        sounds = generator._infer_ambient_sounds("A busy city street corner")
        assert "city traffic" in sounds
        assert "urban ambience" in sounds

    def test_office_setting(self, generator):
        """Test office setting infers room tone."""
        sounds = generator._infer_ambient_sounds("A modern office space")
        assert "room tone" in sounds

    def test_gym_setting(self, generator):
        """Test gym setting infers sports sounds."""
        sounds = generator._infer_ambient_sounds("A basketball court in a gym")
        assert "sneakers squeaking" in sounds
        assert "crowd noise" in sounds

    def test_restaurant_setting(self, generator):
        """Test restaurant setting infers dining sounds."""
        sounds = generator._infer_ambient_sounds("A cozy Italian restaurant")
        assert "clinking dishes" in sounds
        assert "ambient chatter" in sounds

    def test_park_setting(self, generator):
        """Test park setting infers outdoor sounds."""
        sounds = generator._infer_ambient_sounds("A peaceful park")
        assert "birds" in sounds
        assert "wind" in sounds

    def test_mountain_setting(self, generator):
        """Test mountain setting infers natural sounds."""
        sounds = generator._infer_ambient_sounds("A mountain trail")
        assert "wind" in sounds
        assert "distant birds" in sounds

    def test_river_setting(self, generator):
        """Test river setting infers water sounds."""
        sounds = generator._infer_ambient_sounds("Along the river bank")
        assert "flowing water" in sounds

    def test_rain_setting(self, generator):
        """Test rainy setting infers weather sounds."""
        sounds = generator._infer_ambient_sounds("A rainy night in the city")
        assert "rain sounds" in sounds

    def test_night_setting(self, generator):
        """Test night setting infers evening sounds."""
        sounds = generator._infer_ambient_sounds("A quiet night in the suburbs")
        assert "crickets" in sounds

    def test_empty_setting(self, generator):
        """Test empty setting returns empty list."""
        sounds = generator._infer_ambient_sounds("")
        assert sounds == []

    def test_unknown_setting(self, generator):
        """Test unknown setting returns empty list."""
        sounds = generator._infer_ambient_sounds("A futuristic alien landscape")
        assert sounds == []

    def test_case_insensitive(self, generator):
        """Test that setting matching is case insensitive."""
        sounds_lower = generator._infer_ambient_sounds("beach")
        sounds_upper = generator._infer_ambient_sounds("BEACH")
        sounds_mixed = generator._infer_ambient_sounds("BeAcH")

        assert sounds_lower == sounds_upper == sounds_mixed


class TestInferActionSounds:
    """Tests for _infer_action_sounds method."""

    @pytest.fixture
    def generator(self):
        """Create a VideoGenerator with mocked client."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            return VideoGenerator(project="test", location="us-central1")

    def test_walking_action(self, generator):
        """Test walking action infers footsteps."""
        sounds = generator._infer_action_sounds("Person walks down the street")
        assert "footsteps" in sounds

    def test_running_action(self, generator):
        """Test running action infers running footsteps."""
        sounds = generator._infer_action_sounds("Runner sprints to the finish")
        assert "running footsteps" in sounds

    def test_door_action(self, generator):
        """Test door action infers door sounds."""
        sounds = generator._infer_action_sounds("Opens the door and enters")
        assert "door sounds" in sounds

    def test_car_action(self, generator):
        """Test car action infers engine sounds."""
        sounds = generator._infer_action_sounds("Drives away in a car")
        assert "car engine" in sounds

    def test_typing_action(self, generator):
        """Test typing action infers keyboard sounds."""
        sounds = generator._infer_action_sounds("Types furiously on the keyboard")
        assert "keyboard typing" in sounds

    def test_phone_action(self, generator):
        """Test phone action infers phone sounds."""
        sounds = generator._infer_action_sounds("Answers the phone call")
        assert "phone sounds" in sounds

    def test_eating_action(self, generator):
        """Test eating action infers eating sounds."""
        sounds = generator._infer_action_sounds("Eats dinner at the table")
        assert "eating and drinking sounds" in sounds

    def test_writing_action(self, generator):
        """Test writing action infers writing sounds."""
        sounds = generator._infer_action_sounds("Writes a letter with pen")
        assert "writing sounds" in sounds

    def test_ball_action(self, generator):
        """Test ball action infers ball sounds."""
        sounds = generator._infer_action_sounds("Throws the ball to teammate")
        assert "ball sounds" in sounds

    def test_applause_action(self, generator):
        """Test applause action infers clapping sounds."""
        sounds = generator._infer_action_sounds("Audience claps and cheers")
        assert "applause" in sounds

    def test_conversation_action(self, generator):
        """Test conversation action infers talking sounds."""
        sounds = generator._infer_action_sounds("They discuss the proposal")
        assert "conversation" in sounds

    def test_cooking_action(self, generator):
        """Test cooking action infers kitchen sounds."""
        sounds = generator._infer_action_sounds("Chef cooks vegetables and sizzles the pan")
        assert "cooking sounds" in sounds

    def test_swimming_action(self, generator):
        """Test swimming action infers water sounds."""
        sounds = generator._infer_action_sounds("Dives into the pool and swims")
        assert "water splashing" in sounds

    def test_empty_action(self, generator):
        """Test empty action returns empty list."""
        sounds = generator._infer_action_sounds("")
        assert sounds == []

    def test_unknown_action(self, generator):
        """Test unknown action returns empty list."""
        sounds = generator._infer_action_sounds("Contemplates life silently")
        assert sounds == []

    def test_case_insensitive(self, generator):
        """Test that action matching is case insensitive."""
        sounds_lower = generator._infer_action_sounds("walks")
        sounds_upper = generator._infer_action_sounds("WALKS")
        sounds_mixed = generator._infer_action_sounds("WaLkS")

        assert sounds_lower == sounds_upper == sounds_mixed


class TestBuildPromptWithAudio:
    """Tests for _build_prompt integration with audio instructions."""

    @pytest.fixture
    def generator(self):
        """Create a VideoGenerator with mocked client."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            return VideoGenerator(project="test", location="us-central1")

    def test_build_prompt_includes_audio_instruction_by_default(self, generator):
        """Test that audio instruction is included by default."""
        scene = SceneAction(
            scene_number=1,
            setting_description="A beach",
            action_description="Person walks along the shore",
        )
        prompt = generator._build_prompt(scene)

        # New format uses "Ambient:" and "SFX:" prefixes instead of "Audio:"
        assert "Ambient:" in prompt or "SFX:" in prompt
        assert "No background music" in prompt

    def test_build_prompt_excludes_audio_when_disabled(self, generator):
        """Test that audio instruction can be disabled."""
        scene = SceneAction(
            scene_number=1,
            setting_description="A beach",
            action_description="Person walks along the shore",
        )
        prompt = generator._build_prompt(scene, exclude_background_music=False)

        # When disabled, no audio prefixes should be present
        assert "Ambient:" not in prompt
        assert "SFX:" not in prompt
        assert "No background music" not in prompt

    def test_build_prompt_combined_audio_instruction(self, generator):
        """Test full prompt combines setting and action sounds."""
        scene = SceneAction(
            scene_number=2,
            setting_description="A busy city street",
            action_description="Detective runs after suspect",
            dialogue="Stop right there!",
        )
        prompt = generator._build_prompt(scene, total_scenes=3)

        # Should have flow context
        assert "scene 2 of 3" in prompt
        # Should have visual content
        assert "Setting: A busy city street" in prompt
        assert "Detective runs after suspect" in prompt
        # Dialogue is now integrated with action using quotes
        assert '"Stop right there!"' in prompt
        # Should have audio instruction with proper prefixes
        assert "Ambient:" in prompt or "SFX:" in prompt
        assert "clear character dialogue" in prompt
        assert "No background music" in prompt

    def test_build_prompt_all_elements_in_order(self, generator):
        """Test that prompt elements are in logical order.

        New order follows Google's VEO 3.1 formula:
        [Cinematography] + [Subject+Action] + [Context] + [Style] + [Audio]
        """
        scene = SceneAction(
            scene_number=1,
            setting_description="An office",
            action_description="Manager types on computer",
            camera_direction="Close-up shot",
            dialogue="Let me check",
        )
        prompt = generator._build_prompt(scene)

        # Camera should be first (cinematography)
        camera_position = prompt.find("Close-up shot")
        # Action with dialogue follows camera
        action_position = prompt.find("Manager types")
        # Setting comes after action
        setting_position = prompt.find("Setting:")
        # Audio instruction should be at the end
        audio_position = prompt.find("Ambient:")
        if audio_position == -1:
            audio_position = prompt.find("SFX:")

        # Verify order: Camera < Action < Setting < Audio
        assert camera_position < action_position, "Camera should come before action"
        assert action_position < setting_position, "Action should come before setting"
        assert setting_position < audio_position, "Setting should come before audio"


class TestAudioInstructionEdgeCases:
    """Edge case tests for audio instruction generation."""

    @pytest.fixture
    def generator(self):
        """Create a VideoGenerator with mocked client."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            return VideoGenerator(project="test", location="us-central1")

    def test_multiple_environment_matches(self, generator):
        """Test setting with multiple environment keywords."""
        scene = SceneAction(
            scene_number=1,
            setting_description="A beach near the forest at night",
            action_description="Person walks",
        )
        instruction = generator._build_audio_instruction(scene)

        # Should include sounds from all matched environments
        assert "waves crashing" in instruction or "seagulls" in instruction
        assert "birds chirping" in instruction or "rustling leaves" in instruction
        assert "crickets" in instruction

    def test_multiple_action_matches(self, generator):
        """Test action with multiple action keywords."""
        scene = SceneAction(
            scene_number=1,
            setting_description="A street",
            action_description="Opens the car door and drives away",
        )
        instruction = generator._build_audio_instruction(scene)

        assert "door sounds" in instruction
        assert "car engine" in instruction

    def test_very_long_setting(self, generator):
        """Test handling of very long setting descriptions."""
        long_setting = (
            "A massive ancient forest with towering oak trees, "
            "a winding river running through it, "
            "mountains visible in the distance, "
            "and a small beach area by the lake"
        )
        scene = SceneAction(
            scene_number=1,
            setting_description=long_setting,
            action_description="Person explores",
        )
        instruction = generator._build_audio_instruction(scene)

        # Should handle without error and include relevant sounds
        assert "No background music" in instruction

    def test_special_characters_in_setting(self, generator):
        """Test handling of special characters in setting."""
        scene = SceneAction(
            scene_number=1,
            setting_description="A café/restaurant with street-view",
            action_description="Person eats",
        )
        instruction = generator._build_audio_instruction(scene)

        # Should handle special characters gracefully
        assert "No background music" in instruction
