"""Base entity storage classes for DRY CRUD operations."""

from __future__ import annotations

import json
import logging
import shutil
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

from sip_studio.constants import ALLOWED_IMAGE_EXTS
from sip_studio.exceptions import BrandNotFoundError, DuplicateEntityError
from sip_studio.utils.file_utils import write_atomically

from .base import get_brand_dir

TSummary = TypeVar("TSummary", bound=BaseModel)
TFull = TypeVar("TFull", bound=BaseModel)
TIndex = TypeVar("TIndex", bound=BaseModel)
logger = logging.getLogger(__name__)


class BaseEntityStorage(ABC, Generic[TSummary, TFull, TIndex]):
    """Base CRUD for entities with slug, timestamps, summary/full pattern.
    Subclasses implement abstract properties/methods to customize for each entity type."""

    # Config properties (subclass must define)
    @property
    @abstractmethod
    def dir_name(self) -> str:
        """Entity directory name: 'products', 'projects', 'style_references'"""

    @property
    @abstractmethod
    def file_prefix(self) -> str:
        """File prefix: 'product', 'project', 'style_reference'"""

    @property
    @abstractmethod
    def summary_type(self) -> type[TSummary]:
        """The Pydantic model for entity summary."""

    @property
    @abstractmethod
    def full_type(self) -> type[TFull]:
        """The Pydantic model for full entity."""

    @property
    @abstractmethod
    def index_type(self) -> type[TIndex]:
        """The Pydantic model for entity index."""

    # Index adapter methods (varies by entity due to different method names)
    @abstractmethod
    def _index_add(self, index: TIndex, summary: TSummary) -> None:
        """Call index.add_X(summary)"""

    @abstractmethod
    def _index_remove(self, index: TIndex, slug: str) -> bool:
        """Call index.remove_X(slug)"""

    @abstractmethod
    def _index_list(self, index: TIndex) -> list[TSummary]:
        """Get list from index.Xs"""

    def _new_index(self) -> TIndex:
        """Create empty index. Override if index needs special init."""
        return self.index_type()

    # Entity adapter methods
    @abstractmethod
    def _to_summary(self, entity: TFull, brand_slug: str) -> TSummary:
        """Convert full entity to summary. brand_slug for extra context (e.g., asset_count)."""

    @abstractmethod
    def _not_found_error(self, brand_slug: str, slug: str) -> Exception:
        """Return appropriate not found exception."""

    def _get_slug(self, entity: TFull) -> str:
        return entity.slug  # type:ignore

    def _set_updated_at(self, entity: TFull) -> None:
        entity.updated_at = datetime.utcnow()  # type:ignore

    # Path helpers
    def get_entities_dir(self, brand_slug: str) -> Path:
        return get_brand_dir(brand_slug) / self.dir_name

    def get_entity_dir(self, brand_slug: str, slug: str) -> Path:
        return self.get_entities_dir(brand_slug) / slug

    def get_index_path(self, brand_slug: str) -> Path:
        return self.get_entities_dir(brand_slug) / "index.json"

    # Index operations
    def load_index(self, brand_slug: str) -> TIndex:
        """Load the index for a brand. Returns empty index if not exists or corrupted."""
        ip = self.get_index_path(brand_slug)
        if ip.exists():
            try:
                data = json.loads(ip.read_text())
                idx = self.index_type.model_validate(data)
                n = len(self._index_list(idx))
                logger.debug("Loaded %s index for %s with %d items", self.dir_name, brand_slug, n)
                return idx
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON in %s index for %s: %s", self.dir_name, brand_slug, e)
            except Exception as e:
                logger.warning("Failed to load %s index for %s: %s", self.dir_name, brand_slug, e)
        logger.debug("Creating new %s index for %s", self.dir_name, brand_slug)
        return self._new_index()

    def save_index(self, brand_slug: str, index: TIndex) -> None:
        """Save the index for a brand atomically."""
        ip = self.get_index_path(brand_slug)
        write_atomically(ip, index.model_dump_json(indent=2))
        n = len(self._index_list(index))
        logger.debug("Saved %s index for %s with %d items", self.dir_name, brand_slug, n)

    # CRUD operations
    def create(self, brand_slug: str, entity: TFull) -> TSummary:
        """Create a new entity for a brand.
        Args:
            brand_slug: Brand identifier.
            entity: Complete entity data.
        Returns:
            Summary extracted from the entity.
        Raises:
            BrandNotFoundError: If brand doesn't exist.
            DuplicateEntityError: If entity already exists.
        """
        bd = get_brand_dir(brand_slug)
        if not bd.exists():
            raise BrandNotFoundError(f"Brand '{brand_slug}' not found")
        slug = self._get_slug(entity)
        ed = self.get_entity_dir(brand_slug, slug)
        if ed.exists():
            nm = self.file_prefix.replace("_", " ").title()
            raise DuplicateEntityError(f"{nm} '{slug}' already exists in brand '{brand_slug}'")
        # Create directory
        ed.mkdir(parents=True, exist_ok=True)
        # Save entity files atomically
        summary = self._to_summary(entity, brand_slug)
        write_atomically(ed / f"{self.file_prefix}.json", summary.model_dump_json(indent=2))
        write_atomically(ed / f"{self.file_prefix}_full.json", entity.model_dump_json(indent=2))
        # Update index
        idx = self.load_index(brand_slug)
        self._index_add(idx, summary)
        self.save_index(brand_slug, idx)
        logger.info("Created %s %s for brand %s", self.file_prefix, slug, brand_slug)
        return summary

    def load(self, brand_slug: str, slug: str) -> TFull | None:
        """Load an entity's full details from disk.
        Returns:
            Full entity or None if not found or corrupted.
        """
        fp = self.get_entity_dir(brand_slug, slug) / f"{self.file_prefix}_full.json"
        if not fp.exists():
            logger.debug("%s not found: %s/%s", self.file_prefix.title(), brand_slug, slug)
            return None
        try:
            data = json.loads(fp.read_text())
            return self.full_type.model_validate(data)
        except Exception as e:
            logger.error("Failed to load %s %s/%s: %s", self.file_prefix, brand_slug, slug, e)
            return None

    def load_summary(self, brand_slug: str, slug: str) -> TSummary | None:
        """Load just the entity summary (L0 layer).
        This is faster than load() when you only need the summary.
        """
        fp = self.get_entity_dir(brand_slug, slug) / f"{self.file_prefix}.json"
        if not fp.exists():
            return None
        try:
            data = json.loads(fp.read_text())
            return self.summary_type.model_validate(data)
        except Exception as e:
            logger.error(
                "Failed to load %s summary %s/%s: %s", self.file_prefix, brand_slug, slug, e
            )
            return None

    def save(self, brand_slug: str, entity: TFull) -> TSummary:
        """Save/update an entity.
        Args:
            brand_slug: Brand identifier.
            entity: Updated entity data.
        Returns:
            Updated summary.
        """
        slug = self._get_slug(entity)
        ed = self.get_entity_dir(brand_slug, slug)
        if not ed.exists():
            return self.create(brand_slug, entity)
        # Update timestamp
        self._set_updated_at(entity)
        # Save files atomically
        summary = self._to_summary(entity, brand_slug)
        write_atomically(ed / f"{self.file_prefix}.json", summary.model_dump_json(indent=2))
        write_atomically(ed / f"{self.file_prefix}_full.json", entity.model_dump_json(indent=2))
        # Update index
        idx = self.load_index(brand_slug)
        self._index_add(idx, summary)
        self.save_index(brand_slug, idx)
        logger.info("Saved %s %s for brand %s", self.file_prefix, slug, brand_slug)
        return summary

    def delete(self, brand_slug: str, slug: str) -> bool:
        """Delete an entity and all its files.
        Returns:
            True if entity was deleted, False if not found.
        """
        ed = self.get_entity_dir(brand_slug, slug)
        if not ed.exists():
            return False
        shutil.rmtree(ed)
        # Update index
        idx = self.load_index(brand_slug)
        self._index_remove(idx, slug)
        self.save_index(brand_slug, idx)
        logger.info("Deleted %s %s from brand %s", self.file_prefix, slug, brand_slug)
        return True

    def list_all(self, brand_slug: str) -> list[TSummary]:
        """List all entities for a brand, sorted by name."""
        idx = self.load_index(brand_slug)
        return sorted(self._index_list(idx), key=lambda x: x.name.lower())  # type:ignore


