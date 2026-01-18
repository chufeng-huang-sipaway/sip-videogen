"""Research service for web search and deep research using Gemini."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from packaging.version import Version

from sip_studio.research.models import (
    ClarificationResponse,
    PendingResearch,
    ResearchEntry,
    ResearchResult,
    ResearchSource,
)
from sip_studio.research.storage import ResearchStorage

from ..utils.bridge_types import bridge_error, bridge_ok

if TYPE_CHECKING:
    from ..state import BridgeState

log = logging.getLogger(__name__)

# Version check - interactions API requires 1.55.0+
MIN_GENAI_VERSION = "1.55.0"
_genai_version = getattr(genai, "__version__", "0.0.0")
if Version(_genai_version) < Version(MIN_GENAI_VERSION):
    log.warning(
        "google-genai version %s is below minimum %s. "
        "Deep research may not work. Please upgrade: pip install 'google-genai>=%s'",
        _genai_version,
        MIN_GENAI_VERSION,
        MIN_GENAI_VERSION,
    )
# Gemini models and agents
WEB_SEARCH_MODEL = "gemini-2.5-flash"
DEEP_RESEARCH_AGENT = "deep-research-pro-preview-12-2025"
# Polling config
MAX_POLL_DURATION = 45 * 60  # 45 minutes max
INITIAL_POLL_DELAY = 5  # seconds
MAX_POLL_DELAY = 30  # seconds


def _extract_grounding_sources(response) -> tuple[str, list[ResearchSource]]:
    """Extract text and sources from Gemini grounding response."""
    text = response.text or ""
    sources = []
    if response.candidates and len(response.candidates) > 0:
        gm = getattr(response.candidates[0], "grounding_metadata", None)
        if gm:
            for chunk in getattr(gm, "grounding_chunks", []) or []:
                web = getattr(chunk, "web", None)
                if web:
                    sources.append(
                        ResearchSource(
                            url=getattr(web, "uri", ""), title=getattr(web, "title", ""), snippet=""
                        )
                    )
    return text, sources


def _extract_deep_research_result(interaction) -> tuple[str, list[ResearchSource]]:
    """Extract text and sources from deep research interaction."""
    text = ""
    sources = []
    if interaction.outputs and len(interaction.outputs) > 0:
        last_output = interaction.outputs[-1]
        text = getattr(last_output, "text", "") or ""
    # Deep research may include grounding in metadata
    if hasattr(interaction, "grounding_metadata") and interaction.grounding_metadata:
        gm = interaction.grounding_metadata
        for chunk in getattr(gm, "grounding_chunks", []) or []:
            web = getattr(chunk, "web", None)
            if web:
                sources.append(
                    ResearchSource(
                        url=getattr(web, "uri", ""), title=getattr(web, "title", ""), snippet=""
                    )
                )
    return text, sources


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
    """Research caching, web search, and deep research job management using Gemini."""

    def __init__(self, state: BridgeState):
        self._state = state
        self._storage = ResearchStorage()
        self._client: genai.Client | None = None

    def _persist_deep_research_result_to_session(
        self,
        pending: PendingResearch,
        response_id: str,
        final_summary: str,
        sources: list[ResearchSource],
    ) -> None:
        """Persist deep research result into the originating chat session history.

        This ensures results show up in chat history after restarts/session switching.
        """
        brand_slug = pending.brand_slug
        session_id = pending.session_id
        if not brand_slug or not session_id:
            return
        try:
            from sip_studio.advisor.session_history_manager import SessionHistoryManager
            from sip_studio.advisor.session_manager import Message, SessionManager

            mgr = SessionManager(brand_slug)
            if not mgr.get_session(session_id):
                log.warning(
                    "Cannot persist deep research result: session not found (brand=%s, session=%s)",
                    brand_slug,
                    session_id,
                )
                return
            history = SessionHistoryManager(brand_slug, session_id, mgr)
            summary = (final_summary or "").strip()
            content = (
                f"**Deep Research Complete**\n\n{summary}"
                if summary
                else "**Deep Research Complete**"
            )
            meta = {
                "deep_research": {
                    "response_id": response_id,
                    "query": pending.query,
                    "sources": [s.model_dump(by_alias=True) for s in sources[:10]],
                }
            }
            history.add_message(Message.create("assistant", content, metadata=meta))
        except Exception as e:
            log.exception("Failed to persist deep research result to session history: %s", e)

    def _get_client(self) -> genai.Client:
        """Lazily create Gemini client."""
        if self._client is None:
            from sip_studio.config.settings import get_settings

            settings = get_settings()
            self._client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)
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
        return bridge_ok(entry.model_dump(by_alias=True, mode="json"))

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
        return bridge_ok({"entries": [e.model_dump(by_alias=True, mode="json") for e in entries]})

    def cleanup_expired(self) -> dict:
        """Remove expired research entries."""
        count = self._storage.cleanup_expired()
        return bridge_ok({"removed": count})

    # Web search (immediate) using Gemini grounding
    async def trigger_web_search(self, query: str) -> str:
        """Immediate web search using Gemini grounding with Google Search."""
        client = self._get_client()
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=WEB_SEARCH_MODEL,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                ),
            )
            text, sources = _extract_grounding_sources(response)
            if not text:
                return "No results found for query."
            sources_str = "\n".join(f"- [{s.title or s.url}]({s.url})" for s in sources[:10])
            return f"{text}\n\nSources:\n{sources_str}" if sources_str else text
        except genai_errors.ClientError as e:
            log.exception("Gemini client error in web search: %s", e)
            return f"Web search failed: {e}"
        except genai_errors.ServerError as e:
            log.exception("Gemini server error in web search: %s", e)
            return f"Web search temporarily unavailable: {e}"
        except Exception as e:
            log.exception("Web search failed: %s", e)
            return f"Web search failed: {e}"

    # Deep research (background) using Gemini interactions
    async def trigger_deep_research(
        self, query: str, brand_slug: str | None, session_id: str
    ) -> str:
        """Start deep research in background mode. Returns interaction_id for polling."""
        client = self._get_client()
        try:
            interaction = await asyncio.to_thread(
                client.interactions.create,  # type: ignore[attr-defined]
                input=query,
                agent=DEEP_RESEARCH_AGENT,
                background=True,
            )
            interaction_id = interaction.id
            self._storage.add_pending(
                response_id=interaction_id,
                query=query,
                brand_slug=brand_slug,
                session_id=session_id,
                estimated_minutes=15,
            )
            log.info("Started deep research: %s", interaction_id)
            return interaction_id
        except genai_errors.ClientError as e:
            log.exception("Gemini client error starting deep research: %s", e)
            raise
        except genai_errors.ServerError as e:
            log.exception("Gemini server error starting deep research: %s", e)
            raise
        except Exception as e:
            log.exception("Failed to start deep research: %s", e)
            raise

    async def poll_deep_research(self, response_id: str) -> ResearchResult:
        """Poll a pending research job. If complete, saves to cache."""
        client = self._get_client()
        try:
            interaction = await asyncio.to_thread(client.interactions.get, response_id)  # type: ignore[attr-defined]
            raw_status = interaction.status
            # Get current_stage from pending cache
            pending = self._storage.get_pending(response_id)
            current_stage = pending.current_stage if pending else None
            # Try to extract stage from interaction metadata if available
            if hasattr(interaction, "thinking_summary") and interaction.thinking_summary:
                current_stage = str(interaction.thinking_summary)[:100]
                if pending:
                    self._storage.update_pending_stage(response_id, current_stage)
            if raw_status == "queued":
                return ResearchResult(
                    status="queued", progress_percent=None, current_stage=current_stage
                )
            if raw_status == "in_progress":
                return ResearchResult(
                    status="in_progress", progress_percent=None, current_stage=current_stage
                )
            if raw_status == "completed":
                text, sources = _extract_deep_research_result(interaction)
                # Get pending info for category/brand
                pending = self._storage.get_pending(response_id)
                if pending:
                    # Only the first completion poll should persist/cache results.
                    # Use removal as the idempotency gate to avoid duplicates.
                    if self._storage.remove_pending(response_id):
                        self._persist_deep_research_result_to_session(
                            pending, response_id, text, sources
                        )
                        self._storage.add_entry(
                            query=pending.query,
                            category="techniques",
                            brand_slug=pending.brand_slug,
                            summary=text[:2000] if len(text) > 2000 else text,
                            sources=sources,
                            full_report=text if len(text) > 2000 else None,
                        )
                return ResearchResult(
                    status="completed",
                    final_summary=text,
                    sources=sources,
                    full_report=text if len(text) > 2000 else None,
                )
            # Failed
            error = getattr(interaction, "error", None) or "Unknown error"
            self._storage.remove_pending(response_id)
            return ResearchResult(status="failed", error=str(error))
        except genai_errors.ClientError as e:
            log.exception("Gemini client error polling research: %s", e)
            return ResearchResult(status="failed", error=str(e))
        except genai_errors.ServerError as e:
            log.exception("Gemini server error polling research: %s", e)
            return ResearchResult(status="failed", error=str(e))
        except Exception as e:
            log.exception("Poll failed: %s", e)
            return ResearchResult(status="failed", error=str(e))

    # Pending jobs
    def get_pending_for_session(self, session_id: str) -> list:
        """Get pending jobs for a specific session."""
        jobs = self._storage.get_pending_by_session(session_id)
        return [j.model_dump(by_alias=True, mode="json") for j in jobs]

    def recover_pending_research(self) -> list:
        """Get all pending jobs for recovery."""
        jobs = self._storage.get_all_pending()
        return [j.model_dump(by_alias=True, mode="json") for j in jobs]

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
        return bridge_ok({"found": True, "entry": entry.model_dump(by_alias=True, mode="json")})

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
