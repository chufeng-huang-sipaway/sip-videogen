"""Quick image generation without chat context."""

from __future__ import annotations

import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sip_studio.brands.storage import get_active_brand, load_product, load_style_reference
from sip_studio.config.logging import get_logger

if TYPE_CHECKING:
    from ..state import BridgeState
logger = get_logger(__name__)
# Dedicated executor for async operations
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="quick_gen")


def _run_async(coro):
    """Run async coroutine in dedicated thread with its own event loop.
    Avoids asyncio.run() issues when called from existing event loop."""

    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    future = _executor.submit(runner)
    return future.result()


class QuickGeneratorService:
    """Direct image generation service."""

    def __init__(self, state: "BridgeState"):
        self._state = state

    def generate(
        self,
        prompt: str,
        product_slug: str | None = None,
        style_reference_slug: str | None = None,
        aspect_ratio: str = "1:1",
        count: int = 1,
    ) -> dict[str, Any]:
        """Generate images directly without chat.
        Args:
            prompt: Image generation prompt
            product_slug: Optional product to include
            style_reference_slug: Optional style reference
            aspect_ratio: Image aspect ratio
            count: Number of images to generate (1-10)
        Returns:
            Dict with generated images list (base64 encoded for frontend display)"""
        # Validate brand
        brand_slug = get_active_brand()
        if not brand_slug:
            return {"success": False, "error": "No brand selected"}
        # Validate count
        count = max(1, min(10, count))
        # Validate product if specified
        if product_slug:
            try:
                product = load_product(brand_slug, product_slug)
                if not product:
                    return {"success": False, "error": f"Product '{product_slug}' not found"}
            except Exception as e:
                return {"success": False, "error": f"Failed to load product: {e}"}
        # Validate style reference if specified
        if style_reference_slug:
            try:
                style_ref = load_style_reference(brand_slug, style_reference_slug)
                if not style_ref:
                    return {
                        "success": False,
                        "error": f"Style reference '{style_reference_slug}' not found",
                    }
            except Exception as e:
                return {"success": False, "error": f"Failed to load style reference: {e}"}
        # Generate images
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for i in range(count):
            try:
                result = _run_async(
                    self._async_generate_single(
                        prompt=prompt,
                        aspect_ratio=aspect_ratio,
                        product_slug=product_slug,
                        style_reference_slug=style_reference_slug,
                    )
                )
                # Convert file path to base64 data URL for frontend
                if result.get("path"):
                    result["data"] = self._path_to_base64(result["path"])
                results.append(result)
            except Exception as e:
                logger.error(f"Quick generate image {i+1}/{count} failed: {e}")
                errors.append({"index": i, "error": str(e)})
        # Determine overall success
        if not results and errors:
            return {"success": False, "error": "All generations failed", "errors": errors}
        return {
            "success": True,
            "images": results,
            "errors": errors if errors else None,
            "generated": len(results),
            "requested": count,
        }

    async def _async_generate_single(
        self,
        prompt: str,
        aspect_ratio: str,
        product_slug: str | None,
        style_reference_slug: str | None,
    ) -> dict[str, Any]:
        """Generate a single image asynchronously."""
        # Use existing image generation implementation
        from sip_studio.advisor.tools.image_tools import _impl_generate_image

        result = await _impl_generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            product_slug=product_slug,
            template_slug=style_reference_slug,
            strict=True,
            validate_identity=bool(product_slug),
        )
        # Result is either a path string or an error string
        if result.startswith("Error"):
            raise RuntimeError(result)
        # Handle warning appended to path
        path = result.split("\n\n")[0] if "\n\n" in result else result
        return {"path": path, "prompt": prompt}

    def _path_to_base64(self, path: str) -> str | None:
        """Convert image path to base64 data URL."""
        try:
            p = Path(path)
            if not p.exists():
                return None
            data = p.read_bytes()
            ext = p.suffix.lower()
            mime = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }.get(ext, "image/png")
            return f"data:{mime};base64,{base64.b64encode(data).decode()}"
        except Exception:
            return None
