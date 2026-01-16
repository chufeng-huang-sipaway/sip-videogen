"""File storage for research entries and pending jobs."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Literal

from sip_studio.utils.file_utils import write_atomically

from .models import (
    TTL_BY_CATEGORY,
    PendingResearch,
    PendingResearchList,
    ResearchEntry,
    ResearchRegistry,
    ResearchSource,
    extract_keywords,
)

ResearchCategory = Literal["trends", "brand_analysis", "techniques"]

log = logging.getLogger(__name__)


def _get_research_dir() -> Path:
    """Get the research directory path."""
    return Path.home() / ".sip-studio" / "research"


def _get_registry_path() -> Path:
    return _get_research_dir() / "registry.json"


def _get_pending_path() -> Path:
    return _get_research_dir() / "pending.json"


def _get_reports_dir() -> Path:
    return _get_research_dir() / "reports"


class ResearchStorage:
    """Storage layer for research entries and pending jobs."""

    def __init__(self):
        self._dir = _get_research_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        _get_reports_dir().mkdir(parents=True, exist_ok=True)

    # Registry operations
    def load_registry(self) -> ResearchRegistry:
        """Load registry, recovering gracefully from corruption."""
        p = _get_registry_path()
        if not p.exists():
            return ResearchRegistry()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return ResearchRegistry.model_validate(data)
        except Exception as e:
            log.warning(f"Corrupt registry, recreating: {e}")
            return ResearchRegistry()

    def save_registry(self, reg: ResearchRegistry) -> None:
        """Atomically save registry."""
        write_atomically(_get_registry_path(), reg.model_dump_json(by_alias=True, indent=2))

    def find_cached(
        self, query: str, brand_slug: str | None = None, category: str | None = None
    ) -> ResearchEntry | None:
        """Find cached research by keyword matching."""
        reg = self.load_registry()
        return reg.find_by_keywords(query, brand_slug, category)

    def add_entry(
        self,
        query: str,
        category: ResearchCategory,
        brand_slug: str | None,
        summary: str,
        sources: list[ResearchSource],
        full_report: str | None = None,
    ) -> ResearchEntry:
        """Add new research entry to registry."""
        eid = str(uuid.uuid4())[:8]
        report_path = ""
        if full_report:
            rp = _get_reports_dir() / f"{eid}.md"
            write_atomically(rp, full_report)
            report_path = str(rp)
        ttl = TTL_BY_CATEGORY.get(category, 14)
        entry = ResearchEntry(
            id=eid,
            query=query,
            keywords=extract_keywords(query),
            category=category,
            brand_slug=brand_slug,
            ttl_days=ttl,
            summary=summary,
            sources=sources,
            full_report_path=report_path,
        )
        reg = self.load_registry()
        reg.entries.append(entry)
        self.save_registry(reg)
        return entry

    def get_entry(self, entry_id: str) -> ResearchEntry | None:
        """Get entry by ID."""
        reg = self.load_registry()
        for e in reg.entries:
            if e.id == entry_id:
                return e
        return None

    def get_full_report(self, entry_id: str) -> str | None:
        """Get full report content for an entry."""
        e = self.get_entry(entry_id)
        if not e or not e.full_report_path:
            return None
        p = Path(e.full_report_path)
        if not p.exists():
            return None
        return p.read_text(encoding="utf-8")

    def cleanup_expired(self) -> int:
        """Remove expired entries and their reports. Returns count removed."""
        reg = self.load_registry()
        before = len(reg.entries)
        kept = []
        for e in reg.entries:
            if e.is_expired():
                if e.full_report_path:
                    try:
                        Path(e.full_report_path).unlink(missing_ok=True)
                    except Exception:
                        pass
            else:
                kept.append(e)
        reg.entries = kept
        self.save_registry(reg)
        return before - len(kept)

    # Pending jobs operations
    def load_pending(self) -> PendingResearchList:
        """Load pending jobs, recovering gracefully from corruption."""
        p = _get_pending_path()
        if not p.exists():
            return PendingResearchList()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return PendingResearchList.model_validate(data)
        except Exception as e:
            log.warning(f"Corrupt pending list, recreating: {e}")
            return PendingResearchList()

    def save_pending(self, pl: PendingResearchList) -> None:
        """Atomically save pending list."""
        write_atomically(_get_pending_path(), pl.model_dump_json(by_alias=True, indent=2))

    def add_pending(
        self,
        response_id: str,
        query: str,
        brand_slug: str | None,
        session_id: str,
        estimated_minutes: int = 15,
    ) -> PendingResearch:
        """Add new pending research job."""
        job = PendingResearch(
            response_id=response_id,
            query=query,
            brand_slug=brand_slug,
            session_id=session_id,
            estimated_minutes=estimated_minutes,
        )
        pl = self.load_pending()
        pl.jobs.append(job)
        self.save_pending(pl)
        return job

    def remove_pending(self, response_id: str) -> bool:
        """Remove pending job by response_id. Returns True if found."""
        pl = self.load_pending()
        before = len(pl.jobs)
        pl.jobs = [j for j in pl.jobs if j.response_id != response_id]
        self.save_pending(pl)
        return len(pl.jobs) < before

    def get_pending_by_session(self, session_id: str) -> list[PendingResearch]:
        """Get all pending jobs for a session."""
        pl = self.load_pending()
        return [j for j in pl.jobs if j.session_id == session_id]

    def get_all_pending(self) -> list[PendingResearch]:
        """Get all pending jobs for recovery."""
        return self.load_pending().jobs

    def get_pending(self, response_id: str) -> PendingResearch | None:
        """Get pending job by response_id."""
        pl = self.load_pending()
        for j in pl.jobs:
            if j.response_id == response_id:
                return j
        return None
