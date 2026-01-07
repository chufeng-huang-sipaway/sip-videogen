"""VEO 3.1 Video Generator for creating video clips.

This module provides video generation functionality using Google's VEO 3.1 API
via the Gemini API to create video clips for each scene in the script.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from google import genai
from google.genai.types import GenerateVideosConfig, Image, VideoGenerationReferenceImage
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from sip_studio.config.logging import get_logger
from sip_studio.generators.base import (
    BaseVideoGenerator,
    PromptSafetyError,
    ServiceAgentNotReadyError,
    VideoGenerationError,
)
from sip_studio.generators.prompt_builder import build_structured_scene_prompt
from sip_studio.models.aspect_ratio import get_supported_ratio, validate_aspect_ratio
from sip_studio.models.assets import AssetType, GeneratedAsset
from sip_studio.models.script import SceneAction, VideoScript

logger = get_logger(__name__)


class VEOVideoGenerator(BaseVideoGenerator):
    """Generates video clips using Google VEO 3.1 via Gemini API.

    This class handles the generation of video clips for each scene,
    optionally using reference images for visual consistency.
    """

    # Provider identification
    PROVIDER_NAME = "veo"

    # VEO 3.1 constraints
    MAX_REFERENCE_IMAGES = 3
    VALID_DURATIONS = [4, 6, 8]
    FORCED_DURATION_WITH_REFS = 8  # VEO forces 8s when using reference images
    POLL_INTERVAL_SECONDS = 15

    def __init__(
        self,
        api_key: str | None = None,
        *,
        project: str | None = None,
        location: str | None = None,
        model: str = "veo-3.1-generate-preview",
    ):
        """Initialize the video generator with Gemini/VEO client.

        Tests construct this class with ``project`` and ``location`` for backwards
        compatibility with Vertex-style clients; we accept those parameters but
        VEO generation today only needs the Gemini API key.

        Args:
            api_key: Google Gemini API key. If not provided, attempts to create a client
                without explicit key (suitable when default credentials are configured).
            project: Optional project identifier (accepted for compatibility; unused).
            location: Optional location/region (accepted for compatibility; unused).
            model: Model to use for video generation. Defaults to veo-3.1-generate-preview.
        """
        # Accept project/location for compatibility but do not require them.
        self.api_key = api_key
        self.project = project
        self.location = location
        self.model = model
        self.client = genai.Client(api_key=api_key)
        logger.debug(
            "Initialized VEOVideoGenerator with model %s (project=%s, location=%s)",
            model,
            project or "default",
            location or "default",
        )

    @retry(
        retry=retry_if_exception(lambda e: not isinstance(e, PromptSafetyError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    async def generate_video_clip(
        self,
        scene: SceneAction,
        output_dir: str,
        reference_images: list[GeneratedAsset] | None = None,
        aspect_ratio: str = "1:1",
        generate_audio: bool = True,
        total_scenes: int | None = None,
        script: VideoScript | None = None,
        constraints_context: str | None = None,
        start_frame: GeneratedAsset | None = None,
    ) -> GeneratedAsset:
        """Generate a video clip for a scene.

        Args:
            scene: The SceneAction to generate a video for.
            output_dir: Local directory to save the generated video.
            reference_images: Optional list of reference images for visual consistency.
                             Maximum 3 images allowed. Only used with 16:9 aspect ratio.
            aspect_ratio: Video aspect ratio. Defaults to 16:9. Options: 16:9, 9:16.
            generate_audio: Whether to generate audio. Defaults to True.
            total_scenes: Total number of scenes in the video sequence. When provided,
                         adds flow context to prompts to eliminate awkward pauses
                         between clips when assembled.
            script: Optional VideoScript for element lookups when building reference
                   linking context. When provided with reference_images, adds explicit
                   phrases linking characters to their reference images.
            constraints_context: Optional constraints block to append to the prompt.
            start_frame: Optional start frame image for image-to-video mode.
                        Supports both 16:9 and 9:16 aspect ratios. When provided,
                        the video will animate from this frame.

        Returns:
            GeneratedAsset with the local path to the generated video.

        Raises:
            VideoGenerationError: If video generation fails after retries.
        """
        logger.info(f"Generating video clip for scene {scene.scene_number}")

        # Validate and apply provider-specific fallback for aspect ratio
        validated_ratio = validate_aspect_ratio(aspect_ratio)
        actual_ratio, was_fallback = get_supported_ratio(validated_ratio, self.PROVIDER_NAME)
        if was_fallback:
            logger.warning(
                f"Scene {scene.scene_number}: Using fallback ratio "
                f"{actual_ratio.value} (requested: {aspect_ratio})"
            )
        final_aspect_ratio = actual_ratio.value

        # Build start frame image for image-to-video mode (supports 9:16)
        start_frame_image = None
        if start_frame and start_frame.local_path:
            from pathlib import Path

            sf_path = Path(start_frame.local_path)
            if sf_path.exists():
                sf_bytes = sf_path.read_bytes()
                sf_mime = self._get_mime_type(start_frame.local_path)
                start_frame_image = Image(image_bytes=sf_bytes, mime_type=sf_mime)
                logger.info(f"Using start frame for image-to-video mode ({len(sf_bytes)} bytes)")

        # Build reference image configs (max 3) - only for 16:9 or when no start_frame
        ref_configs = None
        if reference_images and not start_frame_image:
            ref_configs = await self._build_reference_configs(reference_images)
            logger.debug(f"Using {len(ref_configs)} reference images")

        # Determine duration (forced to 8s when using reference images)
        duration = self._get_duration(scene, has_references=bool(ref_configs))

        # Build the prompt with flow context and reference image linking
        prompt = self._build_prompt(
            scene,
            total_scenes=total_scenes,
            reference_images=reference_images,
            script=script,
            constraints_context=constraints_context,
        )
        logger.debug(f"Video prompt: {prompt}")

        try:
            # Start video generation via Gemini API
            # VEO 3.1 generates audio by default
            config_kwargs: dict = {
                "duration_seconds": duration,
                "aspect_ratio": final_aspect_ratio,
            }
            # Image-to-video mode: use `image` param (supports 9:16)
            # Reference images mode: use `reference_images` in config (16:9 only)
            if start_frame_image:
                # Image-to-video mode - supports both 16:9 and 9:16
                config_kwargs["person_generation"] = "allow_adult"
                logger.info(
                    f"Scene {scene.scene_number}: Using image-to-video mode "
                    f"(aspect_ratio={final_aspect_ratio})"
                )
                operation = self.client.models.generate_videos(
                    model=self.model,
                    prompt=prompt,
                    image=start_frame_image,
                    config=GenerateVideosConfig(**config_kwargs),
                )
            elif ref_configs:
                # Reference images mode - 16:9 only
                config_kwargs["reference_images"] = ref_configs
                config_kwargs["person_generation"] = "allow_adult"
                if final_aspect_ratio != "16:9":
                    logger.warning(
                        f"Scene {scene.scene_number}: VEO reference images only support 16:9. "
                        f"Falling back from {final_aspect_ratio} to 16:9."
                    )
                    config_kwargs["aspect_ratio"] = "16:9"
                operation = self.client.models.generate_videos(
                    model=self.model,
                    prompt=prompt,
                    config=GenerateVideosConfig(**config_kwargs),
                )
            else:
                # Text-to-video mode
                operation = self.client.models.generate_videos(
                    model=self.model,
                    prompt=prompt,
                    config=GenerateVideosConfig(**config_kwargs),
                )

            logger.info(
                f"Started video generation for scene {scene.scene_number}, "
                f"polling for completion..."
            )

            # Poll for completion (async sleep to allow other clips to generate in parallel)
            while not operation.done:
                await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
                operation = self.client.operations.get(operation)
                logger.debug(f"Scene {scene.scene_number} generation in progress...")

            # Check for errors in the operation
            if hasattr(operation, "error") and operation.error:
                error_raw = operation.error
                error_msg = str(error_raw)
                logger.error(f"VEO operation error: {error_msg}")

                # Try to infer an error code from the error object or message
                error_code = getattr(error_raw, "code", None)
                if error_code is None:
                    if "'code': 3" in error_msg or '"code": 3' in error_msg:
                        error_code = 3
                    elif "'code': 9" in error_msg or '"code": 9' in error_msg:
                        error_code = 9

                # Prompt/policy violation – do not retry
                if error_code == 3 or "usage guidelines" in error_msg:
                    raise PromptSafetyError(
                        "VEO rejected the prompt because it may violate "
                        "usage guidelines (for example, real-person names, brands, "
                        "or other sensitive terms). Please simplify or anonymize "
                        f"the description for scene {scene.scene_number}. "
                        f"Raw error: {error_msg}"
                    )

                # Service agents not ready – advise user to wait and retry CLI later
                if error_code == 9 or "Service agents are being provisioned" in error_msg:
                    raise ServiceAgentNotReadyError(
                        "VEO service agents are still being provisioned. "
                        "Wait a few minutes and try again. "
                        f"Raw error: {error_msg}"
                    )

                raise VideoGenerationError(
                    f"Video generation failed for scene {scene.scene_number}: {error_msg}"
                )

            # Check for response
            if not operation.response:
                # Try to get more details
                details = ""
                if hasattr(operation, "metadata"):
                    details = f" Metadata: {operation.metadata}"
                raise VideoGenerationError(
                    f"Video generation failed for scene {scene.scene_number}: "
                    f"No response received.{details}"
                )

            # Extract and save video
            from pathlib import Path

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            if not operation.result or not operation.result.generated_videos:
                raise VideoGenerationError(f"No video generated for scene {scene.scene_number}")
            video_data = operation.result.generated_videos[0]
            video_filename = f"scene_{scene.scene_number:03d}.mp4"
            video_path = output_path / video_filename

            # Download video via Files API (handles authentication)
            logger.info(f"Downloading video for scene {scene.scene_number} via Files API...")
            if not video_data.video:
                raise VideoGenerationError(f"No video data for scene {scene.scene_number}")
            self.client.files.download(file=video_data.video)
            video_data.video.save(str(video_path))

            logger.info(f"Video clip for scene {scene.scene_number} saved to: {video_path}")

            return GeneratedAsset(
                asset_type=AssetType.VIDEO_CLIP,
                scene_number=scene.scene_number,
                local_path=str(video_path),
            )

        except (PromptSafetyError, ServiceAgentNotReadyError):
            # Already logged with specific guidance, just propagate
            raise
        except Exception as e:
            logger.error(f"Failed to generate video for scene {scene.scene_number}: {e}")
            raise VideoGenerationError(
                f"Failed to generate video clip for scene {scene.scene_number}: {e}"
            ) from e

    async def _build_reference_configs(
        self,
        reference_images: list[GeneratedAsset],
    ) -> list[VideoGenerationReferenceImage]:
        """Build reference image configurations for VEO using Files API.

        Args:
            reference_images: List of GeneratedAssets with local paths.

        Returns:
            List of RawReferenceImage configs with uploaded file references.
        """
        configs = []
        for idx, asset in enumerate(reference_images[: self.MAX_REFERENCE_IMAGES]):
            if not asset.local_path:
                logger.warning(f"Skipping reference image {asset.element_id}: no local path")
                continue

            try:
                # Read image as bytes for Gemini API
                logger.debug(f"Reading reference image {idx + 1}: {asset.local_path}")
                from pathlib import Path

                image_path = Path(asset.local_path)
                image_bytes = image_path.read_bytes()
                mime_type = self._get_mime_type(asset.local_path)

                # Use VideoGenerationReferenceImage with image_bytes
                configs.append(
                    VideoGenerationReferenceImage(
                        image=Image(image_bytes=image_bytes, mime_type=mime_type),
                        reference_type="asset",  # type: ignore[arg-type]
                    )
                )
                logger.debug(f"Added reference image {idx + 1} ({len(image_bytes)} bytes)")
            except Exception as e:
                logger.warning(f"Failed to load reference image {asset.element_id}: {e}")
                continue

        return configs

    def _build_flow_context(
        self,
        scene: SceneAction,
        total_scenes: int | None,
    ) -> str | None:
        """Build scene flow context to eliminate awkward pauses between clips.

        This adds context to each scene's prompt to inform VEO that the clip
        is part of a continuous sequence, guiding it to avoid pauses at
        scene boundaries that would create awkward gaps when assembled.

        Args:
            scene: The SceneAction being processed.
            total_scenes: Total number of scenes in the video sequence.

        Returns:
            Flow context string, or None if context cannot be determined.
        """
        if total_scenes is None or total_scenes <= 1:
            return None

        scene_num = scene.scene_number
        is_first = scene_num == 1
        is_last = scene_num == total_scenes

        parts = [f"This is scene {scene_num} of {total_scenes} in a continuous video sequence"]

        if is_first:
            parts.append(
                "As the opening scene, it may begin with an establishing moment, "
                "but must end with action in progress that continues into the next scene. "
                "Do NOT end with characters pausing, looking at camera, or any sense of conclusion"
            )
        elif is_last:
            parts.append(
                "As the final scene, begin mid-action continuing from the previous scene - "
                "NO pause at the start. A natural conclusion is appropriate for the ending"
            )
        else:
            parts.append(
                "As a middle scene, flow seamlessly: begin mid-action (NO opening pause), "
                "end with action in progress (NO closing pause, NO looking at camera). "
                "Continuous motion throughout"
            )

        return ". ".join(parts)

    def _build_reference_linking_context(
        self,
        reference_images: list[GeneratedAsset] | None,
        script: VideoScript | None,
    ) -> str | None:
        """Build explicit reference image linking phrases for VEO.

        Uses Google's recommended phrasing:
        "Using the provided images for [element1], [element2], and [setting]..."

        This tells VEO which character/element in the prompt corresponds to which
        reference image, improving visual consistency without needing detailed
        appearance descriptions in the prompt text.

        Args:
            reference_images: List of reference images for this scene.
            script: The VideoScript containing SharedElement definitions.

        Returns:
            Reference linking context string, or None if no linking needed.
        """
        if not reference_images or not script:
            return None

        # Group references by element ID to support multi-angle refs
        element_to_indices: dict[str, list[int]] = {}
        for idx, ref in enumerate(reference_images, start=1):
            if not ref.element_id:
                continue
            element_to_indices.setdefault(ref.element_id, []).append(idx)

        if not element_to_indices:
            return None

        element_names: list[str] = []
        element_details: list[str] = []
        seen_names: set[str] = set()

        def _format_indices(indices: list[int]) -> str:
            if len(indices) == 1:
                return f"reference image {indices[0]}"
            if len(indices) == 2:
                return f"reference images {indices[0]} and {indices[1]}"
            return (
                "reference images "
                + ", ".join(str(i) for i in indices[:-1])
                + f", and {indices[-1]}"
            )

        def _ensure_the(label: str) -> str:
            clean = label.strip()
            if not clean:
                return clean
            return clean if clean.lower().startswith("the ") else f"the {clean}"

        for element_id, indices in element_to_indices.items():
            element = script.get_element_by_id(element_id)
            if not element:
                continue

            descriptor = element.role_descriptor or element.name
            if element.element_type.value == "character":
                name = descriptor
                detail = (
                    f"{descriptor.capitalize()}'s appearance matches {_format_indices(indices)}"
                )
            elif element.element_type.value == "environment":
                name = _ensure_the(descriptor)
                detail = f"{name.capitalize()} matches {_format_indices(indices)}"
            else:
                name = _ensure_the(descriptor)
                detail = f"{name.capitalize()} matches {_format_indices(indices)}"

            if name not in seen_names:
                element_names.append(name)
                seen_names.add(name)
            element_details.append(detail)

        if not element_names:
            return None

        if len(element_names) == 1:
            opening = f"Using the provided image for {element_names[0]}"
        elif len(element_names) == 2:
            opening = f"Using the provided images for {element_names[0]} and {element_names[1]}"
        else:
            opening = (
                f"Using the provided images for {', '.join(element_names[:-1])}, "
                f"and {element_names[-1]}"
            )

        if element_details:
            return f"{opening}. Reference mapping: " + "; ".join(element_details)

        return opening

    def _build_prompt(
        self,
        scene: SceneAction,
        total_scenes: int | None = None,
        exclude_background_music: bool = True,
        reference_images: list[GeneratedAsset] | None = None,
        script: VideoScript | None = None,
        constraints_context: str | None = None,
    ) -> str:
        """Build a generation prompt from scene details.

        Uses Google's recommended VEO 3.1 prompt formula:
        [Cinematography] + [Subject+Action] + [Context] + [Style] + [Audio]

        Args:
            scene: The SceneAction to build a prompt for.
            total_scenes: Total number of scenes in the video (for flow context).
            exclude_background_music: Whether to add audio instructions that exclude
                background music. When True, instructs VEO to generate ambient sounds
                and dialogue but no background music/soundtrack, allowing external
                music to be added later. Defaults to True.
            reference_images: Optional list of reference images for this scene.
                Used to build reference linking context.
            script: Optional VideoScript for element lookups when building
                reference linking context.
            constraints_context: Optional constraints block to append to the prompt.

        Returns:
            A detailed prompt string for video generation.
        """
        # Build supporting context
        linking_context = self._build_reference_linking_context(reference_images, script)
        flow_context = self._build_flow_context(scene, total_scenes)
        audio_instruction = None
        if exclude_background_music:
            audio_instruction = self._build_audio_instruction(scene)

        raw_prompt = build_structured_scene_prompt(
            scene=scene,
            script=script,
            flow_context=flow_context,
            reference_context=linking_context,
            audio_instruction=audio_instruction,
            constraints_context=constraints_context,
        )

        return self._sanitize_prompt_for_vertex(raw_prompt)

    def _build_timestamp_prompt_full(
        self,
        scene: SceneAction,
        reference_images: list[GeneratedAsset] | None,
        script: VideoScript | None,
        exclude_background_music: bool,
    ) -> str:
        """Build a complete timestamp-prompted scene (experimental).

        This creates a multi-shot sequence using Google's VEO 3.1 timestamp format.
        Each sub_shot becomes a timestamped segment within the generated clip.

        Args:
            scene: The SceneAction with sub_shots defined.
            reference_images: Optional reference images for visual consistency.
            script: Optional VideoScript for context.
            exclude_background_music: Whether to exclude background music.

        Returns:
            Complete timestamp-formatted prompt string.
        """
        # Safety check: if pattern is not [8] but sub_shots is empty, warn and fall back
        if hasattr(scene, "clip_pattern") and scene.clip_pattern != [8] and not scene.sub_shots:
            logger.warning(
                f"Scene {scene.scene_number} has multi-shot pattern {scene.clip_pattern} "
                "but no sub_shots. Falling back to standard prompt."
            )
            # Fall back to standard prompt building
            return self._build_prompt(
                scene,
                exclude_background_music=exclude_background_music,
                reference_images=reference_images,
                script=script,
            )

        parts = []

        # 1. Reference image context (applies to all sub-shots)
        linking_context = self._build_reference_linking_context(reference_images, script)
        if linking_context:
            parts.append(linking_context)

        # 2. Global setting for all sub-shots
        if scene.setting_description:
            parts.append(f"Setting: {scene.setting_description}")

        # 3. Visual style
        if script and script.visual_style:
            parts.append(f"Visual style: {script.visual_style}")

        # Add intro context
        intro = ". ".join(parts) if parts else ""

        # 4. Build timestamp segments
        timestamp_content = self._build_timestamp_prompt(scene)

        # 5. Audio instruction at the end
        audio_parts = []
        if exclude_background_music:
            audio_instruction = self._build_audio_instruction(scene)
            audio_parts.append(audio_instruction)

        # Combine: intro, then timestamp segments, then audio
        final_parts = []
        if intro:
            final_parts.append(intro)
        final_parts.append(timestamp_content)
        if audio_parts:
            final_parts.append(". ".join(audio_parts))

        raw_prompt = "\n\n".join(final_parts)
        return self._sanitize_prompt_for_vertex(raw_prompt)

    def _build_action_with_dialogue(self, scene: SceneAction) -> str:
        """Build action description with integrated dialogue using quotation marks.

        Following Google's VEO 3.1 best practices:
        - Use quotation marks for spoken lines
        - Integrate dialogue naturally into action description

        Example: 'The vendor flips a burger and says, "Best burgers in town!"'

        Args:
            scene: The SceneAction containing action and optional dialogue.

        Returns:
            Action string with integrated dialogue.
        """
        action = scene.action_description

        if not scene.dialogue:
            return action

        # Format dialogue with quotation marks
        dialogue_text = scene.dialogue.strip()

        # Remove any existing quotes to normalize
        if dialogue_text.startswith('"') and dialogue_text.endswith('"'):
            dialogue_text = dialogue_text[1:-1]
        if dialogue_text.startswith("'") and dialogue_text.endswith("'"):
            dialogue_text = dialogue_text[1:-1]

        # Check if action already mentions speaking/saying
        speaking_verbs = ["says", "saying", "said", "speaks", "asks", "replies", "responds"]
        has_speaking_verb = any(verb in action.lower() for verb in speaking_verbs)

        if has_speaking_verb:
            # Action already has speaking context, just add quoted dialogue
            # Try to insert dialogue after the speaking verb
            return f'{action}: "{dialogue_text}"'
        else:
            # Append dialogue naturally
            # Strip trailing punctuation from action for cleaner merge
            action_clean = action.rstrip(".,;:")
            return f'{action_clean}, saying "{dialogue_text}"'

    def _build_timestamp_prompt(self, scene: SceneAction) -> str:
        """Build a timestamp-based prompt for multi-shot scenes (experimental).

        Uses Google's VEO 3.1 timestamp prompting format:
        [00:00-00:02] Medium shot of explorer pushing aside vines
        [00:02-00:04] Close-up of explorer's face showing wonder
        ...

        Args:
            scene: The SceneAction with sub_shots defined.

        Returns:
            Timestamp-formatted prompt string.
        """
        if not scene.sub_shots:
            return ""

        segments = []
        for sub_shot in scene.sub_shots:
            # Format time as [MM:SS-MM:SS]
            start_time = f"00:0{sub_shot.start_second}"
            end_time = f"00:0{sub_shot.end_second}"

            # Build the sub-shot description
            shot_parts = [sub_shot.camera_direction]

            # Add action with optional dialogue
            if sub_shot.dialogue:
                dialogue_clean = sub_shot.dialogue.strip().strip('"').strip("'")
                shot_parts.append(f'{sub_shot.action_description}, saying "{dialogue_clean}"')
            else:
                shot_parts.append(sub_shot.action_description)

            segment = f"[{start_time}-{end_time}] {'. '.join(shot_parts)}"
            segments.append(segment)

        return "\n\n".join(segments)

    def _build_audio_instruction(self, scene: SceneAction) -> str:
        """Build audio instruction with SFX prefix following Google's VEO 3.1 guide.

        Uses Google's recommended audio notation:
        - "SFX:" prefix for specific sound effects
        - "Ambient:" for environmental background sounds
        - Separate treatment for dialogue

        Args:
            scene: The SceneAction to analyze for audio cues.

        Returns:
            Audio instruction string for the VEO prompt.
        """
        ambient_sounds = []
        sfx_sounds = []

        # Infer ambient sounds from setting
        if scene.setting_description:
            ambient_sounds = self._infer_ambient_sounds(scene.setting_description)

        # Infer action-specific sound effects from action description
        if scene.action_description:
            sfx_sounds = self._infer_action_sounds(scene.action_description)

        # Build the audio instruction with proper prefixes
        audio_parts = []

        # Ambient sounds (environmental background)
        if ambient_sounds:
            unique_ambient = list(dict.fromkeys(ambient_sounds))
            audio_parts.append(f"Ambient: {', '.join(unique_ambient)}")

        # SFX for specific action sounds
        if sfx_sounds:
            unique_sfx = list(dict.fromkeys(sfx_sounds))
            audio_parts.append(f"SFX: {', '.join(unique_sfx)}")

        # Note about dialogue (VEO handles this from the action text with quotes)
        if scene.dialogue:
            audio_parts.append("clear character dialogue forward in the mix")

        # Combine and add no-music instruction
        no_music_clause = (
            "No background music, no soundtrack, no score or instrumental bed; "
            "keep only production sound, ambience, SFX, and dialogue"
        )

        if audio_parts:
            return ". ".join(audio_parts) + ". " + no_music_clause
        else:
            return f"Ambient: natural environmental sounds. {no_music_clause}"

    def _infer_ambient_sounds(self, setting: str) -> list[str]:
        """Infer ambient sounds from scene setting description.

        Args:
            setting: The setting description to analyze.

        Returns:
            List of ambient sound descriptions.
        """
        setting_lower = setting.lower()
        sounds = []

        # Beach/ocean environments
        if any(word in setting_lower for word in ["beach", "ocean", "sea", "coast", "shore"]):
            sounds.extend(["waves crashing", "seagulls"])

        # Forest/nature environments
        if any(word in setting_lower for word in ["forest", "woods", "jungle", "trees", "nature"]):
            sounds.extend(["birds chirping", "rustling leaves", "wind through trees"])

        # City/urban environments
        city_keywords = ["city", "street", "urban", "downtown", "sidewalk"]
        if any(word in setting_lower for word in city_keywords):
            sounds.extend(["city traffic", "distant sirens", "urban ambience"])

        # Indoor environments
        indoor_keywords = ["office", "room", "indoor", "building", "house", "home"]
        if any(word in setting_lower for word in indoor_keywords):
            sounds.append("room tone")

        # Sports/gym environments
        sports_keywords = ["gym", "basketball", "court", "field", "stadium", "arena"]
        if any(word in setting_lower for word in sports_keywords):
            sounds.extend(["sneakers squeaking", "crowd noise"])

        # Restaurant/cafe environments
        if any(word in setting_lower for word in ["restaurant", "cafe", "coffee", "diner", "bar"]):
            sounds.extend(["clinking dishes", "ambient chatter"])

        # Park/outdoor environments
        if any(word in setting_lower for word in ["park", "garden", "lawn", "yard", "backyard"]):
            sounds.extend(["birds", "wind"])

        # Mountain/hiking environments
        if any(word in setting_lower for word in ["mountain", "hill", "hike", "trail", "cliff"]):
            sounds.extend(["wind", "distant birds"])

        # Water environments (non-ocean)
        if any(word in setting_lower for word in ["river", "stream", "waterfall", "lake", "pond"]):
            sounds.append("flowing water")

        # Rain/weather
        if any(word in setting_lower for word in ["rain", "storm", "thunder"]):
            sounds.append("rain sounds")

        # Night environments
        if any(word in setting_lower for word in ["night", "evening", "dark"]):
            sounds.append("crickets")

        return sounds

    def _infer_action_sounds(self, action: str) -> list[str]:
        """Infer sound effects from action description.

        Args:
            action: The action description to analyze.

        Returns:
            List of action sound effect descriptions.
        """
        action_lower = action.lower()
        sounds = []

        # Movement sounds
        if any(word in action_lower for word in ["walk", "walking", "steps"]):
            sounds.append("footsteps")
        if any(word in action_lower for word in ["run", "running", "sprint", "jog"]):
            sounds.append("running footsteps")

        # Door sounds
        if any(word in action_lower for word in ["door", "enter", "exit", "open", "close"]):
            sounds.append("door sounds")

        # Vehicle sounds
        if any(word in action_lower for word in ["car", "drive", "driving", "vehicle"]):
            sounds.append("car engine")
        if any(word in action_lower for word in ["bike", "bicycle", "cycling"]):
            sounds.append("bicycle sounds")

        # Typing/computer sounds
        if any(word in action_lower for word in ["type", "typing", "computer", "keyboard"]):
            sounds.append("keyboard typing")
        if any(word in action_lower for word in ["phone", "call", "ring"]):
            sounds.append("phone sounds")

        # Eating/drinking sounds
        if any(word in action_lower for word in ["eat", "eating", "drink", "drinking", "sip"]):
            sounds.append("eating and drinking sounds")

        # Writing sounds
        if any(word in action_lower for word in ["write", "writing", "pen", "pencil"]):
            sounds.append("writing sounds")

        # Sports sounds
        if any(word in action_lower for word in ["throw", "catch", "ball", "kick"]):
            sounds.append("ball sounds")

        # Clapping/applause
        if any(word in action_lower for word in ["clap", "applause", "cheer"]):
            sounds.append("applause")

        # Conversation
        if any(word in action_lower for word in ["talk", "speak", "convers", "chat", "discuss"]):
            sounds.append("conversation")

        # Cooking
        if any(word in action_lower for word in ["cook", "fry", "boil", "sizzle", "kitchen"]):
            sounds.append("cooking sounds")

        # Water/splash
        if any(word in action_lower for word in ["swim", "splash", "dive", "water"]):
            sounds.append("water splashing")

        return sounds

    def _sanitize_prompt_for_vertex(self, prompt: str) -> str:
        """Sanitize prompts to better align with Vertex AI usage guidelines.

        This avoids directly naming real public figures or specific brands in
        the prompts sent to the video model by replacing them with more
        generic descriptors. This helps reduce prompt rejections while
        keeping the creative intent.
        """
        sanitized = prompt

        replacements = {
            # Public figures – replace with generic descriptors
            "Elon Musk": "a charismatic tech spokesperson",
            "Elon": "the charismatic tech spokesperson",
            # Brand names – replace with generic location descriptions
            "Dunkin’ Donuts": "a popular neon-lit donut shop",
            "Dunkin' Donuts": "a popular neon-lit donut shop",
        }

        for original, replacement in replacements.items():
            if original in sanitized:
                logger.debug(
                    f"Sanitizing prompt for Vertex AI: replacing '{original}' with '{replacement}'"
                )
                sanitized = sanitized.replace(original, replacement)

        return sanitized

    def _get_duration(self, scene: SceneAction, has_references: bool) -> int:
        """Get the video duration, respecting VEO constraints.

        Args:
            scene: The SceneAction with requested duration.
            has_references: Whether reference images are being used.

        Returns:
            Duration in seconds (4, 6, or 8).
        """
        if has_references:
            # VEO forces 8 seconds when using reference images
            return self.FORCED_DURATION_WITH_REFS

        # Validate and normalize to nearest valid duration
        requested = scene.duration_seconds
        if requested in self.VALID_DURATIONS:
            return requested

        # Find nearest valid duration
        nearest = min(self.VALID_DURATIONS, key=lambda x: abs(x - requested))
        logger.debug(
            f"Adjusted duration from {requested}s to {nearest}s (valid: {self.VALID_DURATIONS})"
        )
        return nearest

    def _get_mime_type(self, path: str) -> str:
        """Determine mime type from file path.

        Args:
            path: File path.

        Returns:
            MIME type string.
        """
        path_lower = path.lower()
        if path_lower.endswith(".png"):
            return "image/png"
        elif path_lower.endswith(".jpg") or path_lower.endswith(".jpeg"):
            return "image/jpeg"
        elif path_lower.endswith(".webp"):
            return "image/webp"
        else:
            # Default to PNG for unknown
            return "image/png"

    async def generate_all_video_clips(  # type: ignore[override]
        self,
        script: VideoScript,
        output_dir: str,
        reference_images: list[GeneratedAsset] | None = None,
        max_concurrent: int = 3,
        inter_request_delay: float = 2.0,
        show_progress: bool = True,
        max_repair_attempts: int = 2,
    ) -> list[GeneratedAsset]:
        """Generate video clips for all scenes in parallel with progress tracking.

        This method generates video clips for all scenes in the script,
        managing concurrency and rate limits while displaying progress.
        When a scene fails due to safety policy violations, it automatically
        uses an AI agent to repair the prompt and retry.

        Args:
            script: The VideoScript containing scenes to generate videos for.
            output_dir: Local directory for video outputs.
            reference_images: Optional list of reference images for visual consistency.
            max_concurrent: Maximum number of concurrent video generations. Defaults to 3.
            inter_request_delay: Delay in seconds between starting new requests. Defaults to 2.0.
            show_progress: Whether to display a Rich progress bar. Defaults to True.
            max_repair_attempts: Maximum number of prompt repair attempts per scene
                when safety policy violations occur. Defaults to 2.

        Returns:
            List of GeneratedAssets for all successfully generated video clips,
            sorted by scene number.
        """
        scenes = script.scenes
        if not scenes:
            logger.warning("No scenes to generate video clips for")
            return []

        logger.info(
            f"Starting parallel video generation for {len(scenes)} scenes "
            f"(max concurrent: {max_concurrent})"
        )

        # Build a mapping of scene elements to reference images
        scene_references = self._build_scene_reference_map(script, reference_images)

        # Create results container
        results: list[GeneratedAsset | None] = [None] * len(scenes)
        errors: list[tuple[int, Exception]] = []

        # Semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        # Total scenes for flow context
        total_scene_count = len(scenes)

        async def generate_with_semaphore(
            idx: int,
            scene: SceneAction,
            progress: Progress | None,
            task_id: TaskID | None,
        ) -> None:
            """Generate a single video clip with semaphore control and prompt repair."""
            async with semaphore:
                # Add delay between requests to respect rate limits
                if idx > 0:
                    await asyncio.sleep(inter_request_delay)

                # Get reference images for this scene
                scene_refs = scene_references.get(scene.scene_number, [])

                # Track current scene (may be modified by repair agent)
                current_scene = scene
                last_error: Exception | None = None

                # Try generation with up to max_repair_attempts retries for safety errors
                for attempt in range(max_repair_attempts + 1):
                    try:
                        result = await self.generate_video_clip(
                            scene=current_scene,
                            output_dir=output_dir,
                            reference_images=scene_refs,
                            total_scenes=total_scene_count,
                            script=script,
                        )
                        results[idx] = result

                        if progress and task_id is not None:
                            status = "[green]Scene"
                            if attempt > 0:
                                status = "[yellow]Scene"  # Repaired
                            progress.update(
                                task_id,
                                advance=1,
                                description=f"{status} {scene.scene_number} ✓",
                            )
                        return  # Success, exit the retry loop

                    except PromptSafetyError as e:
                        last_error = e
                        # Check if we have retries left
                        if attempt < max_repair_attempts:
                            logger.warning(
                                f"Scene {scene.scene_number} blocked by safety policy "
                                f"(attempt {attempt + 1}/{max_repair_attempts + 1}), "
                                "attempting prompt repair..."
                            )
                            try:
                                # Import here to avoid circular imports
                                from sip_studio.agents.prompt_repair import (
                                    repair_scene_prompt,
                                )

                                repair_output = await repair_scene_prompt(
                                    scene=current_scene,
                                    error_message=str(e),
                                    attempt_number=attempt + 1,
                                )
                                # Create modified scene with repaired prompts
                                current_scene = SceneAction(
                                    scene_number=scene.scene_number,
                                    duration_seconds=scene.duration_seconds,
                                    setting_description=repair_output.revised_setting_description,
                                    action_description=repair_output.revised_action_description,
                                    dialogue=scene.dialogue,
                                    camera_direction=scene.camera_direction,
                                    shared_element_ids=scene.shared_element_ids,
                                )
                                logger.info(
                                    f"Scene {scene.scene_number} prompt repaired: "
                                    f"{repair_output.changes_made}"
                                )
                            except Exception as repair_error:
                                logger.error(
                                    f"Failed to repair prompt for scene {scene.scene_number}: "
                                    f"{repair_error}"
                                )
                                break  # Exit retry loop on repair failure
                        else:
                            # No more retries
                            logger.error(
                                f"Scene {scene.scene_number} failed after "
                                f"{max_repair_attempts} repair attempts"
                            )
                            break

                    except Exception as e:
                        # Non-safety errors don't get retried with repair
                        last_error = e
                        logger.error(
                            f"Failed to generate video for scene {scene.scene_number}: {e}"
                        )
                        break

                # If we get here, all attempts failed
                if last_error:
                    errors.append((scene.scene_number, last_error))
                    if progress and task_id is not None:
                        progress.update(
                            task_id,
                            advance=1,
                            description=f"[red]Scene {scene.scene_number} ✗",
                        )

        if show_progress:
            # Use Rich progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
            ) as progress:
                task_id = progress.add_task(
                    "[cyan]Generating videos...",
                    total=len(scenes),
                )

                # Create all tasks
                tasks = [
                    generate_with_semaphore(idx, scene, progress, task_id)
                    for idx, scene in enumerate(scenes)
                ]

                # Run all tasks concurrently
                await asyncio.gather(*tasks)
        else:
            # No progress bar
            tasks = [
                generate_with_semaphore(idx, scene, None, None) for idx, scene in enumerate(scenes)
            ]
            await asyncio.gather(*tasks)

        # Filter out None results and sort by scene number
        successful_results = [r for r in results if r is not None]
        successful_results.sort(key=lambda x: x.scene_number or 0)

        logger.info(
            f"Video generation complete: {len(successful_results)}/{len(scenes)} clips generated"
        )

        if errors:
            logger.warning(f"Failed scenes: {[e[0] for e in errors]}")

        return successful_results

    def _build_scene_reference_map(
        self,
        script: VideoScript,
        reference_images: list[GeneratedAsset] | None,
    ) -> dict[int, list[GeneratedAsset]]:
        """Build a mapping of scene numbers to their reference images.

        Args:
            script: The VideoScript with scene and element information.
            reference_images: List of generated reference image assets.

        Returns:
            Dictionary mapping scene numbers to lists of relevant reference images.
        """
        if not reference_images:
            return {}

        # Build element ID to reference image mapping
        element_to_ref: dict[str, GeneratedAsset] = {}
        for ref in reference_images:
            if ref.element_id:
                element_to_ref[ref.element_id] = ref

        # Build scene to reference images mapping
        scene_refs: dict[int, list[GeneratedAsset]] = {}
        for scene in script.scenes:
            refs = []
            for element_id in scene.shared_element_ids:
                if element_id in element_to_ref:
                    refs.append(element_to_ref[element_id])

            # Limit to MAX_REFERENCE_IMAGES per scene
            if refs:
                scene_refs[scene.scene_number] = refs[: self.MAX_REFERENCE_IMAGES]

        return scene_refs


@dataclass
class VideoGenerationResult:
    """Result of parallel video generation."""

    successful: list[GeneratedAsset]
    failed_scenes: list[int]
    total_scenes: int

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_scenes == 0:
            return 0.0
        return len(self.successful) / self.total_scenes * 100

    @property
    def all_succeeded(self) -> bool:
        """Check if all scenes were generated successfully."""
        return len(self.successful) == self.total_scenes
