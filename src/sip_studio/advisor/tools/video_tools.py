"""Video generation tools."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from agents import function_tool

from sip_studio.config.logging import get_logger
from sip_studio.models.aspect_ratio import validate_aspect_ratio

from . import _common
from .image_tools import _generate_output_filename
from .metadata import load_image_metadata, store_video_metadata
from .session import get_active_aspect_ratio

logger = get_logger(__name__)


async def _impl_generate_video_clip(
    prompt: str | None = None,
    concept_image_path: str | None = None,
    aspect_ratio: str = "1:1",
    duration: int | None = None,
    provider: str = "veo",
) -> str:
    """Implementation of generate_video_clip tool."""
    import time as time_mod

    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    start_time = time_mod.time()
    settings = _common.get_settings()
    brand_dir = _common.get_brand_dir(brand_slug)
    output_dir = brand_dir / "assets" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    active_project = _common.get_active_project(brand_slug)
    video_filename_base = _generate_output_filename(active_project)
    effective_prompt = prompt
    reference_images: list = []
    image_metadata: dict | None = None
    resolved_concept: Path | None = None
    constraints_context: str | None = None
    product_slugs: list[str] = []
    shared_elements: dict = {}
    scene_element_ids: list[str] = []

    def _resolve_reference_path(path_value: str) -> Path | None:
        if not path_value:
            return None
        candidate = Path(path_value)
        if candidate.is_absolute():
            return candidate if candidate.exists() else None
        assets_path = brand_dir / "assets" / path_value
        if assets_path.exists():
            return assets_path
        brand_path = brand_dir / path_value
        if brand_path.exists():
            return brand_path
        return None

    def _split_product_specs_block(text: str) -> tuple[str, str | None]:
        if not text:
            return "", None
        marker = "### PRODUCT SPECS"
        idx = text.find(marker)
        if idx == -1:
            return text.strip(), None
        prompt_core = text[:idx].rstrip()
        specs_block = text[idx:].strip()
        return prompt_core, specs_block if specs_block else None

    def _normalize_element_id(value: str) -> str:
        clean = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")
        return clean or "ref"

    def _derive_product_role_descriptor(product_name: str, index: int) -> str:
        name_lower = (product_name or "").lower()
        if any(keyword in name_lower for keyword in ["jar", "pot"]):
            return "the product jar"
        if "bottle" in name_lower:
            return "the product bottle"
        if "tube" in name_lower:
            return "the product tube"
        if "pump" in name_lower:
            return "the pump bottle"
        for keyword in ["cream", "serum", "toner", "lotion", "oil", "mask", "gel"]:
            if keyword in name_lower:
                return f"the {keyword}"
        return f"product {index}"

    def _build_placeholder_music_brief():
        from sip_studio.models.music import MusicBrief, MusicGenre, MusicMood

        return MusicBrief(
            prompt="Placeholder brief for single-clip generation; no background music is needed.",
            mood=MusicMood.CALM,
            genre=MusicGenre.AMBIENT,
            tempo="moderate",
            instruments=[],
            rationale="Placeholder brief for prompt construction only.",
        )

    if concept_image_path:
        resolved_concept = _resolve_reference_path(concept_image_path)
        if resolved_concept is None:
            return f"Error: Concept image not found: {concept_image_path}"
        image_metadata = load_image_metadata(str(resolved_concept))
        if image_metadata:
            if not effective_prompt:
                effective_prompt = image_metadata.get("prompt")
                if not effective_prompt:
                    effective_prompt = image_metadata.get("original_prompt")
            if effective_prompt:
                logger.info(f"Loaded prompt from concept image: {effective_prompt[:100]}...")
        if not effective_prompt:
            return "Error: No prompt and no prompt in concept image metadata"
        raw_product_slugs = image_metadata.get("product_slugs") if image_metadata else None
        if isinstance(raw_product_slugs, list):
            product_slugs = [str(s).strip() for s in raw_product_slugs if str(s).strip()]
            product_slugs = list(dict.fromkeys(product_slugs))
        ref_details = image_metadata.get("reference_images_detail") if image_metadata else None
        ref_images = image_metadata.get("reference_images") if image_metadata else None
        ref_candidates: list[dict] = []
        if isinstance(ref_details, list):
            for detail in ref_details:
                if not isinstance(detail, dict):
                    continue
                ref_path = detail.get("path")
                if not ref_path:
                    continue
                product_slug = detail.get("product_slug")
                role = detail.get("role")
                kind = "product" if product_slug else "other"
                ref_candidates.append(
                    {"path": ref_path, "kind": kind, "product_slug": product_slug, "role": role}
                )
        elif isinstance(ref_images, list):
            for ref_path in ref_images:
                if ref_path:
                    ref_candidates.append(
                        {"path": ref_path, "kind": "other", "product_slug": None, "role": None}
                    )
        max_refs = 3
        selected_refs: list[dict] = []
        seen_refs: set[str] = set()

        def add_ref(candidate: dict) -> None:
            if len(selected_refs) >= max_refs:
                return
            resolved_path = candidate.get("resolved_path")
            if not resolved_path:
                resolved_path = _resolve_reference_path(candidate.get("path") or "")
            if resolved_path is None:
                return
            key = str(resolved_path)
            if key in seen_refs:
                return
            seen_refs.add(key)
            candidate = {**candidate, "resolved_path": resolved_path}
            selected_refs.append(candidate)

        product_primary = [
            c for c in ref_candidates if c["kind"] == "product" and c.get("role") == "primary"
        ]
        product_secondary = [
            c for c in ref_candidates if c["kind"] == "product" and c.get("role") != "primary"
        ]
        other_refs = [c for c in ref_candidates if c["kind"] == "other"]
        for candidate in product_primary:
            add_ref(candidate)
        if resolved_concept:
            add_ref(
                {
                    "path": str(resolved_concept),
                    "kind": "concept",
                    "product_slug": None,
                    "role": None,
                    "resolved_path": resolved_concept,
                }
            )
        for candidate in product_secondary:
            add_ref(candidate)
        for candidate in other_refs:
            add_ref(candidate)
        if selected_refs:
            from sip_studio.models.assets import AssetType, GeneratedAsset
            from sip_studio.models.script import ElementType, SharedElement

            product_index = 0
            for idx, ref in enumerate(selected_refs, start=1):
                kind = str(ref.get("kind") or "")
                if kind == "product":
                    slug = str(ref.get("product_slug") or "product")
                    element_id = _normalize_element_id(f"product_{slug}")
                    if element_id not in shared_elements:
                        product_index += 1
                        product = _common.load_product(brand_slug, slug)
                        product_name = product.name if product else slug
                        shared_elements[element_id] = SharedElement(
                            id=element_id,
                            element_type=ElementType.PROP,
                            name=product_name,
                            visual_description="Matches the provided reference image exactly.",
                            role_descriptor=_derive_product_role_descriptor(
                                product_name, product_index
                            ),
                            appears_in_scenes=[1],
                        )
                        scene_element_ids.append(element_id)
                elif kind == "concept":
                    element_id = "env_concept_scene"
                    if element_id not in shared_elements:
                        shared_elements[element_id] = SharedElement(
                            id=element_id,
                            element_type=ElementType.ENVIRONMENT,
                            name="scene setting",
                            visual_description="Overall lighting, composition, and environment match the reference image.",
                            role_descriptor="",
                            appears_in_scenes=[1],
                        )
                        scene_element_ids.append(element_id)
                else:
                    element_id = _normalize_element_id(f"ref_{idx}")
                    if element_id not in shared_elements:
                        shared_elements[element_id] = SharedElement(
                            id=element_id,
                            element_type=ElementType.PROP,
                            name="style reference",
                            visual_description="Style and texture anchor from the reference image.",
                            role_descriptor="",
                            appears_in_scenes=[1],
                        )
                        scene_element_ids.append(element_id)
                reference_images.append(
                    GeneratedAsset(
                        asset_type=AssetType.REFERENCE_IMAGE,
                        local_path=str(ref["resolved_path"]),
                        element_id=element_id,
                    )
                )
    if effective_prompt:
        effective_prompt, extracted_specs = _split_product_specs_block(effective_prompt)
        if settings.sip_product_specs_injection and product_slugs:
            from sip_studio.advisor.product_specs import build_product_specs_block

            constraints_context = build_product_specs_block(
                brand_slug=brand_slug,
                product_slugs=product_slugs,
                include_description=False,
                include_constraints=True,
            )
        elif extracted_specs:
            constraints_context = extracted_specs
    if not effective_prompt:
        return "Error: prompt or concept_image_path with metadata required"
    if provider != "veo":
        return f"Error: Provider '{provider}' not supported. Only 'veo' available."
    valid_durations = [4, 6, 8]
    if reference_images:
        duration = 8
    elif duration is None:
        duration = 8
    elif duration not in valid_durations:
        cur_dur = duration  # capture for lambda
        duration = min(valid_durations, key=lambda x: abs(x - cur_dur))
    try:
        from sip_studio.models.script import SceneAction, VideoScript

        scene = SceneAction(
            scene_number=1,
            duration_seconds=duration,
            setting_description="",
            action_description=effective_prompt,
            dialogue="",
            camera_direction="",
            shared_element_ids=scene_element_ids,
        )
        script_context = None
        if shared_elements:
            script_context = VideoScript(
                title="Single clip",
                logline="Single clip generation",
                tone="",
                visual_style="",
                shared_elements=list(shared_elements.values()),
                scenes=[scene],
                music_brief=_build_placeholder_music_brief(),
            )
        from sip_studio.generators.video_generator import VEOVideoGenerator
        from sip_studio.models.assets import AssetType, GeneratedAsset

        generator = VEOVideoGenerator(api_key=settings.gemini_api_key)
        logger.info(f"Generating video with VEO ({duration}s, {aspect_ratio})")
        # Use concept image as start_frame for image-to-video (supports 9:16)
        start_frame_asset = None
        if resolved_concept and resolved_concept.exists():
            start_frame_asset = GeneratedAsset(
                asset_type=AssetType.REFERENCE_IMAGE,
                local_path=str(resolved_concept),
                element_id="start_frame",
            )
            logger.info(f"Using concept image as start frame: {resolved_concept}")
        result = await generator.generate_video_clip(
            scene=scene,
            output_dir=str(output_dir),
            reference_images=None,  # Don't use reference_images with start_frame
            aspect_ratio=aspect_ratio,
            script=script_context,
            constraints_context=constraints_context,
            start_frame=start_frame_asset,
        )
        if result and result.local_path:
            output_path = Path(result.local_path)
            target_path = output_dir / f"{video_filename_base}.mp4"
            if output_path != target_path:
                output_path.replace(target_path)
            gen_time = int((time_mod.time() - start_time) * 1000)
            video_meta: dict[str, object] = {
                "prompt": effective_prompt,
                "concept_image_path": concept_image_path,
                "aspect_ratio": aspect_ratio,
                "duration": duration,
                "provider": provider,
                "project_slug": active_project,
                "generated_at": datetime.utcnow().isoformat(),
                "generation_time_ms": gen_time,
            }
            if reference_images:
                video_meta["reference_images"] = [asset.local_path for asset in reference_images]
            if constraints_context:
                video_meta["constraints_context"] = constraints_context
            if image_metadata:
                video_meta["source_image_metadata"] = image_metadata
            store_video_metadata(str(target_path), video_meta)
            deleted_paths = set()
            if resolved_concept and resolved_concept.exists():
                try:
                    resolved_concept.unlink()
                    deleted_paths.add(str(resolved_concept))
                    logger.info(f"Deleted concept image: {resolved_concept}")
                    meta_sidecar = resolved_concept.with_suffix(".meta.json")
                    if meta_sidecar.exists():
                        meta_sidecar.unlink()
                except OSError as del_err:
                    logger.warning(f"Failed to delete concept image {resolved_concept}: {del_err}")
            if effective_prompt and output_dir.exists():
                import json as json_mod

                for meta_file in output_dir.glob("*.meta.json"):
                    try:
                        img_path = meta_file.with_suffix(".png")
                        if not img_path.exists() or str(img_path) in deleted_paths:
                            continue
                        with open(meta_file) as f:
                            meta_data = json_mod.load(f)
                        if meta_data.get("prompt") == effective_prompt:
                            img_path.unlink()
                            meta_file.unlink()
                            deleted_paths.add(str(img_path))
                            logger.info(f"Deleted concept variant: {img_path}")
                    except Exception:
                        pass
            logger.info(f"Video clip saved to: {target_path}")
            return str(target_path)
        return "Error: Video generation did not produce a file"
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        return f"Error generating video: {str(e)}"


@function_tool
async def generate_video_clip(
    prompt: str | None = None,
    concept_image_path: str | None = None,
    aspect_ratio: Literal["1:1", "16:9", "9:16", "5:3", "3:5", "4:3", "3:4", "3:2", "2:3"]
    | None = None,
    duration: int | None = None,
    provider: Literal["veo"] = "veo",
) -> str:
    """Generate a single video clip using VEO 3.1.
    Args:
        prompt: Video description with motion/action details.
        concept_image_path: Path to a concept image generated by generate_image.
        aspect_ratio: Video aspect ratio. Uses session context if not specified.
        duration: Clip duration in seconds (4, 6, or 8). Forced to 8 with refs.
        provider: Video generation provider. Only "veo" is supported.
    Returns:
        Path to the saved video file (.mp4), or error message.
    """
    # Session aspect ratio is source of truth (set by UI before agent runs)
    session_ratio = get_active_aspect_ratio()
    validated = validate_aspect_ratio(session_ratio)
    effective_ratio = validated.value
    if aspect_ratio and aspect_ratio != effective_ratio:
        logger.debug(f"Using session aspect_ratio={effective_ratio} (LLM suggested {aspect_ratio})")
    return await _impl_generate_video_clip(
        prompt, concept_image_path, effective_ratio, duration, provider
    )
