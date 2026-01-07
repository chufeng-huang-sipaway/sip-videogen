"""Project/Campaign models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Project lifecycle status."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectSummary(BaseModel):
    """Compact project summary - L0 layer for quick loading.
    Used for project list display."""

    slug: str = Field(description="URL-safe identifier, e.g., 'christmas-campaign'")
    name: str = Field(description="Project name, e.g., 'Christmas 2024 Campaign'")
    status: ProjectStatus = Field(
        default=ProjectStatus.ACTIVE, description="Project status: active or archived"
    )
    asset_count: int = Field(
        default=0, description="Number of generated assets (from prefix search)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the project was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the project was last updated"
    )


class ProjectFull(BaseModel):
    """Complete project details - L1 layer loaded on demand.
    Contains project instructions and metadata.
    Generated assets are tracked via filename prefix in assets/generated/."""

    slug: str = Field(description="URL-safe identifier")
    name: str = Field(description="Project name")
    status: ProjectStatus = Field(
        default=ProjectStatus.ACTIVE, description="Project status: active or archived"
    )
    instructions: str = Field(
        default="", description="Markdown instructions - campaign rules, guidelines, etc."
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the project was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the project was last updated"
    )

    def to_summary(self, asset_count: int = 0) -> ProjectSummary:
        """Extract a ProjectSummary from this full project.
        Used when saving a project to generate the L0 layer.
        asset_count must be provided as it requires filesystem access."""
        return ProjectSummary(
            slug=self.slug,
            name=self.name,
            status=self.status,
            asset_count=asset_count,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class ProjectIndex(BaseModel):
    """Registry of all projects for a brand.
    Stored at ~/.sip-studio/brands/{brand-slug}/projects/index.json"""

    version: str = Field(default="1.0", description="Index format version")
    projects: List[ProjectSummary] = Field(
        default_factory=list, description="List of project summaries"
    )
    active_project: str | None = Field(
        default=None, description="Slug of the currently active project"
    )

    def get_project(self, slug: str) -> ProjectSummary | None:
        """Find a project by slug."""
        for p in self.projects:
            if p.slug == slug:
                return p
        return None

    def add_project(self, entry: ProjectSummary) -> None:
        """Add or update a project in the index."""
        self.projects = [p for p in self.projects if p.slug != entry.slug]
        self.projects.append(entry)

    def remove_project(self, slug: str) -> bool:
        """Remove a project from the index. Returns True if found and removed."""
        n = len(self.projects)
        self.projects = [p for p in self.projects if p.slug != slug]
        if self.active_project == slug:
            self.active_project = None
        return len(self.projects) < n
