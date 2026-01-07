"""Project management service."""

from __future__ import annotations

import re
from datetime import datetime

from sip_studio.brands.models import ProjectFull, ProjectStatus
from sip_studio.brands.storage import (
    count_project_assets,
    create_project,
    delete_project,
    get_active_project,
    list_project_assets,
    list_projects,
    load_project,
    save_project,
    set_active_project,
)

from ..state import BridgeState
from ..utils.bridge_types import bridge_error, bridge_ok
from ..utils.decorators import require_brand


class ProjectService:
    """Project CRUD and asset listing."""

    def __init__(self, state: BridgeState):
        self._state = state

    @require_brand()
    def get_projects(self, brand_slug: str | None = None) -> dict:
        """Get list of projects for a brand."""
        try:
            if not brand_slug:
                return bridge_error("Brand slug required")
            projects = list_projects(brand_slug)
            active = get_active_project(brand_slug)
            return bridge_ok(
                {
                    "projects": [
                        {
                            "slug": p.slug,
                            "name": p.name,
                            "status": p.status.value,
                            "asset_count": count_project_assets(brand_slug, p.slug),
                            "created_at": p.created_at.isoformat(),
                            "updated_at": p.updated_at.isoformat(),
                        }
                        for p in projects
                    ],
                    "active_project": active,
                }
            )
        except Exception as e:
            return bridge_error(str(e))

    def get_project(self, project_slug: str) -> dict:
        """Get detailed project information."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            project = load_project(slug, project_slug)
            if not project:
                return bridge_error(f"Project '{project_slug}' not found")
            assets = list_project_assets(slug, project_slug)
            return bridge_ok(
                {
                    "slug": project.slug,
                    "name": project.name,
                    "status": project.status.value,
                    "instructions": project.instructions,
                    "assets": assets,
                    "asset_count": len(assets),
                    "created_at": project.created_at.isoformat(),
                    "updated_at": project.updated_at.isoformat(),
                }
            )
        except Exception as e:
            return bridge_error(str(e))

    def create_project(self, name: str, instructions: str = "") -> dict:
        """Create a new project."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            if not name.strip():
                return bridge_error("Project name is required")
            project_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            if not project_slug:
                return bridge_error("Invalid project name")
            if load_project(slug, project_slug):
                return bridge_error(f"Project '{project_slug}' already exists")
            now = datetime.utcnow()
            project = ProjectFull(
                slug=project_slug,
                name=name.strip(),
                status=ProjectStatus.ACTIVE,
                instructions=instructions.strip(),
                created_at=now,
                updated_at=now,
            )
            create_project(slug, project)
            return bridge_ok({"slug": project_slug})
        except Exception as e:
            return bridge_error(str(e))

    def update_project(
        self,
        project_slug: str,
        name: str | None = None,
        instructions: str | None = None,
        status: str | None = None,
    ) -> dict:
        """Update an existing project."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            project = load_project(slug, project_slug)
            if not project:
                return bridge_error(f"Project '{project_slug}' not found")
            if name is not None:
                project.name = name.strip()
            if instructions is not None:
                project.instructions = instructions.strip()
            if status is not None:
                if status == "active":
                    project.status = ProjectStatus.ACTIVE
                elif status == "archived":
                    project.status = ProjectStatus.ARCHIVED
                else:
                    return bridge_error(f"Invalid status: {status}")
            project.updated_at = datetime.utcnow()
            save_project(slug, project)
            return bridge_ok(
                {"slug": project.slug, "name": project.name, "status": project.status.value}
            )
        except Exception as e:
            return bridge_error(str(e))

    def delete_project(self, project_slug: str) -> dict:
        """Delete a project."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            active = get_active_project(slug)
            if active == project_slug:
                set_active_project(slug, None)
            deleted = delete_project(slug, project_slug)
            if not deleted:
                return bridge_error(f"Project '{project_slug}' not found")
            return bridge_ok()
        except Exception as e:
            return bridge_error(str(e))

    def set_active_project(self, project_slug: str | None) -> dict:
        """Set the active project for the current brand."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            if project_slug is not None:
                project = load_project(slug, project_slug)
                if not project:
                    return bridge_error(f"Project '{project_slug}' not found")
            set_active_project(slug, project_slug)
            return bridge_ok({"active_project": project_slug})
        except Exception as e:
            return bridge_error(str(e))

    def get_active_project(self) -> dict:
        """Get the active project for the current brand."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            active = get_active_project(slug)
            return bridge_ok({"active_project": active})
        except Exception as e:
            return bridge_error(str(e))

    def get_project_assets(self, project_slug: str) -> dict:
        """Get list of generated assets for a project."""
        try:
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            assets = list_project_assets(slug, project_slug)
            return bridge_ok({"assets": assets})
        except Exception as e:
            return bridge_error(str(e))

    def get_general_assets(self, brand_slug: str | None = None) -> dict:
        """Get assets not belonging to any project (no project prefix)."""
        from sip_studio.brands.storage import get_brand_dir
        from sip_studio.constants import ALLOWED_IMAGE_EXTS, ALLOWED_VIDEO_EXTS

        try:
            slug = brand_slug or self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            brand_dir = get_brand_dir(slug)
            assets = []
            allowed = ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS
            projects = [p.slug for p in list_projects(slug)]
            for folder in ["generated", "video"]:
                folder_path = brand_dir / "assets" / folder
                if not folder_path.exists():
                    continue
                for f in folder_path.iterdir():
                    if not f.is_file() or f.suffix.lower() not in allowed:
                        continue
                    name = f.name
                    has_project = False
                    for p in projects:
                        if name.startswith(f"{p}__"):
                            has_project = True
                            break
                    if not has_project:
                        assets.append(f"{folder}/{name}")
            return bridge_ok({"assets": sorted(assets), "count": len(assets)})
        except Exception as e:
            return bridge_error(str(e))
