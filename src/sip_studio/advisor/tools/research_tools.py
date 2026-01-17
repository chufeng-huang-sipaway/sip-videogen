"""Research tools for web search and deep research."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from agents import function_tool

from sip_studio.config.logging import get_logger
from sip_studio.research.models import (
    ClarificationOption,
    ClarificationQuestion,
)

from . import _common

if TYPE_CHECKING:
    from sip_studio.studio.services.research_service import ResearchService
logger = get_logger(__name__)
# Module-level state for pending research clarification (same pattern as _pending_interaction)
_pending_research_clarification: dict | None = None
_research_service_factory: Callable[[], ResearchService] | None = None


def set_research_service_factory(factory: Callable[[], ResearchService] | None) -> None:
    """Set factory for getting ResearchService. Called by bridge on init."""
    global _research_service_factory
    _research_service_factory = factory


def _get_research_service() -> "ResearchService":
    """Get ResearchService instance."""
    if _research_service_factory is None:
        raise RuntimeError(
            "ResearchService factory not set. Call set_research_service_factory first."
        )
    return _research_service_factory()


def get_pending_research_clarification() -> dict | None:
    """Get and clear pending research clarification."""
    global _pending_research_clarification
    result = _pending_research_clarification
    _pending_research_clarification = None
    return result


def peek_pending_research_clarification() -> dict | None:
    """Check pending research clarification without clearing it."""
    return _pending_research_clarification


def has_pending_research_clarification() -> bool:
    """Return True if a research clarification panel is pending."""
    return _pending_research_clarification is not None


async def _impl_web_search(query: str) -> str:
    """Implementation - calls ResearchService.trigger_web_search."""
    # DEBUG: Log when web_search tool is actually called
    logger.info("[web_search] TOOL CALLED with query=%s", query)
    service = _get_research_service()
    brand_slug = _common.get_active_brand()
    # Check cache first
    cached = service.find_cached_research(query, brand_slug, "trends")
    if cached:
        sources_str = "\n".join(f"- [{s.title or s.url}]({s.url})" for s in cached.sources[:10])
        return (
            f"[From cache - {cached.created_at.strftime('%Y-%m-%d')}]\n{cached.summary}\n\nSources:\n{sources_str}"
            if sources_str
            else f"[From cache]\n{cached.summary}"
        )
    # Trigger web search (now properly async)
    result = await service.trigger_web_search(query)
    return result


@function_tool
async def web_search(query: str) -> str:
    """Search the web for current brand/trend information.
    Use when you need up-to-date information not in your training data.
    Results include sources with URLs for verification.
    Args:
        query: Search query (e.g., "premium coffee packaging trends 2024")
    Returns:
        Search results with summaries and source links.
    """
    return await _impl_web_search(query)


def _impl_request_deep_research(query: str, context: str) -> str:
    """Set pending clarification interaction (like propose_choices)."""
    # DEBUG: Log when request_deep_research tool is actually called
    logger.info(
        "[request_deep_research] TOOL CALLED with query=%s, context=%s", query, context[:100]
    )
    global _pending_research_clarification
    # Build ClarificationQuestions based on query analysis
    questions = [
        ClarificationQuestion(
            id="focus",
            question="What aspect should I focus on?",
            options=[
                ClarificationOption(value="visual", label="Visual trends", recommended=True),
                ClarificationOption(value="messaging", label="Messaging & copy"),
                ClarificationOption(value="positioning", label="Market positioning"),
            ],
            allow_custom=True,
        ),
        ClarificationQuestion(
            id="depth",
            question="How comprehensive should the research be?",
            options=[
                ClarificationOption(value="quick", label="Quick overview (10-15 min)"),
                ClarificationOption(
                    value="thorough", label="Thorough analysis (20-30 min)", recommended=True
                ),
            ],
        ),
    ]
    _pending_research_clarification = {
        "type": "deep_research_clarification",
        "contextSummary": context,
        "questions": [q.model_dump(by_alias=True) for q in questions],
        "estimatedDuration": "15-20 minutes",
        "query": query,
    }
    return "[Presenting deep research options to user]"


@function_tool
def request_deep_research(query: str, context: str) -> str:
    """Request comprehensive deep research on a topic.
    IMPORTANT: This presents a confirmation dialog to the user before starting.
    Deep research takes 10-30 minutes and searches extensively across the web.
    Use for complex questions requiring thorough investigation:
    - "How do luxury skincare brands photograph products?"
    - "What packaging innovations are trending in sustainable food?"
    Args:
        query: The research question
        context: Your understanding of what the user wants to learn
    Returns:
        Confirmation that options are being presented to the user.
    """
    return _impl_request_deep_research(query, context)


async def _impl_get_research_status(response_id: str) -> str:
    """Implementation for research status polling."""
    service = _get_research_service()
    result = await service.poll_deep_research(response_id)
    if result.status == "completed":
        sources_str = ""
        if result.sources:
            sources_str = "\n\nSources:\n" + "\n".join(
                f"- [{s.title or s.url}]({s.url})" for s in result.sources[:10]
            )
        return f"Research complete!\n\n{result.final_summary}{sources_str}"
    elif result.status == "failed":
        return f"Research failed: {result.error}"
    else:
        progress = f" ({result.progress_percent}%)" if result.progress_percent else ""
        return f"Research in progress{progress}... Status: {result.status}"


@function_tool
async def get_research_status(response_id: str) -> str:
    """Check status of a pending deep research job.
    Args:
        response_id: The ID returned when research was started
    Returns:
        Status update with progress or results.
    """
    return await _impl_get_research_status(response_id)


def _impl_search_research_cache(keywords: list[str], category: str | None = None) -> str:
    """Search cached research entries."""
    service = _get_research_service()
    brand_slug = _common.get_active_brand()
    query = " ".join(keywords)
    entry = service.find_cached_research(query, brand_slug, category)
    if not entry:
        return "No cached research found matching those keywords."
    sources_str = ""
    if entry.sources:
        sources_str = "\n\nSources:\n" + "\n".join(
            f"- [{s.title or s.url}]({s.url})" for s in entry.sources[:5]
        )
    return f"**{entry.query}** (cached {entry.created_at.strftime('%Y-%m-%d')})\n\n{entry.summary}{sources_str}"


@function_tool
def search_research_cache(keywords: list[str], category: str | None = None) -> str:
    """Search cached research before triggering new research.
    Use this to check if relevant research already exists before
    requesting a new web search or deep research.
    Args:
        keywords: Keywords to search for
        category: Optional filter (trends, brand_analysis, techniques)
    Returns:
        Matching research summaries or "No cached research found"
    """
    return _impl_search_research_cache(keywords, category)


# List of research tools (conditionally added to ADVISOR_TOOLS)
RESEARCH_TOOLS = [web_search, request_deep_research, get_research_status, search_research_cache]
