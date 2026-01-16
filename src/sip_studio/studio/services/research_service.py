"""Research service for web search and deep research."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from sip_studio.research.models import (
    ClarificationResponse,
    ResearchEntry,
    ResearchResult,
    ResearchSource,
)
from sip_studio.research.storage import ResearchStorage

from ..utils.bridge_types import bridge_error, bridge_ok

if TYPE_CHECKING:
    from ..state import BridgeState
log = logging.getLogger(__name__)
# Default models
WEB_SEARCH_MODEL = "gpt-4.1"
DEEP_RESEARCH_MODEL = "o4-mini-deep-research-2025-06-26"
# Polling config
MAX_POLL_DURATION = 45 * 60  # 45 minutes max
INITIAL_POLL_DELAY = 5  # seconds
MAX_POLL_DELAY = 30  # seconds


def _extract_research_result(response) -> tuple[str, list[ResearchSource]]:
    """Extract text and sources from Responses API output."""
    text_parts = []
    sources = []
    for item in getattr(response, "output", []):
        if hasattr(item, "content"):
            for c in item.content:
                if hasattr(c, "text"):
                    text_parts.append(c.text)
                if hasattr(c, "annotations"):
                    for ann in c.annotations:
                        if hasattr(ann, "url"):
                            sources.append(
                                ResearchSource(
                                    url=ann.url,
                                    title=getattr(ann, "title", ""),
                                    snippet=getattr(ann, "text", ""),
                                )
                            )
    return "\n\n".join(text_parts), sources


def _build_research_query(original: str, answers: dict[str, str]) -> str:
    """Refine query based on clarification answers."""
    parts = [original]
    if focus := answers.get("focus"):
        parts.append(f"Focus on: {focus}")
    if depth := answers.get("depth"):
        if depth == "quick":
            parts.append("Provide a concise overview.")
        else:
            parts.append("Provide comprehensive analysis with examples.")
    for k, v in answers.items():
        if v.startswith("custom:"):
            parts.append(f"{k}: {v[7:]}")
    return " | ".join(parts)


class ResearchService:
    """Research caching, web search, and deep research job management."""

    def __init__(self, state: BridgeState):
        self._state = state
        self._storage = ResearchStorage()
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        """Lazily create OpenAI client."""
        if self._client is None:
            from sip_studio.config.settings import get_settings

            settings = get_settings()
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._client

    # Cache operations
    def find_cached_research(
        self, query: str, brand_slug: str | None = None, category: str | None = None
    ) -> ResearchEntry | None:
        """Find cached research by keyword matching."""
        return self._storage.find_cached(query, brand_slug, category)

    def get_research_entry(self, entry_id: str) -> dict:
        """Get a research entry by ID."""
        entry = self._storage.get_entry(entry_id)
        if not entry:
            return bridge_error(f"Research entry not found: {entry_id}")
        return bridge_ok(entry.model_dump(by_alias=True))

    def get_full_report(self, entry_id: str) -> dict:
        """Get full report content for an entry."""
        report = self._storage.get_full_report(entry_id)
        if report is None:
            return bridge_error(f"Report not found for entry: {entry_id}")
        return bridge_ok({"content": report})

    def list_research(self, brand_slug: str | None = None, category: str | None = None) -> dict:
        """List cached research entries, optionally filtered."""
        reg = self._storage.load_registry()
        entries = reg.entries
        if brand_slug:
            entries = [e for e in entries if e.brand_slug == brand_slug]
        if category:
            entries = [e for e in entries if e.category == category]
        entries = [e for e in entries if not e.is_expired()]
        return bridge_ok({"entries": [e.model_dump(by_alias=True) for e in entries]})

    def cleanup_expired(self) -> dict:
        """Remove expired research entries."""
        count = self._storage.cleanup_expired()
        return bridge_ok({"removed": count})

    # Web search (immediate)
    async def trigger_web_search(self, query: str) -> str:
        """Immediate web search using OpenAI web_search_preview tool."""
        client = self._get_client()
        try:
            response = await client.responses.create(
                model=WEB_SEARCH_MODEL,
                input=[{"role": "user", "content": query}],
                tools=[{"type": "web_search_preview"}],
            )
            text, sources = _extract_research_result(response)
            if not text:
                return "No results found for query."
            sources_str = "\n".join(f"- [{s.title or s.url}]({s.url})" for s in sources[:10])
            return f"{text}\n\nSources:\n{sources_str}" if sources_str else text
        except Exception as e:
            log.exception("Web search failed: %s", e)
            return f"Web search failed: {e}"

    # Deep research (background)
    async def trigger_deep_research(
        self, query: str, brand_slug: str | None, session_id: str
    ) -> str:
        """Start deep research in background mode. Returns response_id for polling."""
        client = self._get_client()
        try:
            response = await client.responses.create(
                model=DEEP_RESEARCH_MODEL,
                input=[{"role": "user", "content": query}],
                reasoning={"summary": "auto"},
                tools=[{"type": "web_search_preview"}],
                background=True,
            )
            response_id = response.id
            self._storage.add_pending(
                response_id=response_id,
                query=query,
                brand_slug=brand_slug,
                session_id=session_id,
                estimated_minutes=15,
            )
            log.info("Started deep research: %s", response_id)
            return response_id
        except Exception as e:
            log.exception("Failed to start deep research: %s", e)
            raise

    async def poll_deep_research(self, response_id: str) -> ResearchResult:
        """Poll a pending research job. If complete, saves to cache."""
        client = self._get_client()
        try:
            response = await client.responses.retrieve(response_id)
            raw_status = response.status
            if raw_status == "queued":
                return ResearchResult(
                    status="queued", progress_percent=getattr(response, "progress", None)
                )
            if raw_status == "in_progress":
                return ResearchResult(
                    status="in_progress", progress_percent=getattr(response, "progress", None)
                )
            if raw_status == "completed":
                text, sources = _extract_research_result(response)
                # Get pending info for category/brand
                pending = self._storage.get_pending(response_id)
                if pending:
                    self._storage.add_entry(
                        query=pending.query,
                        category="techniques",
                        brand_slug=pending.brand_slug,
                        summary=text[:2000] if len(text) > 2000 else text,
                        sources=sources,
                        full_report=text if len(text) > 2000 else None,
                    )
                    self._storage.remove_pending(response_id)
                return ResearchResult(
                    status="completed",
                    final_summary=text,
                    sources=sources,
                    full_report=text if len(text) > 2000 else None,
                )
            # Failed
            error = getattr(response, "error", None) or "Unknown error"
            self._storage.remove_pending(response_id)
            return ResearchResult(status="failed", error=str(error))
        except Exception as e:
            log.exception("Poll failed: %s", e)
            return ResearchResult(status="failed", error=str(e))

    # Pending jobs
    def get_pending_for_session(self, session_id: str) -> list:
        """Get pending jobs for a specific session."""
        jobs = self._storage.get_pending_by_session(session_id)
        return [j.model_dump(by_alias=True) for j in jobs]

    def recover_pending_research(self) -> list:
        """Get all pending jobs for recovery."""
        jobs = self._storage.get_all_pending()
        return [j.model_dump(by_alias=True) for j in jobs]

    def cancel_pending(self, response_id: str) -> bool:
        """Remove from pending (can't actually cancel API job)."""
        return self._storage.remove_pending(response_id)

    # Execute after clarification
    def execute_deep_research(
        self, clarification_response: dict, original_query: str, session_id: str
    ) -> dict:
        """Execute deep research after user confirms clarification."""
        try:
            resp = ClarificationResponse.model_validate(clarification_response)
            if not resp.confirmed:
                return bridge_ok({"status": "cancelled"})
            refined_query = _build_research_query(original_query, resp.answers)
            brand_slug = self._state.get_active_slug()
            response_id = asyncio.run(
                self.trigger_deep_research(refined_query, brand_slug, session_id)
            )
            return bridge_ok({"response_id": response_id, "status": "started"})
        except Exception as e:
            log.exception("Execute deep research failed: %s", e)
            return bridge_error(str(e))

    # Bridge method wrappers (sync)
    def find_research(self, query: str, category: str | None = None) -> dict:
        """Find cached research (bridge method)."""
        brand_slug = self._state.get_active_slug()
        entry = self.find_cached_research(query, brand_slug, category)
        if not entry:
            return bridge_ok({"found": False})
        return bridge_ok({"found": True, "entry": entry.model_dump(by_alias=True)})

    def start_web_search(self, query: str) -> dict:
        """Trigger web search (bridge method)."""
        try:
            result = asyncio.run(self.trigger_web_search(query))
            return bridge_ok({"result": result})
        except Exception as e:
            return bridge_error(str(e))

    def start_deep_research(self, query: str, session_id: str) -> dict:
        """Start deep research (bridge method)."""
        try:
            brand_slug = self._state.get_active_slug()
            response_id = asyncio.run(self.trigger_deep_research(query, brand_slug, session_id))
            return bridge_ok({"response_id": response_id})
        except Exception as e:
            return bridge_error(str(e))

    def poll_research(self, response_id: str) -> dict:
        """Poll research status (bridge method)."""
        try:
            result = asyncio.run(self.poll_deep_research(response_id))
            return bridge_ok(result.model_dump(by_alias=True))
        except Exception as e:
            return bridge_error(str(e))

    def get_pending_research(self) -> dict:
        """Get all pending jobs (bridge method)."""
        jobs = self.recover_pending_research()
        return bridge_ok({"jobs": jobs})

    def cancel_research(self, response_id: str) -> dict:
        """Cancel/dismiss pending research (bridge method)."""
        success = self.cancel_pending(response_id)
        return bridge_ok({"cancelled": success})
