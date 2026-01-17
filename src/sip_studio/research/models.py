"""Pydantic models for research functionality."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# Category-specific TTL in days
TTL_BY_CATEGORY = {"trends": 14, "brand_analysis": 30, "techniques": 90}
# Stopwords for keyword extraction
STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "how",
    "what",
    "why",
    "do",
    "does",
    "for",
    "in",
    "on",
    "to",
    "of",
    "and",
    "or",
    "with",
}


def extract_keywords(query: str) -> list[str]:
    """Extract keywords from query, filtering stopwords."""
    words = re.findall(r"\b\w+\b", query.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


class ResearchSource(BaseModel):
    """Individual source/citation from research."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    url: str
    title: str
    snippet: str = ""


class ResearchEntry(BaseModel):
    """Cached research result."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str = Field(description="Unique ID for this research entry")
    query: str = Field(description="Original search query")
    keywords: list[str] = Field(default_factory=list, description="Keywords for matching")
    category: Literal["trends", "brand_analysis", "techniques"] = Field(
        default="trends", description="Research category"
    )
    brand_slug: str | None = Field(default=None, description="Associated brand slug")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_days: int = Field(default=14, description="TTL: 14/30/90 days")
    summary: str = Field(default="", description="Summary of research findings")
    sources: list[ResearchSource] = Field(default_factory=list)
    full_report_path: str = Field(default="", description="Path to full report markdown")

    def is_expired(self) -> bool:
        """Check if entry has exceeded TTL."""
        from datetime import timedelta

        return datetime.utcnow() > self.created_at + timedelta(days=self.ttl_days)


class ResearchRegistry(BaseModel):
    """Registry of all cached research."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    version: int = 1
    entries: list[ResearchEntry] = Field(default_factory=list)

    def find_by_keywords(
        self, query: str, brand_slug: str | None = None, category: str | None = None
    ) -> ResearchEntry | None:
        """Find cached research by keyword overlap.
        Rules:
        - Exact brand_slug match required if brand_slug provided
        - Category filter if specified
        - Keywords overlap >50% = match
        - Not expired
        """
        qkw = set(extract_keywords(query))
        if not qkw:
            return None
        for e in self.entries:
            if e.is_expired():
                continue
            if brand_slug is not None and e.brand_slug != brand_slug:
                continue
            if category is not None and e.category != category:
                continue
            ekw = set(e.keywords)
            if not ekw:
                continue
            overlap = len(qkw & ekw) / len(qkw)
            if overlap > 0.5:
                return e
        return None


class PendingResearch(BaseModel):
    """In-flight deep research job."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    response_id: str = Field(description="OpenAI response ID for polling")
    query: str = Field(description="Research query")
    brand_slug: str | None = Field(default=None)
    session_id: str = Field(description="Session that started this research")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_minutes: int = Field(default=15)
    current_stage: str | None = Field(default=None, description="Current research stage")


class PendingResearchList(BaseModel):
    """List of pending research jobs."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    version: int = 1
    jobs: list[PendingResearch] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """Result from polling research status."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    status: Literal["queued", "in_progress", "completed", "failed"]
    progress_percent: int | None = None
    partial_summary: str | None = None
    final_summary: str | None = None
    sources: list[ResearchSource] = Field(default_factory=list)
    full_report: str | None = None
    error: str | None = None
    current_stage: str | None = None


class ClarificationOption(BaseModel):
    """Option for a clarification question."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    value: str
    label: str
    recommended: bool = False


class ClarificationQuestion(BaseModel):
    """Single clarification question with options."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    question: str
    options: list[ClarificationOption]
    allow_custom: bool = False


class DeepResearchClarification(BaseModel):
    """Interaction type for deep research confirmation."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    type: Literal["deep_research_clarification"] = "deep_research_clarification"
    context_summary: str
    questions: list[ClarificationQuestion]
    estimated_duration: str
    query: str


class ClarificationResponse(BaseModel):
    """User's response to clarification."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    answers: dict[str, str] = Field(default_factory=dict, description="question_id -> value")
    confirmed: bool = False
