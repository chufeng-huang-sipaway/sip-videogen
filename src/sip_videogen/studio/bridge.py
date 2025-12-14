"""Python bridge exposed to JavaScript."""

import asyncio
import base64
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from sip_videogen.advisor.agent import BrandAdvisor, AdvisorProgress
from sip_videogen.brands.storage import (
    list_brands,
    load_brand_summary,
    get_active_brand,
    set_active_brand,
    get_brand_dir,
)
from sip_videogen.brands.memory import list_brand_assets


@dataclass
class BridgeResponse:
    """Standard response format for bridge methods."""

    success: bool
    data: Any = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class StudioBridge:
    """API exposed to the frontend via PyWebView."""

    def __init__(self):
        self._advisor: BrandAdvisor | None = None
        self._current_brand: str | None = None
        self._current_progress: str = ""
        self._generated_images: list[str] = []
        self._window = None

    # =========================================================================
    # Path Safety Helper
    # =========================================================================

    def _resolve_safe_path(self, relative_path: str) -> tuple[Path | None, str | None]:
        """Resolve a relative path safely within the brand's assets directory.

        Returns:
            (resolved_path, None) on success
            (None, error_message) on failure
        """
        slug = self._current_brand or get_active_brand()
        if not slug:
            return None, "No brand selected"

        brand_dir = get_brand_dir(slug)
        assets_dir = brand_dir / "assets"

        # Resolve the path and check containment
        try:
            resolved = (assets_dir / relative_path).resolve()
            # Use is_relative_to() for proper containment check (Python 3.9+)
            if not resolved.is_relative_to(assets_dir.resolve()):
                return None, "Invalid path: outside assets directory"
            return resolved, None
        except (ValueError, OSError) as e:
            return None, f"Invalid path: {e}"

    # =========================================================================
    # Configuration / Setup
    # =========================================================================

    def check_api_keys(self) -> dict:
        """Check if required API keys are configured."""
        openai_key = bool(os.environ.get("OPENAI_API_KEY"))
        gemini_key = bool(os.environ.get("GEMINI_API_KEY"))
        return BridgeResponse(
            success=True,
            data={
                "openai": openai_key,
                "gemini": gemini_key,
                "all_configured": openai_key and gemini_key,
            },
        ).to_dict()

    def save_api_keys(self, openai_key: str, gemini_key: str) -> dict:
        """Save API keys to environment (session only).

        NOTE: Keys are not persisted. For a production app, consider:
        - macOS Keychain via `keyring` library
        - Encrypted config file in ~/Library/Application Support/
        """
        try:
            if openai_key:
                os.environ["OPENAI_API_KEY"] = openai_key
            if gemini_key:
                os.environ["GEMINI_API_KEY"] = gemini_key
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    # =========================================================================
    # Brand Management
    # =========================================================================

    def get_brands(self) -> dict:
        """Get list of all available brands."""
        try:
            entries = list_brands()
            brands = [
                {"slug": e.slug, "name": e.name, "category": e.category} for e in entries
            ]
            active = get_active_brand()
            return BridgeResponse(
                success=True, data={"brands": brands, "active": active}
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def set_brand(self, slug: str) -> dict:
        """Set the active brand and initialize advisor."""
        try:
            entries = list_brands()
            if slug not in [e.slug for e in entries]:
                return BridgeResponse(
                    success=False, error=f"Brand '{slug}' not found"
                ).to_dict()

            set_active_brand(slug)
            self._current_brand = slug

            if self._advisor is None:
                self._advisor = BrandAdvisor(
                    brand_slug=slug, progress_callback=self._progress_callback
                )
            else:
                self._advisor.set_brand(slug, preserve_history=False)

            self._generated_images = []
            return BridgeResponse(success=True, data={"slug": slug}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def get_brand_info(self, slug: str | None = None) -> dict:
        """Get detailed brand information.

        Uses BrandSummary for faster loading and correct field access.
        """
        try:
            target_slug = slug or self._current_brand or get_active_brand()
            if not target_slug:
                return BridgeResponse(
                    success=False, error="No brand selected"
                ).to_dict()

            # Use BrandSummary for direct field access
            summary = load_brand_summary(target_slug)
            if not summary:
                return BridgeResponse(
                    success=False, error=f"Brand '{target_slug}' not found"
                ).to_dict()

            return BridgeResponse(
                success=True,
                data={
                    "slug": target_slug,
                    "name": summary.name,
                    "tagline": summary.tagline,
                    "category": summary.category,
                },
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    # =========================================================================
    # Asset Management (Images Only)
    # =========================================================================

    def get_assets(self, slug: str | None = None) -> dict:
        """Get asset tree for a brand.

        NOTE: Only returns image files. Text file management is out of MVP scope.
        """
        try:
            target_slug = slug or self._current_brand or get_active_brand()
            if not target_slug:
                return BridgeResponse(
                    success=False, error="No brand selected"
                ).to_dict()

            categories = [
                "logo",
                "packaging",
                "lifestyle",
                "mascot",
                "marketing",
                "generated",
            ]
            tree = []

            for category in categories:
                assets = list_brand_assets(target_slug, category=category)
                children = []

                for asset in assets:
                    filename = asset["filename"]
                    file_path = Path(asset["path"])
                    size = file_path.stat().st_size if file_path.exists() else 0

                    children.append(
                        {
                            "name": filename,
                            "type": "image",
                            "path": f"{category}/{filename}",
                            "size": size,
                        }
                    )

                tree.append(
                    {
                        "name": category,
                        "type": "folder",
                        "path": category,
                        "children": children,
                    }
                )

            return BridgeResponse(success=True, data={"tree": tree}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def get_asset_thumbnail(self, relative_path: str) -> dict:
        """Get base64-encoded thumbnail for an asset."""
        try:
            resolved, error = self._resolve_safe_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            content = resolved.read_bytes()
            encoded = base64.b64encode(content).decode("utf-8")

            mime_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".svg": "image/svg+xml",
            }
            mime = mime_types.get(resolved.suffix.lower(), "application/octet-stream")

            return BridgeResponse(
                success=True, data={"dataUrl": f"data:{mime};base64,{encoded}"}
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def open_asset_in_finder(self, relative_path: str) -> dict:
        """Open an asset in Finder."""
        import subprocess

        try:
            resolved, error = self._resolve_safe_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            subprocess.run(["open", "-R", str(resolved)], check=True)
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def delete_asset(self, relative_path: str) -> dict:
        """Delete an asset file."""
        try:
            resolved, error = self._resolve_safe_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            if resolved.is_dir():
                return BridgeResponse(
                    success=False, error="Cannot delete folders"
                ).to_dict()

            resolved.unlink()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def rename_asset(self, relative_path: str, new_name: str) -> dict:
        """Rename an asset file."""
        try:
            resolved, error = self._resolve_safe_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            if "/" in new_name or "\\" in new_name:
                return BridgeResponse(
                    success=False, error="Invalid filename"
                ).to_dict()

            new_path = resolved.parent / new_name
            if new_path.exists():
                return BridgeResponse(
                    success=False, error=f"File already exists: {new_name}"
                ).to_dict()

            resolved.rename(new_path)
            return BridgeResponse(
                success=True, data={"newPath": f"{resolved.parent.name}/{new_name}"}
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def upload_asset(
        self, filename: str, data_base64: str, category: str = "generated"
    ) -> dict:
        """Upload a file to brand's assets directory."""
        try:
            slug = self._current_brand or get_active_brand()
            if not slug:
                return BridgeResponse(
                    success=False, error="No brand selected"
                ).to_dict()

            valid_categories = [
                "logo",
                "packaging",
                "lifestyle",
                "mascot",
                "marketing",
                "generated",
            ]
            if category not in valid_categories:
                return BridgeResponse(
                    success=False, error="Invalid category"
                ).to_dict()

            if "/" in filename or "\\" in filename:
                return BridgeResponse(
                    success=False, error="Invalid filename"
                ).to_dict()

            brand_dir = get_brand_dir(slug)
            target_dir = brand_dir / "assets" / category
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / filename
            content = base64.b64decode(data_base64)
            target_path.write_bytes(content)

            return BridgeResponse(
                success=True, data={"path": f"{category}/{filename}"}
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    # =========================================================================
    # Chat
    # =========================================================================

    def _progress_callback(self, progress: AdvisorProgress) -> None:
        """Called by BrandAdvisor during execution."""
        if progress.event_type == "thinking":
            self._current_progress = "Thinking..."
        elif progress.event_type == "tool_start":
            if "generate_image" in progress.message.lower():
                self._current_progress = "Generating image..."
            else:
                self._current_progress = progress.message
        elif progress.event_type == "tool_end":
            if progress.detail and progress.detail.endswith(
                (".png", ".jpg", ".jpeg")
            ):
                self._generated_images.append(progress.detail)
            self._current_progress = ""

    def get_progress(self) -> dict:
        """Get current operation progress.

        NOTE: Polling may not work if PyWebView blocks concurrent calls.
        Test during implementation; fall back to static "Thinking..." if needed.
        """
        return BridgeResponse(
            success=True, data={"status": self._current_progress}
        ).to_dict()

    def chat(self, message: str) -> dict:
        """Send a message to the Brand Advisor."""
        try:
            if self._advisor is None:
                active = get_active_brand()
                if active:
                    self._advisor = BrandAdvisor(
                        brand_slug=active, progress_callback=self._progress_callback
                    )
                    self._current_brand = active
                else:
                    return BridgeResponse(
                        success=False, error="No brand selected"
                    ).to_dict()

            self._generated_images = []
            response = asyncio.run(self._advisor.chat(message))

            # Convert generated images to base64
            image_data_urls = []
            for img_path in self._generated_images:
                try:
                    path = Path(img_path)
                    if path.exists():
                        content = path.read_bytes()
                        encoded = base64.b64encode(content).decode("utf-8")
                        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(
                            path.suffix.lower().lstrip("."), "image/png"
                        )
                        image_data_urls.append(f"data:{mime};base64,{encoded}")
                except Exception:
                    pass

            return BridgeResponse(
                success=True, data={"response": response, "images": image_data_urls}
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def clear_chat(self) -> dict:
        """Clear conversation history."""
        try:
            if self._advisor:
                self._advisor.clear_history()
            self._generated_images = []
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def refresh_brand_memory(self) -> dict:
        """Refresh the agent's brand context."""
        try:
            slug = self._current_brand or get_active_brand()
            if not slug:
                return BridgeResponse(
                    success=False, error="No brand selected"
                ).to_dict()

            if self._advisor is None:
                self._advisor = BrandAdvisor(
                    brand_slug=slug, progress_callback=self._progress_callback
                )
            else:
                self._advisor.set_brand(slug, preserve_history=True)

            return BridgeResponse(
                success=True, data={"message": "Brand context refreshed"}
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()
