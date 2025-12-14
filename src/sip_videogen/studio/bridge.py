"""Python bridge exposed to JavaScript."""

import asyncio
import base64
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sip_videogen.advisor.agent import AdvisorProgress, BrandAdvisor
from sip_videogen.brands.memory import list_brand_assets
from sip_videogen.brands.storage import (
    get_active_brand,
    get_brand_dir,
    list_brands,
    load_brand_summary,
    set_active_brand,
)

ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
ALLOWED_TEXT_EXTS = {".md", ".txt", ".json", ".yaml", ".yml"}


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
        self._window = None

    # =========================================================================
    # Path Safety Helpers
    # =========================================================================

    def _get_active_slug(self) -> str | None:
        """Get the active brand slug (bridge-local, falling back to global)."""
        return self._current_brand or get_active_brand()

    def _get_brand_dir(self) -> tuple[Path | None, str | None]:
        """Get the active brand directory."""
        slug = self._get_active_slug()
        if not slug:
            return None, "No brand selected"
        return get_brand_dir(slug), None

    def _resolve_in_dir(self, base_dir: Path, relative_path: str) -> tuple[Path | None, str | None]:
        """Resolve a path safely within a base directory (prevents path traversal)."""
        try:
            resolved = (base_dir / relative_path).resolve()
            if not resolved.is_relative_to(base_dir.resolve()):
                return None, "Invalid path: outside allowed directory"
            return resolved, None
        except (ValueError, OSError) as e:
            return None, f"Invalid path: {e}"

    def _resolve_assets_path(self, relative_path: str) -> tuple[Path | None, str | None]:
        """Resolve a path inside the brand's assets directory."""
        brand_dir, err = self._get_brand_dir()
        if err:
            return None, err
        return self._resolve_in_dir(brand_dir / "assets", relative_path)

    def _resolve_docs_path(self, relative_path: str) -> tuple[Path | None, str | None]:
        """Resolve a path inside the brand's docs directory."""
        brand_dir, err = self._get_brand_dir()
        if err:
            return None, err
        return self._resolve_in_dir(brand_dir / "docs", relative_path)

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
            brands = [{"slug": e.slug, "name": e.name, "category": e.category} for e in entries]
            active = get_active_brand()
            return BridgeResponse(success=True, data={"brands": brands, "active": active}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def set_brand(self, slug: str) -> dict:
        """Set the active brand and initialize advisor."""
        try:
            entries = list_brands()
            if slug not in [e.slug for e in entries]:
                return BridgeResponse(success=False, error=f"Brand '{slug}' not found").to_dict()

            set_active_brand(slug)
            self._current_brand = slug

            if self._advisor is None:
                self._advisor = BrandAdvisor(
                    brand_slug=slug, progress_callback=self._progress_callback
                )
            else:
                self._advisor.set_brand(slug, preserve_history=False)

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
                return BridgeResponse(success=False, error="No brand selected").to_dict()

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
    # Document Management (Text Files)
    # =========================================================================

    def get_documents(self, slug: str | None = None) -> dict:
        """List brand documents (text files) under docs/.

        Returns:
            {"success": True, "data": {"documents": [{"name": ..., "path": ..., "size": ...}, ...]}}
        """
        try:
            target_slug = slug or self._current_brand or get_active_brand()
            if not target_slug:
                return BridgeResponse(success=False, error="No brand selected").to_dict()

            docs_dir = get_brand_dir(target_slug) / "docs"
            if not docs_dir.exists():
                return BridgeResponse(success=True, data={"documents": []}).to_dict()

            documents: list[dict] = []
            for path in sorted(docs_dir.rglob("*")):
                if not path.is_file():
                    continue
                if path.name.startswith("."):
                    continue
                if path.suffix.lower() not in ALLOWED_TEXT_EXTS:
                    continue

                rel = str(path.relative_to(docs_dir))
                documents.append(
                    {
                        "name": path.name,
                        "path": rel,
                        "size": path.stat().st_size,
                    }
                )

            return BridgeResponse(success=True, data={"documents": documents}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def read_document(self, relative_path: str) -> dict:
        """Read a document's text content (read-only preview)."""
        try:
            resolved, error = self._resolve_docs_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Document not found").to_dict()

            if resolved.suffix.lower() not in ALLOWED_TEXT_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            # Basic safety limit to avoid returning huge files to the UI
            max_bytes = 512 * 1024  # 512 KB
            if resolved.stat().st_size > max_bytes:
                return BridgeResponse(
                    success=False,
                    error="Document too large to preview (limit: 512KB)",
                ).to_dict()

            content = resolved.read_text(encoding="utf-8", errors="replace")
            return BridgeResponse(
                success=True,
                data={"content": content},
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def open_document_in_finder(self, relative_path: str) -> dict:
        """Reveal a document in Finder."""
        import subprocess

        try:
            resolved, error = self._resolve_docs_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Document not found").to_dict()

            subprocess.run(["open", "-R", str(resolved)], check=True)
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def delete_document(self, relative_path: str) -> dict:
        """Delete a document file."""
        try:
            resolved, error = self._resolve_docs_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Document not found").to_dict()

            if resolved.is_dir():
                return BridgeResponse(success=False, error="Cannot delete folders").to_dict()

            resolved.unlink()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def rename_document(self, relative_path: str, new_name: str) -> dict:
        """Rename a document file."""
        try:
            resolved, error = self._resolve_docs_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Document not found").to_dict()

            if "/" in new_name or "\\" in new_name:
                return BridgeResponse(success=False, error="Invalid filename").to_dict()

            if Path(new_name).suffix.lower() not in ALLOWED_TEXT_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            new_path = resolved.parent / new_name
            if new_path.exists():
                return BridgeResponse(
                    success=False, error=f"File already exists: {new_name}"
                ).to_dict()

            resolved.rename(new_path)
            brand_dir, err = self._get_brand_dir()
            if err:
                return BridgeResponse(success=False, error=err).to_dict()
            rel = str(new_path.relative_to(brand_dir / "docs"))
            return BridgeResponse(success=True, data={"newPath": rel}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def upload_document(self, filename: str, data_base64: str) -> dict:
        """Upload a document into docs/ (text-only)."""
        try:
            brand_dir, err = self._get_brand_dir()
            if err:
                return BridgeResponse(success=False, error=err).to_dict()

            if "/" in filename or "\\" in filename:
                return BridgeResponse(success=False, error="Invalid filename").to_dict()

            if Path(filename).suffix.lower() not in ALLOWED_TEXT_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            docs_dir = brand_dir / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            target_path = docs_dir / filename
            if target_path.exists():
                return BridgeResponse(
                    success=False, error=f"File already exists: {filename}"
                ).to_dict()

            content = base64.b64decode(data_base64)
            target_path.write_bytes(content)

            return BridgeResponse(success=True, data={"path": filename}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    # =========================================================================
    # Asset Management (Images)
    # =========================================================================

    def get_assets(self, slug: str | None = None) -> dict:
        """Get asset tree for a brand.

        NOTE: Images are listed via list_brand_assets(). Documents are handled by get_documents().
        """
        try:
            target_slug = slug or self._current_brand or get_active_brand()
            if not target_slug:
                return BridgeResponse(success=False, error="No brand selected").to_dict()

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
            resolved, error = self._resolve_assets_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            suffix = resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            # SVG: return as-is (thumbnailing SVG is non-trivial without extra deps)
            if suffix == ".svg":
                content = resolved.read_bytes()
                encoded = base64.b64encode(content).decode("utf-8")
                return BridgeResponse(
                    success=True,
                    data={"dataUrl": f"data:image/svg+xml;base64,{encoded}"},
                ).to_dict()

            # Raster images: generate a real thumbnail to reduce payload size
            import io

            from PIL import Image

            with Image.open(resolved) as img:
                img = img.convert("RGBA")
                img.thumbnail((256, 256))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode("utf-8")

            return BridgeResponse(
                success=True,
                data={"dataUrl": f"data:image/png;base64,{encoded}"},
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def open_asset_in_finder(self, relative_path: str) -> dict:
        """Open an asset in Finder."""
        import subprocess

        try:
            resolved, error = self._resolve_assets_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            if resolved.suffix.lower() not in ALLOWED_IMAGE_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            subprocess.run(["open", "-R", str(resolved)], check=True)
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def delete_asset(self, relative_path: str) -> dict:
        """Delete an asset file."""
        try:
            resolved, error = self._resolve_assets_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            if resolved.is_dir():
                return BridgeResponse(success=False, error="Cannot delete folders").to_dict()

            if resolved.suffix.lower() not in ALLOWED_IMAGE_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            resolved.unlink()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def rename_asset(self, relative_path: str, new_name: str) -> dict:
        """Rename an asset file."""
        try:
            resolved, error = self._resolve_assets_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            if resolved.suffix.lower() not in ALLOWED_IMAGE_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            if "/" in new_name or "\\" in new_name:
                return BridgeResponse(success=False, error="Invalid filename").to_dict()

            if Path(new_name).suffix.lower() not in ALLOWED_IMAGE_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

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

    def upload_asset(self, filename: str, data_base64: str, category: str = "generated") -> dict:
        """Upload a file to brand's assets directory."""
        try:
            slug = self._current_brand or get_active_brand()
            if not slug:
                return BridgeResponse(success=False, error="No brand selected").to_dict()

            valid_categories = [
                "logo",
                "packaging",
                "lifestyle",
                "mascot",
                "marketing",
                "generated",
            ]
            if category not in valid_categories:
                return BridgeResponse(success=False, error="Invalid category").to_dict()

            if "/" in filename or "\\" in filename:
                return BridgeResponse(success=False, error="Invalid filename").to_dict()

            if Path(filename).suffix.lower() not in ALLOWED_IMAGE_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            brand_dir = get_brand_dir(slug)
            target_dir = brand_dir / "assets" / category
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / filename
            if target_path.exists():
                return BridgeResponse(
                    success=False, error=f"File already exists: {filename}"
                ).to_dict()

            content = base64.b64decode(data_base64)
            target_path.write_bytes(content)

            return BridgeResponse(success=True, data={"path": f"{category}/{filename}"}).to_dict()
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
            self._current_progress = ""

    def get_progress(self) -> dict:
        """Get current operation progress.

        NOTE: Polling may not work if PyWebView blocks concurrent calls.
        Test during implementation; fall back to static "Thinking..." if needed.
        """
        return BridgeResponse(success=True, data={"status": self._current_progress}).to_dict()

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
                    return BridgeResponse(success=False, error="No brand selected").to_dict()

            slug = self._get_active_slug()
            if not slug:
                return BridgeResponse(success=False, error="No brand selected").to_dict()

            # Snapshot generated assets before running (robust vs relying on progress hook details)
            before = {a["path"] for a in list_brand_assets(slug, category="generated")}

            response = asyncio.run(self._advisor.chat(message))

            after = {a["path"] for a in list_brand_assets(slug, category="generated")}
            new_paths = sorted(after - before)

            # Convert new images to base64 data URLs (cap to avoid huge responses)
            image_data_urls: list[str] = []
            for img_path in new_paths[:4]:
                try:
                    path = Path(img_path)
                    if not path.exists():
                        continue
                    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                        continue
                    content = path.read_bytes()
                    encoded = base64.b64encode(content).decode("utf-8")
                    mime = {
                        ".png": "image/png",
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".webp": "image/webp",
                    }.get(path.suffix.lower(), "image/png")
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
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def refresh_brand_memory(self) -> dict:
        """Refresh the agent's brand context."""
        try:
            slug = self._current_brand or get_active_brand()
            if not slug:
                return BridgeResponse(success=False, error="No brand selected").to_dict()

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
