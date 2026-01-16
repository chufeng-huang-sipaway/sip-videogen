"""Product CRUD operations."""

from __future__ import annotations

import logging

from sip_studio.exceptions import ProductNotFoundError

from ..models import ProductFull, ProductIndex, ProductSummary
from .base_entity import BaseImageEntityStorage

logger = logging.getLogger(__name__)


class ProductStorage(BaseImageEntityStorage[ProductSummary, ProductFull, ProductIndex]):
    """Storage implementation for products."""

    @property
    def dir_name(self) -> str:
        return "products"

    @property
    def file_prefix(self) -> str:
        return "product"

    @property
    def summary_type(self) -> type[ProductSummary]:
        return ProductSummary

    @property
    def full_type(self) -> type[ProductFull]:
        return ProductFull

    @property
    def index_type(self) -> type[ProductIndex]:
        return ProductIndex

    # Index adapters
    def _index_add(self, index: ProductIndex, summary: ProductSummary) -> None:
        index.add_product(summary)

    def _index_remove(self, index: ProductIndex, slug: str) -> bool:
        return index.remove_product(slug)

    def _index_list(self, index: ProductIndex) -> list[ProductSummary]:
        return index.products

    # Entity adapters
    def _to_summary(self, entity: ProductFull, brand_slug: str) -> ProductSummary:
        return entity.to_summary()

    def _not_found_error(self, brand_slug: str, slug: str) -> Exception:
        return ProductNotFoundError(f"Product '{slug}' not found in brand '{brand_slug}'")

    # Image adapters
    def _get_entity_images(self, entity: ProductFull) -> list[str]:
        return entity.images

    def _set_entity_images(self, entity: ProductFull, images: list[str]) -> None:
        entity.images = images

    def _get_primary_image(self, entity: ProductFull) -> str:
        return entity.primary_image

    def _set_primary_image(self, entity: ProductFull, path: str) -> None:
        entity.primary_image = path


# Module-level singleton
_st = ProductStorage()


# Path helpers (backward compat)
def get_products_dir(bs: str):
    return _st.get_entities_dir(bs)


def get_product_dir(bs: str, ps: str):
    return _st.get_entity_dir(bs, ps)


def get_product_index_path(bs: str):
    return _st.get_index_path(bs)


# Index operations (backward compat)
def load_product_index(bs: str) -> ProductIndex:
    return _st.load_index(bs)


def save_product_index(bs: str, idx: ProductIndex) -> None:
    _st.save_index(bs, idx)


# CRUD operations (backward compat)
def create_product(bs: str, p: ProductFull) -> ProductSummary:
    return _st.create(bs, p)


def load_product(bs: str, ps: str) -> ProductFull | None:
    return _st.load(bs, ps)


def load_product_summary(bs: str, ps: str) -> ProductSummary | None:
    return _st.load_summary(bs, ps)


def save_product(bs: str, p: ProductFull) -> ProductSummary:
    return _st.save(bs, p)


def delete_product(bs: str, ps: str) -> bool:
    return _st.delete(bs, ps)


def list_products(bs: str) -> list[ProductSummary]:
    return _st.list_all(bs)


# Image operations (backward compat)
def list_product_images(bs: str, ps: str) -> list[str]:
    return _st.list_images(bs, ps)


def add_product_image(bs: str, ps: str, fn: str, data: bytes) -> str:
    return _st.add_image(bs, ps, fn, data)


def delete_product_image(bs: str, ps: str, fn: str) -> bool:
    return _st.delete_image(bs, ps, fn)


def set_primary_product_image(bs: str, ps: str, brp: str) -> bool:
    return _st.set_primary_image(bs, ps, brp)