class BaseImageEntityStorage(BaseEntityStorage[TSummary, TFull, TIndex]):
    """Extended storage with image management for entities that have images."""

    # Image field adapters (subclass implements)
    @abstractmethod
    def _get_entity_images(self, entity: TFull) -> list[str]:
        """Get entity.images list."""

    @abstractmethod
    def _set_entity_images(self, entity: TFull, images: list[str]) -> None:
        """Set entity.images list."""

    @abstractmethod
    def _get_primary_image(self, entity: TFull) -> str:
        """Get entity.primary_image."""

    @abstractmethod
    def _set_primary_image(self, entity: TFull, path: str) -> None:
        """Set entity.primary_image."""

    def create(self, brand_slug: str, entity: TFull) -> TSummary:
        """Create entity and images directory."""
        result = super().create(brand_slug, entity)
        # Create images dir after entity dir exists
        (self.get_entity_dir(brand_slug, self._get_slug(entity)) / "images").mkdir(exist_ok=True)
        return result

    def list_images(self, brand_slug: str, slug: str) -> list[str]:
        """List all images for an entity.
        Returns:
            List of brand-relative image paths.
        """
        imd = self.get_entity_dir(brand_slug, slug) / "images"
        if not imd.exists():
            return []
        imgs = []
        for fp in sorted(imd.iterdir()):
            if fp.suffix.lower() in ALLOWED_IMAGE_EXTS:
                imgs.append(f"{self.dir_name}/{slug}/images/{fp.name}")
        return imgs

    def add_image(self, brand_slug: str, slug: str, filename: str, data: bytes) -> str:
        """Add an image to an entity.
        Args:
            brand_slug: Brand identifier.
            slug: Entity identifier.
            filename: Image filename.
            data: Image binary data.
        Returns:
            Brand-relative path to the saved image.
        Raises:
            EntityNotFoundError: If entity doesn't exist.
        """
        ed = self.get_entity_dir(brand_slug, slug)
        if not ed.exists():
            raise self._not_found_error(brand_slug, slug)
        imd = ed / "images"
        imd.mkdir(exist_ok=True)
        # Save image
        (imd / filename).write_bytes(data)
        # Brand-relative path
        br = f"{self.dir_name}/{slug}/images/{filename}"
        # Update entity's images list
        ent = self.load(brand_slug, slug)
        if ent:
            imgs = self._get_entity_images(ent)
            if br not in imgs:
                imgs.append(br)
                self._set_entity_images(ent, imgs)
            # Set as primary if first image
            if not self._get_primary_image(ent):
                self._set_primary_image(ent, br)
            self.save(brand_slug, ent)
        logger.info("Added image %s to %s %s/%s", filename, self.file_prefix, brand_slug, slug)
        return br

    def delete_image(self, brand_slug: str, slug: str, filename: str) -> bool:
        """Delete an image from an entity.
        Returns:
            True if image was deleted, False if not found.
        """
        ip = self.get_entity_dir(brand_slug, slug) / "images" / filename
        if not ip.exists():
            return False
        ip.unlink()
        # Update entity's images list
        br = f"{self.dir_name}/{slug}/images/{filename}"
        ent = self.load(brand_slug, slug)
        if ent:
            imgs = self._get_entity_images(ent)
            if br in imgs:
                imgs.remove(br)
                self._set_entity_images(ent, imgs)
            # Update primary if it was the deleted image
            if self._get_primary_image(ent) == br:
                self._set_primary_image(ent, imgs[0] if imgs else "")
            self.save(brand_slug, ent)
        logger.info("Deleted image %s from %s %s/%s", filename, self.file_prefix, brand_slug, slug)
        return True

    def set_primary_image(self, brand_slug: str, slug: str, brand_relative_path: str) -> bool:
        """Set the primary image for an entity.
        Args:
            brand_slug: Brand identifier.
            slug: Entity identifier.
            brand_relative_path: Brand-relative path to the image.
        Returns:
            True if primary was set, False if image not found in entity.
        """
        ent = self.load(brand_slug, slug)
        if not ent:
            return False
        if brand_relative_path not in self._get_entity_images(ent):
            return False
        self._set_primary_image(ent, brand_relative_path)
        self.save(brand_slug, ent)
        brp = brand_relative_path
        logger.info("Set primary image for %s %s/%s to %s", self.file_prefix, brand_slug, slug, brp)
        return True
