"""Image generation metadata for debugging visibility."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from sip_videogen.config.logging import get_logger
from sip_videogen.utils.file_utils import write_atomically

logger = get_logger(__name__)


@dataclass
class ImageGenerationMetadata:
    """Metadata captured during image generation for debugging visibility."""

    prompt: str
    original_prompt: str
    model: str
    aspect_ratio: str
    image_size: str
    reference_image: str | None
    product_slugs: list[str]
    validate_identity: bool
    generated_at: str
    generation_time_ms: int
    api_call_code: str
    reference_images: list[str] = field(default_factory=list)
    reference_images_detail: list[dict] = field(default_factory=list)
    validation_passed: bool | None = None
    validation_warning: str | None = None
    validation_attempts: int | None = None
    final_attempt_number: int | None = None
    attempts: list[dict] = field(default_factory=list)
    request_payload: dict | None = None


def _build_api_call_code(
    prompt: str,
    model: str,
    aspect_ratio: str,
    image_size: str,
    reference_images: list[str] | None = None,
    grouped_reference_images: list[tuple[str, list[str]]] | None = None,
) -> str:
    """Build a string representation of the actual API call for debugging."""
    prompt_escaped = prompt.replace('"""', '\\"\\"\\"')
    if grouped_reference_images:
        contents_lines = ["[", f'    """{prompt_escaped}""",']
        img_idx = 1
        for product_name, paths in grouped_reference_images:
            img_count = len(paths)
            plural = "s" if img_count > 1 else ""
            label = f"[Reference images for {product_name} ({img_count} image{plural}):]"
            contents_lines.append(f'    "{label}",')
            for ref_path in paths:
                ref_comment = f"  # Loaded from: {ref_path}"
                contents_lines.append(
                    f"    PILImage.open(io.BytesIO(reference_image_bytes_{img_idx})),{ref_comment}"
                )
                img_idx += 1
        contents_lines.append("]")
        contents_repr = "\n".join(contents_lines)
    elif reference_images:
        reference_images = [path for path in reference_images if path]
        contents_lines = ["[", f'    """{prompt_escaped}""",']
        for idx, ref_path in enumerate(reference_images, start=1):
            ref_comment = f"  # Loaded from: {ref_path}"
            contents_lines.append(
                f"    PILImage.open(io.BytesIO(reference_image_bytes_{idx})),{ref_comment}"
            )
        contents_lines.append("]")
        contents_repr = "\n".join(contents_lines)
    else:
        contents_repr = f'"""{prompt_escaped}"""'
    return f"""client.models.generate_content(
    model="{model}",
    contents={contents_repr},
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio="{aspect_ratio}",
            image_size="{image_size}",
        ),
    ),
)"""


def _build_request_payload(
    prompt: str,
    model: str,
    aspect_ratio: str,
    image_size: str,
    reference_images: list[str] | None = None,
    grouped_reference_images: list[tuple[str, list[str]]] | None = None,
) -> dict:
    """Build a structured representation of the generate_content request."""
    if grouped_reference_images:
        contents_items: list[dict] = [{"type": "prompt", "text": prompt}]
        for product_name, paths in grouped_reference_images:
            img_count = len(paths)
            plural = "s" if img_count > 1 else ""
            label = f"[Reference images for {product_name} ({img_count} image{plural}):]"
            contents_items.append({"type": "label", "text": label})
            for path in paths:
                contents_items.append({"type": "image", "path": path})
        contents = {"items": contents_items}
    else:
        contents = {"prompt": prompt, "reference_images": reference_images or []}  # type: ignore[dict-item]
    return {
        "model": model,
        "contents": contents,
        "config": {
            "response_modalities": ["IMAGE"],
            "image_config": {"aspect_ratio": aspect_ratio, "image_size": image_size},
        },
    }


def _build_attempts_metadata(
    attempts: list[dict],
    model: str,
    aspect_ratio: str,
    image_size: str,
    reference_images: list[str] | None = None,
    grouped_reference_images: list[tuple[str, list[str]]] | None = None,
) -> list[dict]:
    """Attach API call details to each attempt record."""
    enriched_attempts: list[dict] = []
    for attempt in attempts:
        prompt = attempt.get("prompt")
        enriched = dict(attempt)
        if prompt:
            enriched["api_call_code"] = _build_api_call_code(
                prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_images=reference_images,
                grouped_reference_images=grouped_reference_images,
            )
            enriched["request_payload"] = _build_request_payload(
                prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_images=reference_images,
                grouped_reference_images=grouped_reference_images,
            )
        enriched_attempts.append(enriched)
    return enriched_attempts


# Module-level storage for metadata (keyed by output path)
_image_metadata: dict[str, dict] = {}


def _get_metadata_path(image_path: str) -> Path:
    """Get the .meta.json path for an image."""
    p = Path(image_path)
    return p.with_suffix(".meta.json")


def store_image_metadata(path: str, metadata: ImageGenerationMetadata) -> None:
    """Store metadata for a generated image (in memory and on disk)."""
    import json

    data = asdict(metadata)
    _image_metadata[path] = data
    try:
        meta_path = _get_metadata_path(path)
        write_atomically(meta_path, json.dumps(data, indent=2))
        logger.debug(f"Saved image metadata to {meta_path}")
    except Exception as e:
        logger.warning(f"Failed to save image metadata: {e}")


def get_image_metadata(path: str) -> dict | None:
    """Get and remove metadata for a generated image from memory."""
    return _image_metadata.pop(path, None)


def load_image_metadata(path: str) -> dict | None:
    """Load metadata for an image from disk (.meta.json file)."""
    import json

    meta_path = _get_metadata_path(path)
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text())
    except Exception as e:
        logger.warning(f"Failed to load image metadata from {meta_path}: {e}")
        return None


# Video metadata storage
_video_metadata: dict[str, dict] = {}


def store_video_metadata(path: str, metadata: dict) -> None:
    """Store metadata for a generated video (in memory and on disk)."""
    import json

    _video_metadata[path] = metadata
    try:
        meta_path = Path(path).with_suffix(".meta.json")
        write_atomically(meta_path, json.dumps(metadata, indent=2))
        logger.debug(f"Saved video metadata to {meta_path}")
    except Exception as e:
        logger.warning(f"Failed to save video metadata: {e}")


def get_video_metadata(path: str) -> dict | None:
    """Get and remove video metadata from memory."""
    return _video_metadata.pop(path, None)


def load_video_metadata(path: str) -> dict | None:
    """Load video metadata from disk (.meta.json file)."""
    import json

    meta_path = Path(path).with_suffix(".meta.json")
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text())
    except Exception as e:
        logger.warning(f"Failed to load video metadata from {meta_path}: {e}")
        return None
