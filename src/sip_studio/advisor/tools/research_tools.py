"""Research tools for web search and deep research."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from agents import function_tool
from pydantic import BaseModel

from sip_studio.config.logging import get_logger
from sip_studio.research.models import ClarificationOption, ClarificationQuestion

from . import _common

if TYPE_CHECKING:
    from sip_studio.studio.services.research_service import ResearchService
logger = get_logger(__name__)


# Pydantic models for tool parameters (required by OpenAI Agents SDK strict schema)
class ToolOptionInput(BaseModel):
    """Option for a clarification question."""

    value: str
    label: str
    recommended: bool = False


class ToolQuestionInput(BaseModel):
    """Clarification question with options."""

    id: str
    question: str
    options: list[ToolOptionInput]
    allow_custom: bool = False


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


def _impl_request_deep_research(
    query: str, questions: list[ToolQuestionInput], estimated_duration: str = "15-20 minutes"
) -> str:
    """Set pending clarification with agent-constructed questions."""
    logger.info(
        "[request_deep_research] TOOL CALLED with query=%s, %d questions", query, len(questions)
    )
    global _pending_research_clarification
    # Convert to internal ClarificationQuestion models
    validated = [
        ClarificationQuestion(
            id=q.id,
            question=q.question,
            options=[
                ClarificationOption(value=o.value, label=o.label, recommended=o.recommended)
                for o in q.options
            ],
            allow_custom=q.allow_custom,
        )
        for q in questions
    ]
    _pending_research_clarification = {
        "type": "deep_research_clarification",
        "questions": [q.model_dump(by_alias=True) for q in validated],
        "estimatedDuration": estimated_duration,
        "query": query,
    }
    return "[Presenting clarification questions to user]"


@function_tool
def request_deep_research(
    query: str, questions: list[ToolQuestionInput], estimated_duration: str = "15-20 minutes"
) -> str:
    """Request deep research with custom clarification questions.
    IMPORTANT: Construct questions tailored to the user's specific request.
    Each question should have a recommended option based on your understanding.
    Args:
        query: The research question
        questions: List of clarification questions. Each question has:
            - id: unique identifier (e.g., "focus", "scope", "format")
            - question: The question text
            - options: List of options with value, label, and recommended (exactly ONE should be True)
            - allow_custom: bool (optional, default False)
        estimated_duration: e.g. "10-15 minutes" or "20-30 minutes"
    Example questions based on user intent:
    - For visual research: focus areas (photography style, color palettes, composition)
    - For competitive analysis: which competitors, what aspects
    - For trends research: timeframe, geographic scope, sub-categories
    Returns:
        Confirmation that clarification questions are being presented.
    """
    return _impl_request_deep_research(query, questions, estimated_duration)


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
