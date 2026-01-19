"""Deep research integration for brand creation.
Wraps existing ResearchService for brand creation use case with cooperative cancellation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from sip_studio.research.models import ResearchSource

from .models import BrandResearchBundle

log = logging.getLogger(__name__)
# Models and agents
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


def _build_brand_research_query(brand_name: str, website_url: str) -> str:
    """Build comprehensive deep research query for brand creation."""
    return f"""Research the brand "{brand_name}" with website {website_url}.
Provide comprehensive information about:
1. Brand history, founding story, and company background
2. Core products/services and unique value proposition
3. Target audience and market positioning
4. Brand voice, tone, and personality traits
5. Visual identity elements (colors, typography style, design aesthetic)
6. Competitor landscape and market differentiation
7. Company mission, vision, and values
8. Key messaging and taglines
9. Social media presence and communication style
10. Customer reviews and brand perception

Focus on factual information from official sources, press releases, and credible publications."""


class BrandResearchError(Exception):
    """Error during brand research operations."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


class BrandResearchWrapper:
    """Wrapper for deep research and web search for brand creation.
    Uses google-genai SDK directly to avoid coupling with ResearchService state management.
    """

    def __init__(self):
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Lazily create Gemini client."""
        if self._client is None:
            from sip_studio.config.settings import get_settings

            settings = get_settings()
            if not settings.gemini_api_key:
                raise BrandResearchError("GEMINI_API_KEY not configured", "API_KEY_MISSING")
            self._client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)
        return self._client

    async def trigger_deep_research(self, brand_name: str, website_url: str) -> str:
        """Start deep research for brand. Returns interaction_id for polling."""
        client = self._get_client()
        query = _build_brand_research_query(brand_name, website_url)
        try:
            interaction = await asyncio.to_thread(
                client.interactions.create, input=query, agent=DEEP_RESEARCH_AGENT, background=True
            )
            log.info("Started brand deep research: %s", interaction.id)
            return interaction.id
        except genai_errors.ClientError as e:
            log.exception("Gemini client error starting deep research: %s", e)
            raise BrandResearchError(f"Failed to start research: {e}", "RESEARCH_API_ERROR") from e
        except genai_errors.ServerError as e:
            log.exception("Gemini server error starting deep research: %s", e)
            raise BrandResearchError(
                f"Research service unavailable: {e}", "RESEARCH_API_ERROR"
            ) from e
        except Exception as e:
            log.exception("Failed to start deep research: %s", e)
            raise BrandResearchError(f"Unexpected error: {e}") from e

    async def poll_deep_research_with_cancellation(
        self,
        interaction_id: str,
        is_cancelled: Callable[[], bool],
        on_progress: Callable[[str], None] | None = None,
    ) -> tuple[str, list[str]]:
        """Poll deep research with cooperative cancellation.
        Args:
                interaction_id: Interaction ID from trigger_deep_research
                is_cancelled: Callback that returns True if cancellation requested
                on_progress: Optional callback for progress updates
        Returns:
                Tuple of (summary_text, source_urls)
        Raises:
                BrandResearchError: On failure or timeout
                asyncio.CancelledError: If cancelled (caller should handle)
        """
        client = self._get_client()
        start_time = asyncio.get_event_loop().time()
        delay: float = INITIAL_POLL_DELAY
        while True:
            # Check cancellation before each poll
            if is_cancelled():
                log.info("Brand research cancelled during polling")
                raise asyncio.CancelledError("Research cancelled by user")
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > MAX_POLL_DURATION:
                raise BrandResearchError(
                    f"Research timed out after {MAX_POLL_DURATION//60} minutes", "RESEARCH_TIMEOUT"
                )
            try:
                interaction = await asyncio.to_thread(client.interactions.get, interaction_id)
                raw_status = interaction.status
                # Update progress callback with stage info if available
                if on_progress:
                    stage = getattr(interaction, "thinking_summary", None)
                    if stage:
                        on_progress(str(stage)[:100])
                if raw_status == "queued":
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, MAX_POLL_DELAY)
                    continue
                if raw_status == "in_progress":
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, MAX_POLL_DELAY)
                    continue
                if raw_status == "completed":
                    text, sources = _extract_deep_research_result(interaction)
                    source_urls = [s.url for s in sources if s.url]
                    log.info(
                        "Brand deep research completed, summary length=%d, sources=%d",
                        len(text),
                        len(source_urls),
                    )
                    return text, source_urls
                # Failed
                error = getattr(interaction, "error", None) or "Unknown error"
                raise BrandResearchError(f"Research failed: {error}", "RESEARCH_FAILED")
            except genai_errors.ClientError as e:
                log.exception("Gemini client error polling research: %s", e)
                raise BrandResearchError(f"Polling error: {e}", "RESEARCH_API_ERROR") from e
            except genai_errors.ServerError as e:
                log.exception("Gemini server error polling research: %s", e)
                # Server errors may be transient, continue polling
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, MAX_POLL_DELAY)
                continue
            except asyncio.CancelledError:
                raise
            except BrandResearchError:
                raise
            except Exception as e:
                log.exception("Poll failed: %s", e)
                raise BrandResearchError(f"Unexpected polling error: {e}") from e

    async def web_search(self, query: str) -> tuple[str, list[str]]:
        """Immediate web search using Gemini grounding.
        Returns:
                Tuple of (result_text, source_urls)
        """
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
                return "No results found.", []
            source_urls = [s.url for s in sources if s.url]
            return text, source_urls
        except genai_errors.ClientError as e:
            log.exception("Gemini client error in web search: %s", e)
            return f"Search failed: {e}", []
        except genai_errors.ServerError as e:
            log.exception("Gemini server error in web search: %s", e)
            return f"Search temporarily unavailable: {e}", []
        except Exception as e:
            log.exception("Web search failed: %s", e)
            return f"Search failed: {e}", []

    async def gap_fill_search(self, queries: list[str], max_queries: int = 3) -> list[str]:
        """Run gap-filling web searches for missing information.
        Args:
                queries: List of search queries for gap-filling
                max_queries: Maximum number of queries to run
        Returns:
                List of result texts from searches
        """
        results = []
        for q in queries[:max_queries]:
            text, _ = await self.web_search(q)
            if text and not text.startswith("Search failed") and not text.startswith("No results"):
                results.append(f"Query: {q}\n{text}")
        return results


async def research_brand(
    brand_name: str,
    website_url: str,
    is_cancelled: Callable[[], bool],
    on_progress: Callable[[str], None] | None = None,
) -> BrandResearchBundle:
    """Execute full brand research pipeline.
    This is the main entry point for brand research. It:
    1. Triggers deep research
    2. Polls with cancellation support
    3. Returns a BrandResearchBundle with results
    Args:
            brand_name: Brand name to research
            website_url: Brand website URL
            is_cancelled: Callback returning True if cancellation requested
            on_progress: Optional callback for progress updates
    Returns:
            BrandResearchBundle with research results
    Raises:
            BrandResearchError: On failure
            asyncio.CancelledError: If cancelled
    """
    wrapper = BrandResearchWrapper()
    # Start deep research
    interaction_id = await wrapper.trigger_deep_research(brand_name, website_url)
    # Poll for completion
    summary, sources = await wrapper.poll_deep_research_with_cancellation(
        interaction_id, is_cancelled, on_progress
    )
    return BrandResearchBundle(
        brand_name=brand_name,
        website_url=website_url,
        deep_research_summary=summary,
        deep_research_sources=sources,
    )
