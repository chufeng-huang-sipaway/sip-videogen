"""Pydantic models for brand creation from website URL."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Valid status/phase combinations per implementation plan
JobStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
JobPhase = Literal["starting", "researching", "creating", "finalizing", "complete", "failed"]
VALID_STATES: set[tuple[JobStatus, JobPhase]] = {
    ("pending", "starting"),
    ("running", "researching"),
    ("running", "creating"),
    ("running", "finalizing"),
    ("completed", "complete"),
    ("failed", "failed"),
    ("cancelled", "failed"),
}


class WebsiteAssets(BaseModel):
    """Extracted assets from brand website scraping."""

    colors: list[str] = Field(default_factory=list, description="Hex colors extracted from CSS")
    meta_description: str = Field(default="", description="Meta description tag content")
    og_title: str = Field(default="", description="Open Graph title")
    og_description: str = Field(default="", description="Open Graph description")
    og_image: str = Field(default="", description="Open Graph image URL")
    theme_color: str = Field(default="", description="Theme color meta tag")
    headlines: list[str] = Field(default_factory=list, description="H1 and H2 headlines")
    logo_candidates: list[str] = Field(
        default_factory=list, description="URLs of potential logos (not fetched)"
    )
    favicon_url: str = Field(default="", description="Favicon URL if found")


class ResearchCompleteness(BaseModel):
    """LLM evaluation of research completeness."""

    confidence: float = Field(ge=0, le=1, description="Confidence score 0-1")
    is_complete: bool = Field(description="Whether research is sufficient")
    missing_aspects: list[str] = Field(default_factory=list, description="Specific gaps to fill")
    suggested_queries: list[str] = Field(
        default_factory=list, description="Queries for gap-filling"
    )


class BrandResearchBundle(BaseModel):
    """Combined research results for brand creation."""

    brand_name: str
    website_url: str
    deep_research_summary: str = Field(default="", description="Summary from deep research")
    deep_research_sources: list[str] = Field(default_factory=list, description="Source URLs")
    website_assets: WebsiteAssets | None = Field(default=None, description="Scraped website data")
    gap_fill_results: list[str] = Field(
        default_factory=list, description="Results from gap-filling searches"
    )
    completeness: ResearchCompleteness | None = Field(default=None, description="Evaluation result")


class BrandCreationJob(BaseModel):
    """Persistent job state for brand creation from website."""

    schema_version: int = Field(default=1, description="Schema version for migrations")
    job_id: str = Field(description="Unique job identifier")
    brand_name: str = Field(description="User-provided brand name")
    website_url: str = Field(description="Brand website URL")
    slug: str = Field(description="Generated brand slug")
    status: JobStatus = Field(default="pending")
    phase: JobPhase = Field(default="starting")
    phase_detail: str | None = Field(default=None, description="Human-readable phase detail")
    percent_complete: int = Field(default=0, ge=0, le=100)
    error: str | None = Field(default=None, description="Error message if failed")
    error_code: str | None = Field(
        default=None, description="Error code: SSRF_BLOCKED, API_KEY_MISSING, etc."
    )
    cancel_requested: bool = Field(
        default=False, description="Cancellation flag for cooperative cancellation"
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    completed_at: datetime | None = Field(default=None, description="For tombstone TTL calculation")

    def validate_state(self) -> bool:
        """Validate status/phase combination is valid."""
        return (self.status, self.phase) in VALID_STATES

    def to_json_dict(self) -> dict:
        """Serialize to JSON-safe dict with ISO datetime strings."""
        return self.model_dump(mode="json")

    @classmethod
    def from_json_dict(cls, data: dict) -> "BrandCreationJob":
        """Deserialize from JSON dict."""
        return cls.model_validate(data)
