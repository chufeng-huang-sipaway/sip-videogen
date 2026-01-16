"""Project CRUD operations."""

from __future__ import annotations

import logging
from pathlib import Path

from sip_studio.constants import ALLOWED_IMAGE_EXTS, ALLOWED_VIDEO_EXTS
from sip_studio.exceptions import ProjectNotFoundError

from ..models import ProjectFull, ProjectIndex, ProjectSummary
from .base import get_brand_dir
from .base_entity import BaseEntityStorage

logger = logging.getLogger(__name__)


def count_project_assets(brand_slug: str, project_slug: str) -> int:
    """Count assets belonging to a project by filename prefix.
    Searches assets/generated/ and assets/video/ for files prefixed with '{project_slug}__'.
    """
    bd = get_brand_dir(brand_slug)
    ads = [bd / "assets" / "generated", bd / "assets" / "video"]
    pf = f"{project_slug}__"
    cnt = 0
    ae = ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS
    for ad in ads:
        if not ad.exists():
            continue
        for fp in ad.iterdir():
            if fp.is_file() and fp.suffix.lower() in ae and fp.name.startswith(pf):
                cnt += 1
    return cnt


def list_project_assets(brand_slug: str, project_slug: str) -> list[str]:
    """List assets belonging to a project by filename prefix.
    Returns:
        List of assets-relative paths (e.g., 'generated/project__file.png').
    """
    bd = get_brand_dir(brand_slug)
    ads = {"generated": bd / "assets" / "generated", "video": bd / "assets" / "video"}
    pf = f"{project_slug}__"
    assets = []
    ae = ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS
    for cat, ad in ads.items():
        if not ad.exists():
            continue
        for fp in sorted(ad.iterdir()):
            if fp.is_file() and fp.suffix.lower() in ae and fp.name.startswith(pf):
                assets.append(f"{cat}/{fp.name}")
    return assets


class ProjectStorage(BaseEntityStorage[ProjectSummary, ProjectFull, ProjectIndex]):
    """Storage implementation for projects."""

    @property
    def dir_name(self) -> str:
        return "projects"

    @property
    def file_prefix(self) -> str:
        return "project"

    @property
    def summary_type(self) -> type[ProjectSummary]:
        return ProjectSummary

    @property
    def full_type(self) -> type[ProjectFull]:
        return ProjectFull

    @property
    def index_type(self) -> type[ProjectIndex]:
        return ProjectIndex

    # Index adapters
    def _index_add(self, index: ProjectIndex, summary: ProjectSummary) -> None:
        index.add_project(summary)

    def _index_remove(self, index: ProjectIndex, slug: str) -> bool:
        return index.remove_project(slug)

    def _index_list(self, index: ProjectIndex) -> list[ProjectSummary]:
        return index.projects

    # Entity adapters
    def _to_summary(self, entity: ProjectFull, brand_slug: str) -> ProjectSummary:
        ac = count_project_assets(brand_slug, entity.slug)
        return entity.to_summary(asset_count=ac)

    def _not_found_error(self, brand_slug: str, slug: str) -> Exception:
        return ProjectNotFoundError(f"Project '{slug}' not found in brand '{brand_slug}'")


# Module-level singleton
_st = ProjectStorage()


# Path helpers (backward compat)
def get_projects_dir(bs: str) -> Path:
    return _st.get_entities_dir(bs)


def get_project_dir(bs: str, ps: str) -> Path:
    return _st.get_entity_dir(bs, ps)


def get_project_index_path(bs: str) -> Path:
    return _st.get_index_path(bs)


# Index operations (backward compat)
def load_project_index(bs: str) -> ProjectIndex:
    return _st.load_index(bs)


def save_project_index(bs: str, idx: ProjectIndex) -> None:
    _st.save_index(bs, idx)


# CRUD operations (backward compat)
def create_project(bs: str, p: ProjectFull) -> ProjectSummary:
    return _st.create(bs, p)


def load_project(bs: str, ps: str) -> ProjectFull | None:
    return _st.load(bs, ps)


def load_project_summary(bs: str, ps: str) -> ProjectSummary | None:
    return _st.load_summary(bs, ps)


def save_project(bs: str, p: ProjectFull) -> ProjectSummary:
    return _st.save(bs, p)


def delete_project(bs: str, ps: str) -> bool:
    return _st.delete(bs, ps)


def list_projects(bs: str) -> list[ProjectSummary]:
    return _st.list_all(bs)


# Active project operations (project-specific, not in base)
def get_active_project(brand_slug: str) -> str | None:
    """Get the slug of the currently active project for a brand."""
    idx = _st.load_index(brand_slug)
    logger.debug(
        "get_active_project(%s) -> %s (from index with %d projects)",
        brand_slug,
        idx.active_project,
        len(idx.projects),
    )
    return idx.active_project


def set_active_project(brand_slug: str, project_slug: str | None) -> None:
    """Set the active project for a brand.
    Args:
        brand_slug: Brand identifier.
        project_slug: Project slug to set as active, or None to clear.
    Raises:
        ProjectNotFoundError: If project doesn't exist (when setting non-None).
    """
    idx = _st.load_index(brand_slug)
    if project_slug and not idx.get_project(project_slug):
        raise ProjectNotFoundError(f"Project '{project_slug}' not found in brand '{brand_slug}'")
    idx.active_project = project_slug
    _st.save_index(brand_slug, idx)
    logger.info("Active project for brand %s set to: %s", brand_slug, project_slug or "(none)")
