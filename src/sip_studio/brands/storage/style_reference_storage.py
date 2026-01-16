"""Style Reference CRUD operations."""

from __future__ import annotations

import logging

from sip_studio.exceptions import StyleReferenceNotFoundError

from ..models import StyleReferenceFull, StyleReferenceIndex, StyleReferenceSummary
from .base_entity import BaseImageEntityStorage

logger = logging.getLogger(__name__)


class StyleReferenceStorage(
    BaseImageEntityStorage[StyleReferenceSummary, StyleReferenceFull, StyleReferenceIndex]
):
    """Storage implementation for style references."""

    @property
    def dir_name(self) -> str:
        return "style_references"

    @property
    def file_prefix(self) -> str:
        return "style_reference"

    @property
    def summary_type(self) -> type[StyleReferenceSummary]:
        return StyleReferenceSummary

    @property
    def full_type(self) -> type[StyleReferenceFull]:
        return StyleReferenceFull

    @property
    def index_type(self) -> type[StyleReferenceIndex]:
        return StyleReferenceIndex

    # Index adapters
    def _index_add(self, index: StyleReferenceIndex, summary: StyleReferenceSummary) -> None:
        index.add_style_reference(summary)

    def _index_remove(self, index: StyleReferenceIndex, slug: str) -> bool:
        return index.remove_style_reference(slug)

    def _index_list(self, index: StyleReferenceIndex) -> list[StyleReferenceSummary]:
        return index.style_references

    # Entity adapters
    def _to_summary(self, entity: StyleReferenceFull, brand_slug: str) -> StyleReferenceSummary:  # noqa: ARG002
        return entity.to_summary()

    def _not_found_error(self, brand_slug: str, slug: str) -> Exception:
        return StyleReferenceNotFoundError(
            f"Style reference '{slug}' not found in brand '{brand_slug}'"
        )

    # Image adapters
    def _get_entity_images(self, entity: StyleReferenceFull) -> list[str]:
        return entity.images

    def _set_entity_images(self, entity: StyleReferenceFull, images: list[str]) -> None:
        entity.images = images

    def _get_primary_image(self, entity: StyleReferenceFull) -> str:
        return entity.primary_image

    def _set_primary_image(self, entity: StyleReferenceFull, path: str) -> None:
        entity.primary_image = path


# Module-level singleton
_st = StyleReferenceStorage()


# Path helpers (backward compat)
def get_style_references_dir(bs: str):
    return _st.get_entities_dir(bs)


def get_style_reference_dir(bs: str, srs: str):
    return _st.get_entity_dir(bs, srs)


def get_style_reference_index_path(bs: str):
    return _st.get_index_path(bs)


# Index operations (backward compat)
def load_style_reference_index(bs: str) -> StyleReferenceIndex:
    return _st.load_index(bs)


def save_style_reference_index(bs: str, idx: StyleReferenceIndex) -> None:
    _st.save_index(bs, idx)


# CRUD operations (backward compat)
def create_style_reference(bs: str, sr: StyleReferenceFull) -> StyleReferenceSummary:
    return _st.create(bs, sr)


def load_style_reference(bs: str, srs: str) -> StyleReferenceFull | None:
    return _st.load(bs, srs)


def load_style_reference_summary(bs: str, srs: str) -> StyleReferenceSummary | None:
    return _st.load_summary(bs, srs)


def save_style_reference(bs: str, sr: StyleReferenceFull) -> StyleReferenceSummary:
    return _st.save(bs, sr)


def delete_style_reference(bs: str, srs: str) -> bool:
    return _st.delete(bs, srs)


def list_style_references(bs: str) -> list[StyleReferenceSummary]:
    return _st.list_all(bs)


# Image operations (backward compat)
def list_style_reference_images(bs: str, srs: str) -> list[str]:
    return _st.list_images(bs, srs)


def add_style_reference_image(bs: str, srs: str, fn: str, data: bytes) -> str:
    return _st.add_image(bs, srs, fn, data)


def delete_style_reference_image(bs: str, srs: str, fn: str) -> bool:
    return _st.delete_image(bs, srs, fn)


def set_primary_style_reference_image(bs: str, srs: str, brp: str) -> bool:
    return _st.set_primary_image(bs, srs, brp)


def sync_style_reference_index(brand_slug: str) -> int:
    """Reconcile style reference index with filesystem.

    Adds style references that exist on disk but not in index,
    removes index entries for style references that no longer exist.

    Returns:
        Number of changes made (additions + removals).
    """
    srd = _st.get_entities_dir(brand_slug)
    if not srd.exists():
        return 0
    idx = _st.load_index(brand_slug)
    changes = 0
    # Find style references on disk
    dslugs = set()
    for item in srd.iterdir():
        if item.is_dir() and (item / "style_reference_full.json").exists():
            dslugs.add(item.name)
    # Find style references in index
    islugs = {t.slug for t in idx.style_references}
    # Add missing to index
    for s in dslugs - islugs:
        sr = _st.load(brand_slug, s)
        if sr:
            idx.add_style_reference(sr.to_summary())
            logger.info("Synced style reference %s to index for brand %s", s, brand_slug)
            changes += 1
    # Remove orphaned from index
    for s in islugs - dslugs:
        idx.remove_style_reference(s)
        logger.info("Removed orphaned style reference %s from index for brand %s", s, brand_slug)
        changes += 1
    if changes > 0:
        _st.save_index(brand_slug, idx)
    return changes
