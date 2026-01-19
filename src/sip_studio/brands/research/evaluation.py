"""LLM-based evaluation of research completeness for brand creation.
Uses Gemini Flash for structured evaluation with confidence scoring.
"""

from __future__ import annotations

import asyncio
import json
import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from .models import BrandResearchBundle, ResearchCompleteness

log = logging.getLogger(__name__)
EVALUATION_MODEL = "gemini-2.5-flash"
# Required aspects for brand identity creation
REQUIRED_ASPECTS = [
    "brand_history",
    "products_services",
    "target_audience",
    "brand_voice",
    "visual_identity",
    "competitors",
    "mission_values",
]
EVALUATION_SYSTEM_PROMPT = """You are a brand research evaluator. Analyze research completeness for brand identity creation.
Evaluate if the research contains sufficient information for these aspects:
1. Brand history/founding story
2. Products/services offered
3. Target audience
4. Brand voice and tone
5. Visual identity elements (colors, style)
6. Competitor landscape
7. Mission and values

Output JSON only:
{
  "confidence": 0.0-1.0,
  "is_complete": true/false,
  "missing_aspects": ["aspect1", "aspect2"],
  "suggested_queries": ["query for aspect1", "query for aspect2"]
}

Confidence thresholds:
- 0.8+: Complete, can proceed
- 0.5-0.8: Partial, gap-fill recommended
- <0.5: Incomplete, needs more research

Be strict. Missing visual identity or brand voice should significantly lower confidence."""


def _build_evaluation_prompt(bundle: BrandResearchBundle) -> str:
    """Build evaluation prompt from research bundle."""
    parts = [f"Brand: {bundle.brand_name}", f"Website: {bundle.website_url}", ""]
    if bundle.deep_research_summary:
        parts.append("## Deep Research Summary")
        parts.append(bundle.deep_research_summary[:8000])  # Truncate if too long
        parts.append("")
    if bundle.website_assets:
        wa = bundle.website_assets
        parts.append("## Website Scraping Results")
        if wa.meta_description:
            parts.append(f"Description: {wa.meta_description}")
        if wa.og_description:
            parts.append(f"OG Description: {wa.og_description}")
        if wa.headlines:
            parts.append(f"Headlines: {', '.join(wa.headlines[:10])}")
        if wa.colors:
            parts.append(f"Colors: {', '.join(wa.colors[:10])}")
        parts.append("")
    if bundle.gap_fill_results:
        parts.append("## Gap Fill Results")
        for r in bundle.gap_fill_results[:3]:
            parts.append(r[:2000])  # Truncate each result
        parts.append("")
    return "\n".join(parts)


def _parse_evaluation_response(text: str) -> ResearchCompleteness:
    """Parse LLM response into ResearchCompleteness model."""
    # Try to extract JSON from response
    text = text.strip()
    # Handle markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                break
            if in_block:
                json_lines.append(line)
        text = "\n".join(json_lines)
    try:
        data = json.loads(text)
        return ResearchCompleteness(
            confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
            is_complete=bool(data.get("is_complete", False)),
            missing_aspects=list(data.get("missing_aspects", [])),
            suggested_queries=list(data.get("suggested_queries", [])),
        )
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        log.warning("Failed to parse evaluation response: %s", e)
        # Return low confidence if parsing fails
        return ResearchCompleteness(
            confidence=0.3,
            is_complete=False,
            missing_aspects=["parsing_failed"],
            suggested_queries=[f"{text[:50]}... (parse error)"],
        )


class ResearchEvaluator:
    """Evaluates research completeness using Gemini Flash."""

    def __init__(self):
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Lazily create Gemini client."""
        if self._client is None:
            from sip_studio.config.settings import get_settings

            settings = get_settings()
            if not settings.gemini_api_key:
                raise EvaluationError("GEMINI_API_KEY not configured", "API_KEY_MISSING")
            self._client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)
        return self._client

    async def evaluate(self, bundle: BrandResearchBundle) -> ResearchCompleteness:
        """Evaluate research completeness for brand creation.
        Args:
            bundle: Research bundle with deep research and website assets
        Returns:
            ResearchCompleteness with confidence score and gap identification
        Raises:
            EvaluationError: On API or parsing failure
        """
        # Handle empty research
        if not bundle.deep_research_summary and not bundle.website_assets:
            return ResearchCompleteness(
                confidence=0.0,
                is_complete=False,
                missing_aspects=REQUIRED_ASPECTS.copy(),
                suggested_queries=[
                    f"{bundle.brand_name} company history founding",
                    f"{bundle.brand_name} products services",
                    f"{bundle.brand_name} brand identity visual style",
                ],
            )
        client = self._get_client()
        prompt = _build_evaluation_prompt(bundle)
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=EVALUATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=EVALUATION_SYSTEM_PROMPT,
                    temperature=0.1,  # Low temp for consistent structured output
                ),
            )
            text = response.text or ""
            if not text:
                log.warning("Empty evaluation response")
                return ResearchCompleteness(
                    confidence=0.4,
                    is_complete=False,
                    missing_aspects=["evaluation_failed"],
                    suggested_queries=[f"{bundle.brand_name} brand identity"],
                )
            return _parse_evaluation_response(text)
        except genai_errors.ClientError as e:
            log.exception("Gemini client error in evaluation: %s", e)
            raise EvaluationError(f"Evaluation failed: {e}", "EVALUATION_API_ERROR") from e
        except genai_errors.ServerError as e:
            log.exception("Gemini server error in evaluation: %s", e)
            raise EvaluationError(
                f"Evaluation service unavailable: {e}", "EVALUATION_API_ERROR"
            ) from e
        except Exception as e:
            log.exception("Evaluation failed: %s", e)
            raise EvaluationError(f"Unexpected error: {e}") from e


class EvaluationError(Exception):
    """Error during research evaluation."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


async def evaluate_research(bundle: BrandResearchBundle) -> ResearchCompleteness:
    """Evaluate research completeness - convenience function.
    Args:
        bundle: Research bundle to evaluate
    Returns:
        ResearchCompleteness with confidence and gaps
    """
    evaluator = ResearchEvaluator()
    return await evaluator.evaluate(bundle)
