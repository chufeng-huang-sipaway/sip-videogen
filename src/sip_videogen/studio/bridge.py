"""Python bridge exposed to JavaScript - thin facade delegating to services."""

from ..constants import (
    ALLOWED_IMAGE_EXTS,
    ALLOWED_TEXT_EXTS,
    ALLOWED_VIDEO_EXTS,
    ASSET_CATEGORIES,
    MIME_TYPES,
    VIDEO_MIME_TYPES,
)
from .services.asset_service import AssetService
from .services.brand_service import BrandService
from .services.chat_service import ChatService
from .services.document_service import DocumentService
from .services.image_status import ImageStatusService
from .services.product_service import ProductService
from .services.project_service import ProjectService
from .services.style_reference_service import StyleReferenceService
from .services.update_service import UpdateService
from .state import BridgeState
from .utils.bridge_types import bridge_error, bridge_ok
from .utils.config_store import check_api_keys as do_check_api_keys
from .utils.config_store import load_api_keys_from_config
from .utils.config_store import save_api_keys as do_save_api_keys


class StudioBridge:
    """API exposed to the frontend via PyWebView."""

    def __init__(self):
        # Load API keys on bridge initialization rather than module import, to avoid
        # side effects when the module is imported (e.g., during tests).
        load_api_keys_from_config()
        self._state = BridgeState()
        self._brand = BrandService(self._state)
        self._document = DocumentService(self._state)
        self._asset = AssetService(self._state)
        self._product = ProductService(self._state)
        self._project = ProjectService(self._state)
        self._style_reference = StyleReferenceService(self._state)
        self._chat = ChatService(self._state)
        self._update = UpdateService(self._state)
        self._image_status = ImageStatusService(self._state)

    def set_window(self, window):
        self._state.window = window

    # ===========================================================================
    # Constants (Single Source of Truth)
    # ===========================================================================
    def get_constants(self) -> dict:
        """Return all constants for frontend consumption. Sets converted to sorted lists."""
        return bridge_ok(
            {
                "asset_categories": list(ASSET_CATEGORIES),
                "allowed_image_exts": sorted(ALLOWED_IMAGE_EXTS),
                "allowed_video_exts": sorted(ALLOWED_VIDEO_EXTS),
                "allowed_text_exts": sorted(ALLOWED_TEXT_EXTS),
                "mime_types": MIME_TYPES,
                "video_mime_types": VIDEO_MIME_TYPES,
            }
        )

    # ===========================================================================
    # Configuration / Setup
    # ===========================================================================
    def check_api_keys(self) -> dict:
        """Check if required API keys are configured."""
        return bridge_ok(do_check_api_keys())

    def save_api_keys(self, openai_key: str, gemini_key: str, firecrawl_key: str = "") -> dict:
        """Save API keys to environment and persist to config file."""
        try:
            do_save_api_keys(openai_key, gemini_key, firecrawl_key)
            return bridge_ok()
        except Exception as e:
            return bridge_error(str(e))

    # ===========================================================================
    # Brand Management
    # ===========================================================================
    def get_brands(self) -> dict:
        return self._brand.get_brands()

    def set_brand(self, slug: str) -> dict:
        return self._brand.set_brand(slug)

    def get_brand_info(self, slug: str | None = None) -> dict:
        return self._brand.get_brand_info(slug)

    def get_brand_identity(self) -> dict:
        return self._brand.get_brand_identity()

    def update_brand_identity_section(self, section: str, data: dict) -> dict:
        return self._brand.update_brand_identity_section(section, data)

    def regenerate_brand_identity(self, confirm: bool) -> dict:
        return self._brand.regenerate_brand_identity(confirm)

    def list_identity_backups(self) -> dict:
        return self._brand.list_identity_backups()

    def restore_identity_backup(self, filename: str) -> dict:
        return self._brand.restore_identity_backup(filename)

    def delete_brand(self, slug: str) -> dict:
        return self._brand.delete_brand(slug)

    def create_brand_from_materials(
        self, description: str, images: list[dict], documents: list[dict]
    ) -> dict:
        return self._brand.create_brand_from_materials(description, images, documents)

    # ===========================================================================
    # Document Management
    # ===========================================================================
    def get_documents(self, slug: str | None = None) -> dict:
        return self._document.get_documents(slug)

    def read_document(self, relative_path: str) -> dict:
        return self._document.read_document(relative_path)

    def upload_document(self, filename: str, data_base64: str) -> dict:
        return self._document.upload_document(filename, data_base64)

    def delete_document(self, relative_path: str) -> dict:
        return self._document.delete_document(relative_path)

    def rename_document(self, relative_path: str, new_name: str) -> dict:
        return self._document.rename_document(relative_path, new_name)

    def open_document_in_finder(self, relative_path: str) -> dict:
        return self._document.open_document_in_finder(relative_path)

    # ===========================================================================
    # Asset Management
    # ===========================================================================
    def get_assets(self, slug: str | None = None) -> dict:
        return self._asset.get_assets(slug)

    def get_asset_thumbnail(self, relative_path: str) -> dict:
        return self._asset.get_asset_thumbnail(relative_path)

    def get_asset_full(self, relative_path: str) -> dict:
        return self._asset.get_asset_full(relative_path)

    def get_image_thumbnail(self, image_path: str) -> dict:
        return self._asset.get_image_thumbnail(image_path)

    def get_image_data(self, image_path: str) -> dict:
        return self._asset.get_image_data(image_path)

    def upload_asset(self, filename: str, data_base64: str, category: str = "generated") -> dict:
        return self._asset.upload_asset(filename, data_base64, category)

    def delete_asset(self, relative_path: str) -> dict:
        return self._asset.delete_asset(relative_path)

    def rename_asset(self, relative_path: str, new_name: str) -> dict:
        return self._asset.rename_asset(relative_path, new_name)

    def open_asset_in_finder(self, relative_path: str) -> dict:
        return self._asset.open_asset_in_finder(relative_path)

    def get_video_path(self, relative_path: str) -> dict:
        return self._asset.get_video_path(relative_path)

    def replace_asset(self, original_path: str, new_path: str) -> dict:
        return self._asset.replace_asset(original_path, new_path)

    def get_video_data(self, relative_path: str) -> dict:
        return self._asset.get_video_data(relative_path)

    def get_image_metadata(self, image_path: str) -> dict:
        return self._asset.get_image_metadata(image_path)

    # ===========================================================================
    # Product Management
    # ===========================================================================
    def get_products(self, brand_slug: str | None = None) -> dict:
        return self._product.get_products(brand_slug)

    def get_product(self, product_slug: str) -> dict:
        return self._product.get_product(product_slug)

    def create_product(
        self,
        name: str,
        description: str,
        images: list[dict] | None = None,
        attributes: list[dict] | None = None,
    ) -> dict:
        return self._product.create_product(name, description, images, attributes)

    def update_product(
        self,
        product_slug: str,
        name: str | None = None,
        description: str | None = None,
        attributes: list[dict] | None = None,
    ) -> dict:
        return self._product.update_product(product_slug, name, description, attributes)

    def delete_product(self, product_slug: str) -> dict:
        return self._product.delete_product(product_slug)

    def get_product_images(self, product_slug: str) -> dict:
        return self._product.get_product_images(product_slug)

    def upload_product_image(self, product_slug: str, filename: str, data_base64: str) -> dict:
        return self._product.upload_product_image(product_slug, filename, data_base64)

    def delete_product_image(self, product_slug: str, filename: str) -> dict:
        return self._product.delete_product_image(product_slug, filename)

    def set_primary_product_image(self, product_slug: str, filename: str) -> dict:
        return self._product.set_primary_product_image(product_slug, filename)

    def get_product_image_thumbnail(self, path: str) -> dict:
        return self._product.get_product_image_thumbnail(path)

    def get_product_image_full(self, path: str) -> dict:
        return self._product.get_product_image_full(path)

    def analyze_product_packaging(self, product_slug: str, force: bool = False) -> dict:
        import asyncio

        return asyncio.run(self._product.analyze_product_packaging(product_slug, force))

    # ===========================================================================
    # Style Reference Management
    # ===========================================================================
    def get_style_references(self, brand_slug: str | None = None) -> dict:
        return self._style_reference.get_style_references(brand_slug)

    def get_style_reference(self, sr_slug: str) -> dict:
        return self._style_reference.get_style_reference(sr_slug)

    def create_style_reference(
        self,
        name: str,
        description: str,
        images: list[dict] | None = None,
        default_strict: bool = True,
    ) -> dict:
        return self._style_reference.create_style_reference(
            name, description, images, default_strict
        )

    def update_style_reference(
        self,
        sr_slug: str,
        name: str | None = None,
        description: str | None = None,
        default_strict: bool | None = None,
    ) -> dict:
        return self._style_reference.update_style_reference(
            sr_slug, name, description, default_strict
        )

    def delete_style_reference(self, sr_slug: str) -> dict:
        return self._style_reference.delete_style_reference(sr_slug)

    def get_style_reference_images(self, sr_slug: str) -> dict:
        return self._style_reference.get_style_reference_images(sr_slug)

    def upload_style_reference_image(self, sr_slug: str, filename: str, data_base64: str) -> dict:
        return self._style_reference.upload_style_reference_image(sr_slug, filename, data_base64)

    def delete_style_reference_image(self, sr_slug: str, filename: str) -> dict:
        return self._style_reference.delete_style_reference_image(sr_slug, filename)

    def set_primary_style_reference_image(self, sr_slug: str, filename: str) -> dict:
        return self._style_reference.set_primary_style_reference_image(sr_slug, filename)

    def get_style_reference_image_thumbnail(self, path: str) -> dict:
        return self._style_reference.get_style_reference_image_thumbnail(path)

    def get_style_reference_image_full(self, path: str) -> dict:
        return self._style_reference.get_style_reference_image_full(path)

    def reanalyze_style_reference(self, sr_slug: str) -> dict:
        return self._style_reference.reanalyze_style_reference(sr_slug)

    # ===========================================================================
    # Project Management
    # ===========================================================================
    def get_projects(self, brand_slug: str | None = None) -> dict:
        return self._project.get_projects(brand_slug)

    def get_project(self, project_slug: str) -> dict:
        return self._project.get_project(project_slug)

    def create_project(self, name: str, instructions: str = "") -> dict:
        return self._project.create_project(name, instructions)

    def update_project(
        self,
        project_slug: str,
        name: str | None = None,
        instructions: str | None = None,
        status: str | None = None,
    ) -> dict:
        return self._project.update_project(project_slug, name, instructions, status)

    def delete_project(self, project_slug: str) -> dict:
        return self._project.delete_project(project_slug)

    def set_active_project(self, project_slug: str | None) -> dict:
        return self._project.set_active_project(project_slug)

    def get_active_project(self) -> dict:
        return self._project.get_active_project()

    def get_project_assets(self, project_slug: str) -> dict:
        return self._project.get_project_assets(project_slug)

    def get_general_assets(self, brand_slug: str | None = None) -> dict:
        return self._project.get_general_assets(brand_slug)

    # ===========================================================================
    # Chat
    # ===========================================================================
    def chat(
        self,
        message: str,
        attachments: list[dict] | None = None,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_style_references: list[dict] | None = None,
        aspect_ratio: str | None = None,
        generation_mode: str | None = None,
    ) -> dict:
        return self._chat.chat(
            message,
            attachments,
            project_slug,
            attached_products,
            attached_style_references,
            aspect_ratio,
            generation_mode,
        )

    def clear_chat(self) -> dict:
        return self._chat.clear_chat()

    def refresh_brand_memory(self) -> dict:
        return self._chat.refresh_brand_memory()

    def get_progress(self) -> dict:
        return self._chat.get_progress()

    # ===========================================================================
    # App Updates
    # ===========================================================================
    def get_app_version(self) -> dict:
        return self._update.get_app_version()

    def check_for_updates(self) -> dict:
        return self._update.check_for_updates()

    def download_and_install_update(self, download_url: str, version: str) -> dict:
        return self._update.download_and_install_update(download_url, version)

    def get_update_progress(self) -> dict:
        return self._update.get_update_progress()

    def skip_update_version(self, version: str) -> dict:
        return self._update.skip_update_version(version)

    def get_update_settings(self) -> dict:
        return self._update.get_update_settings()

    def set_update_check_on_startup(self, enabled: bool) -> dict:
        return self._update.set_update_check_on_startup(enabled)

    # ===========================================================================
    # Image Status (Workstation Curation)
    # ===========================================================================
    def get_unsorted_images(self, brand_slug: str | None = None) -> dict:
        """Get all unsorted images for a brand."""
        slug = brand_slug or self._state.get_active_slug()
        if not slug:
            return bridge_error("No brand selected")
        return self._image_status.list_by_status(slug, "unsorted")

    def mark_image_viewed(self, image_id: str, brand_slug: str | None = None) -> dict:
        """Mark image as viewed (read)."""
        slug = brand_slug or self._state.get_active_slug()
        if not slug:
            return bridge_error("No brand selected")
        return self._image_status.mark_viewed(slug, image_id)

    def register_image(
        self,
        image_path: str,
        brand_slug: str | None = None,
        prompt: str | None = None,
        source_style_reference_path: str | None = None,
    ) -> dict:
        """Register a new image with unsorted status."""
        slug = brand_slug or self._state.get_active_slug()
        if not slug:
            return bridge_error("No brand selected")
        return self._image_status.register_image(
            slug, image_path, prompt, source_style_reference_path
        )

    def register_generated_images(self, images: list[dict], brand_slug: str | None = None) -> dict:
        """Register multiple generated images at once."""
        slug = brand_slug or self._state.get_active_slug()
        if not slug:
            return bridge_error("No brand selected")
        try:
            registered = []
            for img in images:
                path = img.get("path", "")
                prompt = img.get("prompt")
                src = img.get("sourceStyleReferencePath")
                result = self._image_status.register_image(slug, path, prompt, src)
                if result.get("success"):
                    registered.append(result.get("data"))
            return bridge_ok(registered)
        except Exception as e:
            return bridge_error(str(e))

    def cancel_generation(self, brand_slug: str | None = None) -> dict:
        """Cancel ongoing image generation (placeholder for future implementation)."""
        return bridge_ok({"cancelled": True})

    def backfill_images(self, brand_slug: str | None = None) -> dict:
        """Backfill image status from existing folders. Called on brand selection."""
        slug = brand_slug or self._state.get_active_slug()
        if not slug:
            return bridge_error("No brand selected")
        return self._image_status.backfill_from_folders(slug)

    def copy_image_to_clipboard(self, image_path: str) -> dict:
        """Copy image file to system clipboard (macOS)."""
        import subprocess
        from pathlib import Path

        from .utils.os_utils import copy_image_to_clipboard_macos
        from .utils.path_utils import resolve_assets_path

        try:
            path = Path(image_path)
            # Handle relative paths (e.g. "generated/project__image.png")
            if not path.is_absolute():
                brand_dir, err = self._state.get_brand_dir()
                if err:
                    return bridge_error(err)
                resolved, err = resolve_assets_path(brand_dir, image_path)
                if err:
                    return bridge_error(err)
                path = resolved
            if not path.exists():
                return bridge_error(f"File not found: {image_path}")
            copy_image_to_clipboard_macos(path)
            return bridge_ok({"copied": True, "path": str(path)})
        except subprocess.CalledProcessError as e:
            return bridge_error(f"Failed to copy: {e}")
        except Exception as e:
            return bridge_error(str(e))

    def share_image(self, image_path: str) -> dict:
        """Reveal image in Finder."""
        from pathlib import Path

        from .utils.os_utils import reveal_in_file_manager
        from .utils.path_utils import resolve_assets_path

        try:
            path = Path(image_path)
            # Handle relative paths (e.g. "generated/project__image.png")
            if not path.is_absolute():
                brand_dir, err = self._state.get_brand_dir()
                if err:
                    return bridge_error(err)
                resolved, err = resolve_assets_path(brand_dir, image_path)
                if err:
                    return bridge_error(err)
                path = resolved
            if not path.exists():
                return bridge_error(f"File not found: {image_path}")
            reveal_in_file_manager(path)
            return bridge_ok({"shared": True, "path": str(path)})
        except Exception as e:
            return bridge_error(str(e))
