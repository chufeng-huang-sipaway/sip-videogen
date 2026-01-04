"""Brand management service."""

from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime
from pathlib import Path

from sip_videogen.brands.models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIdentityFull,
    BrandIndexEntry,
    CompetitivePositioning,
    VisualIdentity,
    VoiceGuidelines,
)
from sip_videogen.brands.storage import (
    backup_brand_identity,
    get_brand_dir,
    list_brand_backups,
    list_brands,
    load_brand,
    load_brand_summary,
    restore_brand_backup,
    save_asset,
    save_brand,
    save_document,
)
from sip_videogen.brands.storage import create_brand as storage_create_brand
from sip_videogen.brands.storage import delete_brand as storage_delete_brand

from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_IMAGE_EXTS, ALLOWED_TEXT_EXTS, bridge_error, bridge_ok

logger = logging.getLogger(__name__)


class BrandService:
    """Brand CRUD and identity management."""

    def __init__(self, state: BridgeState):
        self._state = state

    def _sync_brand_index(self) -> None:
        """Sync index.json with actual brand directories on disk."""
        from sip_videogen.brands.storage import get_brands_dir, load_index, save_index

        try:
            brands_dir = get_brands_dir()
            if not brands_dir.exists():
                return
            index = load_index()
            changed = False
            valid = []
            for entry in index.brands:
                brand_dir = brands_dir / entry.slug
                if brand_dir.exists() and (brand_dir / "identity.json").exists():
                    valid.append(entry)
                else:
                    logger.info("Removing orphaned entry: %s", entry.slug)
                    changed = True
            for item in brands_dir.iterdir():
                if not item.is_dir() or item.name.startswith("."):
                    continue
                if item.name not in [e.slug for e in valid]:
                    summary = load_brand_summary(item.name)
                    if summary:
                        logger.info("Adding missing entry: %s", item.name)
                        entry = BrandIndexEntry(
                            slug=summary.slug,
                            name=summary.name,
                            category=summary.category,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        valid.append(entry)
                        changed = True
            if changed:
                index.brands = valid
                if index.active_brand and index.active_brand not in [e.slug for e in valid]:
                    logger.info("Clearing invalid active brand: %s", index.active_brand)
                    index.active_brand = valid[0].slug if valid else None
                save_index(index)
                logger.info("Index updated with %d brands", len(valid))
        except Exception as e:
            logger.error("Error syncing index: %s", e)

    def _get_progress_callback(self):
        """Get progress callback function for advisor."""
        import time

        def cb(progress):
            event = {
                "type": progress.event_type,
                "timestamp": int(time.time() * 1000),
                "message": progress.message,
                "detail": progress.detail or "",
            }
            self._state.execution_trace.append(event)
            if progress.event_type == "skill_loaded":
                skill_name = progress.message.replace("Loading ", "").replace(" skill", "")
                if skill_name not in self._state.matched_skills:
                    self._state.matched_skills.append(skill_name)
            if progress.event_type == "tool_end":
                self._state.current_progress = ""
                self._state.current_progress_type = ""
            else:
                self._state.current_progress = progress.message
                self._state.current_progress_type = progress.event_type

        return cb

    def _trigger_background_packaging_analysis(self, slug: str) -> None:
        """Trigger background packaging text analysis for all products."""
        import threading

        def run():
            import asyncio

            from sip_videogen.advisor.tools import _impl_analyze_all_product_packaging

            try:
                if self._state.background_analysis_slug != slug:
                    return
                asyncio.run(
                    _impl_analyze_all_product_packaging(
                        skip_existing=True, skip_human_edited=True, max_products=9999
                    )
                )
            except Exception as e:
                logger.debug("Background packaging analysis: %s", e)
            finally:
                if self._state.background_analysis_slug == slug:
                    self._state.background_analysis_slug = None

        self._state.background_analysis_slug = slug
        threading.Thread(target=run, daemon=True).start()

    def get_brands(self) -> dict:
        """Get list of all available brands."""
        try:
            self._sync_brand_index()
            entries = list_brands()
            brands = [{"slug": e.slug, "name": e.name, "category": e.category} for e in entries]
            active = self._state.get_active_slug()
            logger.info("Found %d brands: %s", len(brands), [b["slug"] for b in brands])
            logger.info("Active brand: %s", active)
            return bridge_ok({"brands": brands, "active": active})
        except Exception as e:
            logger.exception("Error getting brands: %s", e)
            return bridge_error(str(e))

    def set_brand(self, slug: str) -> dict:
        """Set the active brand and initialize advisor."""
        from sip_videogen.advisor.agent import BrandAdvisor

        try:
            entries = list_brands()
            if slug not in [e.slug for e in entries]:
                return bridge_error(f"Brand '{slug}' not found")
            self._state.set_active_slug(slug)
            if self._state.advisor is None:
                self._state.advisor = BrandAdvisor(
                    brand_slug=slug, progress_callback=self._get_progress_callback()
                )
            else:
                self._state.advisor.set_brand(slug, preserve_history=False)
            self._trigger_background_packaging_analysis(slug)
            return bridge_ok({"slug": slug})
        except Exception as e:
            return bridge_error(str(e))

    def get_brand_info(self, slug: str | None = None) -> dict:
        """Get detailed brand information."""
        try:
            target = slug or self._state.get_active_slug()
            if not target:
                return bridge_error("No brand selected")
            summary = load_brand_summary(target)
            if not summary:
                return bridge_error(f"Brand '{target}' not found")
            return bridge_ok(
                {
                    "slug": target,
                    "name": summary.name,
                    "tagline": summary.tagline,
                    "category": summary.category,
                }
            )
        except Exception as e:
            return bridge_error(str(e))

    def get_brand_identity(self) -> dict:
        """Get full brand identity (L1 data) for the active brand."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            identity = load_brand(slug)
            if not identity:
                return bridge_error(f"Brand '{slug}' not found")
            return bridge_ok(identity.model_dump(mode="json"))
        except Exception as e:
            return bridge_error(str(e))

    def update_brand_identity_section(self, section: str, data: dict) -> dict:
        """Update a specific section of the brand identity."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            identity = load_brand(slug)
            if not identity:
                return bridge_error(f"Brand '{slug}' not found")
            valid = {"core", "visual", "voice", "audience", "positioning", "constraints_avoid"}
            if section not in valid:
                return bridge_error(
                    f"Invalid section: {section}. Must be one of: {', '.join(sorted(valid))}"
                )
            try:
                if section == "core":
                    identity.core = BrandCoreIdentity.model_validate(data)
                elif section == "visual":
                    identity.visual = VisualIdentity.model_validate(data)
                elif section == "voice":
                    identity.voice = VoiceGuidelines.model_validate(data)
                elif section == "audience":
                    identity.audience = AudienceProfile.model_validate(data)
                elif section == "positioning":
                    identity.positioning = CompetitivePositioning.model_validate(data)
                elif section == "constraints_avoid":
                    if not isinstance(data, dict):
                        return bridge_error(
                            "constraints_avoid section must be an object with 'constraints' and 'avoid' arrays"
                        )
                    constraints = data.get("constraints", [])
                    avoid = data.get("avoid", [])
                    if not isinstance(constraints, list) or not isinstance(avoid, list):
                        return bridge_error("'constraints' and 'avoid' must be arrays")
                    identity.constraints = constraints
                    identity.avoid = avoid
            except Exception as ve:
                return bridge_error(f"Invalid {section} data: {ve}")
            save_brand(identity)
            if self._state.advisor:
                self._state.advisor.set_brand(slug, preserve_history=True)
            return bridge_ok(identity.model_dump(mode="json"))
        except Exception as e:
            return bridge_error(str(e))

    def regenerate_brand_identity(self, confirm: bool) -> dict:
        """Regenerate brand identity from source materials."""
        from sip_videogen.agents.brand_director import develop_brand_with_output

        try:
            if not confirm:
                return bridge_error(
                    "Regeneration requires confirm=True. This will overwrite the current identity."
                )
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            identity = load_brand(slug)
            if not identity:
                return bridge_error(f"Brand '{slug}' not found")
            brand_dir = get_brand_dir(slug)
            docs_dir = brand_dir / "docs"
            if not docs_dir.exists() or not any(docs_dir.iterdir()):
                return bridge_error(
                    "No source documents found. Add documents to the brand's docs/ folder before regenerating."
                )
            concept_parts = []
            for doc_path in sorted(docs_dir.rglob("*")):
                if (
                    not doc_path.is_file()
                    or doc_path.name.startswith(".")
                    or doc_path.suffix.lower() not in ALLOWED_TEXT_EXTS
                ):
                    continue
                try:
                    content = doc_path.read_text(encoding="utf-8", errors="replace")
                    if len(content) > 50 * 1024:
                        content = content[: 50 * 1024] + "\n...[truncated]"
                    concept_parts.append(f"## From: {doc_path.name}\n\n{content}")
                except Exception:
                    continue
            if not concept_parts:
                return bridge_error("No readable documents found in docs/ folder.")
            concept = "\n\n---\n\n".join(concept_parts)
            if len(concept) > 4800:
                concept = concept[:4800] + "\n...[truncated]"
            try:
                backup_filename = backup_brand_identity(slug)
                logger.info("Backed up identity to: %s", backup_filename)
            except Exception as be:
                return bridge_error(f"Failed to backup current identity: {be}")
            logger.info("Starting regeneration for %s...", slug)
            output = asyncio.run(develop_brand_with_output(concept, existing_brand_slug=slug))
            new_identity = output.brand_identity
            new_identity.slug = slug
            logger.info("AI completed! Brand name: %s", new_identity.core.name)
            save_brand(new_identity)
            if self._state.advisor:
                self._state.advisor.set_brand(slug, preserve_history=True)
            return bridge_ok(new_identity.model_dump(mode="json"))
        except Exception as e:
            logger.exception("Regeneration error: %s", e)
            return bridge_error(str(e))

    def list_identity_backups(self) -> dict:
        """List all identity backups for the active brand."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            backups = list_brand_backups(slug)
            return bridge_ok({"backups": backups})
        except Exception as e:
            return bridge_error(str(e))

    def restore_identity_backup(self, filename: str) -> dict:
        """Restore brand identity from a backup file."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            if "/" in filename or "\\" in filename:
                return bridge_error("Invalid filename: path separators not allowed")
            if not filename.endswith(".json"):
                return bridge_error("Invalid filename: must end with .json")
            try:
                restored = restore_brand_backup(slug, filename)
            except ValueError as e:
                return bridge_error(str(e))
            restored.slug = slug
            save_brand(restored)
            logger.info("Restored identity from backup: %s", filename)
            if self._state.advisor:
                self._state.advisor.set_brand(slug, preserve_history=True)
            return bridge_ok(restored.model_dump(mode="json"))
        except Exception as e:
            logger.exception("Restore identity error: %s", e)
            return bridge_error(str(e))

    def delete_brand(self, slug: str) -> dict:
        """Delete a brand and all its files."""
        try:
            entries = list_brands()
            if slug not in [e.slug for e in entries]:
                return bridge_error(f"Brand '{slug}' not found")
            if self._state.get_active_slug() == slug:
                self._state.advisor = None
                self._state.set_active_slug(None)
            deleted = storage_delete_brand(slug)
            if not deleted:
                return bridge_error(f"Failed to delete brand '{slug}'")
            return bridge_ok()
        except Exception as e:
            return bridge_error(str(e))

    # Helper methods for create_brand_from_materials
    def _build_concept(
        self, description: str, documents: list[dict]
    ) -> tuple[str | None, str | None]:
        """Build concept string from description and document contents."""
        parts = []
        if description.strip():
            parts.append(f"## Brand Description\n\n{description.strip()}")
            logger.debug("Added description to concept")
        for doc in documents:
            fn = doc.get("filename", "unknown")
            data = doc.get("data", "")
            try:
                content = base64.b64decode(data).decode("utf-8", errors="replace")
                logger.debug("Extracted %d chars from %s", len(content), fn)
                if len(content) > 50 * 1024:
                    content = content[: 50 * 1024] + "\n...[truncated]"
                    logger.debug("Truncated to 50KB")
                parts.append(f"## From: {fn}\n\n{content}")
            except Exception as e:
                logger.error("Error reading %s: %s", fn, e)
        if not parts:
            return None, "Please provide a description or upload documents."
        concept = "\n\n---\n\n".join(parts)
        logger.debug("Combined concept length: %d chars", len(concept))
        max_len = 4800
        if len(concept) > max_len:
            logger.debug("Concept too long (%d), truncating...", len(concept))
            if description.strip():
                desc_part = f"## Brand Description\n\n{description.strip()}"
                remaining = max_len - len(desc_part) - 100
                if remaining > 500:
                    doc_summary = concept[len(desc_part) :][:remaining]
                    concept = desc_part + "\n\n---\n\n" + doc_summary + "\n...[truncated]"
                else:
                    concept = desc_part[:max_len]
            else:
                concept = concept[:max_len] + "\n...[truncated]"
            logger.debug("Final concept length: %d chars", len(concept))
        return concept, None

    def _run_brand_director(self, concept: str) -> tuple[BrandIdentityFull | None, str | None]:
        """Run async brand director and return identity."""
        from sip_videogen.agents.brand_director import develop_brand_with_output

        try:
            self._state.current_progress = "Creating brand identity..."
            logger.info("Calling AI brand director...")
            output = asyncio.run(develop_brand_with_output(concept))
            logger.info("AI completed! Brand name: %s", output.brand_identity.core.name)
            return output.brand_identity, None
        except Exception as e:
            logger.exception("AI brand director error: %s", e)
            return None, f"Failed to create brand: {e}"

    def _persist_materials(self, slug: str, images: list[dict], documents: list[dict]) -> None:
        """Save image and document files to brand directory via storage layer."""
        logger.debug("Saving %d images...", len(images))
        for img in images:
            fn = img.get("filename", "")
            data = img.get("data", "")
            if not fn or not data:
                continue
            ext = Path(fn).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTS:
                logger.debug("Skipping %s (unsupported ext)", fn)
                continue
            cat = "logo" if "logo" in fn.lower() else "marketing"
            rel_path, err = save_asset(slug, cat, fn, base64.b64decode(data))
            if err:
                logger.debug("Skipping %s: %s", fn, err)
            else:
                logger.debug("Saved: %s", rel_path)
        logger.debug("Saving %d documents...", len(documents))
        for doc in documents:
            fn = doc.get("filename", "")
            data = doc.get("data", "")
            if not fn or not data:
                continue
            ext = Path(fn).suffix.lower()
            if ext not in ALLOWED_TEXT_EXTS:
                logger.debug("Skipping %s (unsupported ext)", fn)
                continue
            rel_path, err = save_document(slug, fn, base64.b64decode(data))
            if err:
                logger.debug("Skipping %s: %s", fn, err)
            else:
                logger.debug("Saved: docs/%s", rel_path)

    def create_brand_from_materials(
        self, description: str, images: list[dict], documents: list[dict]
    ) -> dict:
        """Create a new brand using AI agents with user-provided materials."""
        logger.info(
            "Starting brand creation - desc:%d chars, images:%d, docs:%d",
            len(description),
            len(images),
            len(documents),
        )
        try:
            # Build concept
            concept, err = self._build_concept(description, documents)
            if err:
                logger.error("Concept error: %s", err)
                return bridge_error(err)
            # Run AI
            identity, err = self._run_brand_director(concept)
            if err:
                self._state.current_progress = ""
                return bridge_error(err)
            # Save brand
            self._state.current_progress = "Saving brand..."
            storage_create_brand(identity)
            slug = identity.slug
            # Persist materials
            self._persist_materials(slug, images, documents)
            self._state.current_progress = ""
            logger.info("SUCCESS! Brand '%s' created", identity.core.name)
            return bridge_ok({"slug": slug, "name": identity.core.name})
        except ValueError as e:
            logger.error("ValueError: %s", e)
            self._state.current_progress = ""
            return bridge_error(str(e))
        except Exception as e:
            logger.exception("Exception during brand creation: %s", e)
            self._state.current_progress = ""
            return bridge_error(f"Failed to create brand: {e}")
