"""Project CRUD operations."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from sip_studio.constants import ALLOWED_IMAGE_EXTS, ALLOWED_VIDEO_EXTS
from sip_studio.exceptions import BrandNotFoundError, DuplicateEntityError, ProjectNotFoundError
from sip_studio.utils.file_utils import write_atomically

from ..models import ProjectFull, ProjectIndex, ProjectSummary
from .base import get_brand_dir

logger = logging.getLogger(__name__)


def get_projects_dir(brand_slug: str) -> Path:
    """Get the projects directory for a brand."""
    return get_brand_dir(brand_slug) / "projects"


def get_project_dir(brand_slug: str, project_slug: str) -> Path:
    """Get the directory for a specific project."""
    return get_projects_dir(brand_slug) / project_slug


def get_project_index_path(brand_slug: str) -> Path:
    """Get the path to the project index file for a brand."""
    return get_projects_dir(brand_slug) / "index.json"


def load_project_index(brand_slug: str) -> ProjectIndex:
    """Load the project index for a brand."""
    ip = get_project_index_path(brand_slug)
    if ip.exists():
        try:
            data = json.loads(ip.read_text())
            idx = ProjectIndex.model_validate(data)
            logger.debug(
                "Loaded project index for %s with %d projects", brand_slug, len(idx.projects)
            )
            return idx
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in project index for %s: %s", brand_slug, e)
        except Exception as e:
            logger.warning("Failed to load project index for %s: %s", brand_slug, e)
    logger.debug("Creating new project index for %s", brand_slug)
    return ProjectIndex()


def save_project_index(brand_slug: str, index: ProjectIndex) -> None:
    """Save the project index for a brand atomically."""
    ip = get_project_index_path(brand_slug)
    write_atomically(ip, index.model_dump_json(indent=2))
    logger.debug("Saved project index for %s with %d projects", brand_slug, len(index.projects))


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


def create_project(brand_slug: str, project: ProjectFull) -> ProjectSummary:
    """Create a new project for a brand.
    Args:
        brand_slug: Brand identifier.
        project: Complete project data.
    Returns:
        ProjectSummary extracted from the project.
    Raises:
        BrandNotFoundError: If brand doesn't exist.
        DuplicateEntityError: If project already exists.
    """
    bd = get_brand_dir(brand_slug)
    if not bd.exists():
        raise BrandNotFoundError(f"Brand '{brand_slug}' not found")
    pd = get_project_dir(brand_slug, project.slug)
    if pd.exists():
        raise DuplicateEntityError(
            f"Project '{project.slug}' already exists in brand '{brand_slug}'"
        )
    # Create directory
    pd.mkdir(parents=True, exist_ok=True)
    # Save project files atomically (asset_count is 0 for new projects)
    ac = count_project_assets(brand_slug, project.slug)
    summary = project.to_summary(asset_count=ac)
    write_atomically(pd / "project.json", summary.model_dump_json(indent=2))
    write_atomically(pd / "project_full.json", project.model_dump_json(indent=2))
    # Update index
    idx = load_project_index(brand_slug)
    idx.add_project(summary)
    save_project_index(brand_slug, idx)
    logger.info("Created project %s for brand %s", project.slug, brand_slug)
    return summary


def load_project(brand_slug: str, project_slug: str) -> ProjectFull | None:
    """Load a project's full details from disk.
    Args:
        brand_slug: Brand identifier.
        project_slug: Project identifier.
    Returns:
        ProjectFull or None if not found.
    """
    pd = get_project_dir(brand_slug, project_slug)
    pp = pd / "project_full.json"
    if not pp.exists():
        logger.debug("Project not found: %s/%s", brand_slug, project_slug)
        return None
    try:
        data = json.loads(pp.read_text())
        return ProjectFull.model_validate(data)
    except Exception as e:
        logger.error("Failed to load project %s/%s: %s", brand_slug, project_slug, e)
        return None


def load_project_summary(brand_slug: str, project_slug: str) -> ProjectSummary | None:
    """Load just the project summary (L0 layer).
    This is faster than load_project() when you only need the summary.
    """
    pd = get_project_dir(brand_slug, project_slug)
    sp = pd / "project.json"
    if not sp.exists():
        return None
    try:
        data = json.loads(sp.read_text())
        return ProjectSummary.model_validate(data)
    except Exception as e:
        logger.error("Failed to load project summary %s/%s: %s", brand_slug, project_slug, e)
        return None


def save_project(brand_slug: str, project: ProjectFull) -> ProjectSummary:
    """Save/update a project.
    Args:
        brand_slug: Brand identifier.
        project: Updated project data.
    Returns:
        Updated ProjectSummary.
    """
    pd = get_project_dir(brand_slug, project.slug)
    if not pd.exists():
        return create_project(brand_slug, project)
    # Update timestamp
    project.updated_at = datetime.utcnow()
    # Save files atomically (recalculate asset_count)
    ac = count_project_assets(brand_slug, project.slug)
    summary = project.to_summary(asset_count=ac)
    write_atomically(pd / "project.json", summary.model_dump_json(indent=2))
    write_atomically(pd / "project_full.json", project.model_dump_json(indent=2))
    # Update index
    idx = load_project_index(brand_slug)
    idx.add_project(summary)
    save_project_index(brand_slug, idx)
    logger.info("Saved project %s for brand %s", project.slug, brand_slug)
    return summary


def delete_project(brand_slug: str, project_slug: str) -> bool:
    """Delete a project and its metadata (not generated assets).
    Note: Generated assets in assets/generated/ are NOT deleted,
    only the project metadata in projects/{slug}/.
    Returns:
        True if project was deleted, False if not found.
    """
    pd = get_project_dir(brand_slug, project_slug)
    if not pd.exists():
        return False
    shutil.rmtree(pd)
    # Update index
    idx = load_project_index(brand_slug)
    idx.remove_project(project_slug)
    save_project_index(brand_slug, idx)
    logger.info("Deleted project %s from brand %s", project_slug, brand_slug)
    return True


def list_projects(brand_slug: str) -> list[ProjectSummary]:
    """List all projects for a brand, sorted by name."""
    idx = load_project_index(brand_slug)
    return sorted(idx.projects, key=lambda p: p.name.lower())


def get_active_project(brand_slug: str) -> str | None:
    """Get the slug of the currently active project for a brand."""
    idx = load_project_index(brand_slug)
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
    idx = load_project_index(brand_slug)
    if project_slug and not idx.get_project(project_slug):
        raise ProjectNotFoundError(f"Project '{project_slug}' not found in brand '{brand_slug}'")
    idx.active_project = project_slug
    save_project_index(brand_slug, idx)
    logger.info("Active project for brand %s set to: %s", brand_slug, project_slug or "(none)")
