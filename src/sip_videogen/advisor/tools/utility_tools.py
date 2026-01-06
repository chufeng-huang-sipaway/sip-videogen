"""Utility tools for URL fetching and thinking visibility."""

from __future__ import annotations

import json
import os
import uuid
from time import time as _time

from agents import function_tool

from sip_videogen.config.logging import get_logger

logger = get_logger(__name__)
# URL content cache (10 min TTL)
_url_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 600


def _impl_fetch_url_content(url: str) -> str:
    """Fetch URL content as LLM-friendly markdown with caching."""
    logger.info(f"fetch_url_content called with url={url}")
    if url in _url_cache:
        content, ts = _url_cache[url]
        if _time() - ts < _CACHE_TTL:
            logger.info("Returning cached content")
            return content
    try:
        from firecrawl import Firecrawl
    except ImportError:
        logger.error("firecrawl-py not installed")
        return "Error: firecrawl-py not installed. Run: pip install firecrawl-py"
    api_key = os.environ.get("FIRECRAWL_API_KEY", "")
    logger.info(
        f"FIRECRAWL_API_KEY from env: {'set (' + api_key[:8] + '...)' if api_key else 'NOT SET'}"
    )
    if not api_key:
        return "Error: FireCrawl API key not configured. Please add your key in Brand Studio Settings (gear icon in sidebar)."
    try:
        logger.info("Calling FireCrawl API...")
        fc = Firecrawl(api_key=api_key)
        r = fc.scrape(url=url, formats=["markdown"], only_main_content=True)
        md = getattr(r, "markdown", "") or ""
        meta = getattr(r, "metadata", None)
        title = (
            meta.get("title", "")
            if isinstance(meta, dict)
            else getattr(meta, "title", "")
            if meta
            else ""
        )
        if md:
            content = f"# {title}\n\n{md}" if title else md
            _url_cache[url] = (content, _time())
            logger.info(f"Successfully fetched {len(content)} chars from {url}")
            return content
        logger.warning(f"No markdown content returned for {url}")
        return "Error: No content returned from URL"
    except Exception as e:
        logger.error(f"Exception in fetch_url_content: {e}")
        return f"Error fetching URL: {e}"


# Thinking visibility constants
_MAX_STEP_LEN = 100
_MAX_DETAIL_LEN = 500


def _build_thinking_step_result(step: str, detail: str, expertise: str | None = None) -> str:
    """Build JSON result string containing thinking step data."""
    s = step[:_MAX_STEP_LEN].strip() if step else "Thinking"
    d = detail[:_MAX_DETAIL_LEN].strip() if detail else ""
    data: dict = {
        "_thinking_step": True,
        "id": str(uuid.uuid4()),
        "step": s,
        "detail": d,
        "timestamp": int(_time() * 1000),
    }
    if expertise:
        data["expertise"] = expertise[:50].strip()
    return json.dumps(data)


def _impl_report_thinking(step: str, detail: str, expertise: str | None = None) -> str:
    """Report a thinking step to show reasoning to the user."""
    logger.debug(f"[THINKING] {step[:50]}")
    return _build_thinking_step_result(step, detail, expertise)


def parse_thinking_step_result(result: str) -> dict | None:
    """Parse thinking step data from tool result if present."""
    try:
        data = json.loads(result)
        if isinstance(data, dict) and data.get("_thinking_step"):
            r = {
                "id": data["id"],
                "step": data["step"],
                "detail": data["detail"],
                "timestamp": data["timestamp"],
            }
            if data.get("expertise"):
                r["expertise"] = data["expertise"]
            return r
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None


@function_tool
def fetch_url_content(url: str) -> str:
    """Fetch content from a URL and return as markdown.
    Use when user shares a URL and wants you to read or analyze its content.
    The content is automatically converted to clean markdown suitable for analysis.
    Args:
        url: The full URL to fetch (must include https://)
    Returns:
        Clean markdown content from the webpage, or error message if fetch fails.
    """
    return _impl_fetch_url_content(url)


@function_tool
def report_thinking(step: str, detail: str, expertise: str = "") -> str:
    """Report a thinking step to show the user your reasoning process.
    REQUIRED: Call this tool to explain what you're doing at each decision point.
    Users see these steps in a timeline, building trust in your process.
    Args:
        step: Brief title (2-8 words) in first-person voice describing this stage.
              Examples: "Setting the scene", "Considering your brand", "Crafting the shot"
        detail: Brief first-person explanation (1-2 sentences) of your thinking.
                Use "I'm", "Your brand", "I think" — focus on creative/technical decisions.
        expertise: Optional domain label for this decision. Include when relevant.
                   Values: "Visual Design", "Brand Strategy", "Copywriting", "Image Generation", "Research"
    Returns:
        Confirmation that thinking step was recorded.
    """
    exp = expertise if expertise else None
    return _impl_report_thinking(step, detail, exp)
