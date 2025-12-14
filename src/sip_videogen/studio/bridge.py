"""Python bridge exposed to JavaScript."""

import asyncio
import base64
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sip_videogen.advisor.agent import AdvisorProgress, BrandAdvisor
from sip_videogen.brands.memory import list_brand_assets
from sip_videogen.brands.storage import (
    create_brand as storage_create_brand,
)
from sip_videogen.brands.storage import (
    delete_brand as storage_delete_brand,
)
from sip_videogen.brands.storage import (
    get_active_brand,
    get_brand_dir,
    list_brands,
    load_brand_summary,
    set_active_brand,
)

ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
ALLOWED_TEXT_EXTS = {".md", ".txt", ".json", ".yaml", ".yml"}

# Config file for persistent settings (API keys, preferences)
CONFIG_PATH = Path.home() / ".sip-videogen" / "config.json"


def _load_config() -> dict:
    """Load config from disk."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(config: dict) -> None:
    """Save config to disk."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def _load_api_keys_from_config() -> None:
    """Load API keys from config into environment (called on startup)."""
    config = _load_config()
    api_keys = config.get("api_keys", {})
    if api_keys.get("openai") and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = api_keys["openai"]
    if api_keys.get("gemini") and not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = api_keys["gemini"]


# Load keys on module import (app startup)
_load_api_keys_from_config()


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
        """Save API keys to environment and persist to config file.

        Keys are stored in ~/.sip-videogen/config.json for persistence across sessions.
        """
        try:
            # Set in environment for current session
            if openai_key:
                os.environ["OPENAI_API_KEY"] = openai_key
            if gemini_key:
                os.environ["GEMINI_API_KEY"] = gemini_key

            # Persist to config file
            config = _load_config()
            config["api_keys"] = {
                "openai": openai_key or config.get("api_keys", {}).get("openai", ""),
                "gemini": gemini_key or config.get("api_keys", {}).get("gemini", ""),
            }
            _save_config(config)

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

    def delete_brand(self, slug: str) -> dict:
        """Delete a brand and all its files.

        Args:
            slug: Brand identifier to delete.

        Returns:
            Success response or error if brand not found.
        """
        try:
            # Validate brand exists
            entries = list_brands()
            if slug not in [e.slug for e in entries]:
                return BridgeResponse(
                    success=False, error=f"Brand '{slug}' not found"
                ).to_dict()

            # If this is the active brand, clear it
            if self._current_brand == slug:
                self._current_brand = None
                self._advisor = None

            # If this is the globally active brand, clear that too
            if get_active_brand() == slug:
                set_active_brand(None)

            # Delete the brand
            deleted = storage_delete_brand(slug)
            if not deleted:
                return BridgeResponse(
                    success=False, error=f"Failed to delete brand '{slug}'"
                ).to_dict()

            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def create_brand_from_materials(
        self,
        description: str,
        images: list[dict],
        documents: list[dict],
    ) -> dict:
        """Create a new brand using AI agents with user-provided materials.

        Args:
            description: User's text description of the brand concept.
            images: List of dicts with {filename, data} where data is base64.
            documents: List of dicts with {filename, data} where data is base64.

        Returns:
            Success response with {slug} of the new brand, or error.
        """
        from sip_videogen.agents.brand_director import develop_brand_with_output

        print("\n" + "=" * 60)
        print("[CREATE_BRAND] Starting brand creation...")
        print(f"[CREATE_BRAND] Description length: {len(description)} chars")
        print(f"[CREATE_BRAND] Images count: {len(images)}")
        print(f"[CREATE_BRAND] Documents count: {len(documents)}")
        for img in images:
            print(f"[CREATE_BRAND]   Image: {img.get('filename', 'unknown')}")
        for doc in documents:
            print(f"[CREATE_BRAND]   Document: {doc.get('filename', 'unknown')}")
        print("=" * 60)

        try:
            # Build concept from description and document contents
            concept_parts = []

            if description.strip():
                concept_parts.append(f"## Brand Description\n\n{description.strip()}")
                print("[CREATE_BRAND] Added description to concept")

            # Extract text from documents
            for doc in documents:
                filename = doc.get("filename", "unknown")
                data_b64 = doc.get("data", "")
                try:
                    content = base64.b64decode(data_b64).decode("utf-8", errors="replace")
                    print(f"[CREATE_BRAND] Extracted {len(content)} chars from {filename}")
                    # Limit document size (50KB ~= 25 pages)
                    if len(content) > 50 * 1024:
                        content = content[: 50 * 1024] + "\n...[truncated]"
                        print("[CREATE_BRAND]   Truncated to 50KB")
                    concept_parts.append(f"## From: {filename}\n\n{content}")
                except Exception as e:
                    print(f"[CREATE_BRAND] ERROR reading {filename}: {e}")

            if not concept_parts:
                print("[CREATE_BRAND] ERROR: No concept parts - nothing to create from")
                return BridgeResponse(
                    success=False,
                    error="Please provide a description or upload documents.",
                ).to_dict()

            concept = "\n\n---\n\n".join(concept_parts)
            print(f"[CREATE_BRAND] Combined concept length: {len(concept)} chars")

            # The AI has a 5000 character limit - truncate smartly if needed
            max_concept_len = 4800  # Leave some buffer
            if len(concept) > max_concept_len:
                print(f"[CREATE_BRAND] Concept too long ({len(concept)}), truncating...")
                # Prioritize the description, truncate document content
                if description.strip():
                    desc_part = f"## Brand Description\n\n{description.strip()}"
                    remaining = max_concept_len - len(desc_part) - 100
                    if remaining > 500:
                        # Include truncated document summary
                        doc_summary = concept[len(desc_part) :][:remaining]
                        concept = desc_part + "\n\n---\n\n" + doc_summary + "\n...[truncated]"
                    else:
                        concept = desc_part[:max_concept_len]
                else:
                    concept = concept[:max_concept_len] + "\n...[truncated]"
                print(f"[CREATE_BRAND] Final concept length: {len(concept)} chars")

            # Report progress
            self._current_progress = "Creating brand identity..."
            print("[CREATE_BRAND] Calling AI brand director...")
            print("[CREATE_BRAND] This may take 1-2 minutes...")

            # Run brand development (async function)
            output = asyncio.run(develop_brand_with_output(concept))
            brand_identity = output.brand_identity
            print(f"[CREATE_BRAND] AI completed! Brand name: {brand_identity.core.name}")
            print(f"[CREATE_BRAND] Brand slug: {brand_identity.slug}")

            # Save the brand
            self._current_progress = "Saving brand..."
            print("[CREATE_BRAND] Saving brand to storage...")
            storage_create_brand(brand_identity)
            slug = brand_identity.slug
            print(f"[CREATE_BRAND] Brand saved successfully: {slug}")

            # Save uploaded images to the new brand's assets directory
            brand_dir = get_brand_dir(slug)
            assets_dir = brand_dir / "assets"
            docs_dir = brand_dir / "docs"
            print(f"[CREATE_BRAND] Brand directory: {brand_dir}")

            print(f"[CREATE_BRAND] Saving {len(images)} images...")
            for img in images:
                filename = img.get("filename", "")
                data_b64 = img.get("data", "")
                if not filename or not data_b64:
                    continue

                ext = Path(filename).suffix.lower()
                if ext not in ALLOWED_IMAGE_EXTS:
                    print(f"[CREATE_BRAND]   Skipping {filename} (unsupported ext)")
                    continue

                # Determine category from filename or default to logo
                category = "logo" if "logo" in filename.lower() else "marketing"
                target_dir = assets_dir / category
                target_dir.mkdir(parents=True, exist_ok=True)

                target_path = target_dir / filename
                if not target_path.exists():
                    target_path.write_bytes(base64.b64decode(data_b64))
                    print(f"[CREATE_BRAND]   Saved: {category}/{filename}")

            # Save uploaded documents to the brand's docs directory
            print(f"[CREATE_BRAND] Saving {len(documents)} documents...")
            docs_dir.mkdir(parents=True, exist_ok=True)
            for doc in documents:
                filename = doc.get("filename", "")
                data_b64 = doc.get("data", "")
                if not filename or not data_b64:
                    continue

                ext = Path(filename).suffix.lower()
                if ext not in ALLOWED_TEXT_EXTS:
                    print(f"[CREATE_BRAND]   Skipping {filename} (unsupported ext)")
                    continue

                target_path = docs_dir / filename
                if not target_path.exists():
                    target_path.write_bytes(base64.b64decode(data_b64))
                    print(f"[CREATE_BRAND]   Saved: docs/{filename}")

            self._current_progress = ""

            print("[CREATE_BRAND] " + "=" * 40)
            print(f"[CREATE_BRAND] SUCCESS! Brand '{brand_identity.core.name}' created")
            print("[CREATE_BRAND] " + "=" * 40 + "\n")

            return BridgeResponse(
                success=True,
                data={"slug": slug, "name": brand_identity.core.name},
            ).to_dict()

        except ValueError as e:
            print(f"[CREATE_BRAND] ValueError: {e}")
            return BridgeResponse(success=False, error=str(e)).to_dict()
        except Exception as e:
            import traceback
            print(f"[CREATE_BRAND] EXCEPTION: {type(e).__name__}: {e}")
            print("[CREATE_BRAND] Traceback:")
            traceback.print_exc()
            self._current_progress = ""
            return BridgeResponse(success=False, error=f"Failed to create brand: {e}").to_dict()

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
