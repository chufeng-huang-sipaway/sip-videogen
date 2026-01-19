"""Research orchestrator for brand creation from website URL.
Main orchestration logic: parallel deep research + scraping, evaluation, gap-filling, brand director call.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Callable

from sip_studio.agents.brand_director import develop_brand_with_output
from sip_studio.brands.storage import create_brand as storage_create_brand
from sip_studio.brands.storage import list_brands
from sip_studio.brands.storage.base import get_brand_dir, slugify

from .deep_research import BrandResearchError, BrandResearchWrapper
from .evaluation import EvaluationError, evaluate_research
from .job_storage import (
    cancel_job,
    complete_job,
    create_job,
    fail_job,
    is_cancellation_requested,
    update_job_progress,
)
from .models import BrandCreationJob, BrandResearchBundle, WebsiteAssets
from .website_scraper import MaxRetriesError, SSRFError, scrape_website

log = logging.getLogger(__name__)
MAX_GAP_FILL_ROUNDS = 3
MAX_CONCEPT_CHARS = 4800
CONFIDENCE_THRESHOLD = 0.8


class OrchestrationError(Exception):
    """Error during brand creation orchestration."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


def _generate_unique_slug(brand_name: str) -> str:
    """Generate unique slug from brand name, appending -2, -3 on collision."""
    base_slug = slugify(brand_name)
    if not base_slug:
        base_slug = "brand"
    existing = {e.slug for e in list_brands()}
    if base_slug not in existing and not get_brand_dir(base_slug).exists():
        return base_slug
    for i in range(2, 100):
        candidate = f"{base_slug}-{i}"
        if candidate not in existing and not get_brand_dir(candidate).exists():
            return candidate
    # Fallback to UUID suffix
    return f"{base_slug}-{uuid.uuid4().hex[:8]}"


def _truncate_concept(bundle: BrandResearchBundle) -> str:
    """Build concept string from research bundle with priority-based truncation.
    Priority: brand description > visual identity > competitors > other.
    """
    parts = [f"# Brand: {bundle.brand_name}", f"Website: {bundle.website_url}", ""]
    # Deep research summary (highest priority content)
    if bundle.deep_research_summary:
        parts.append("## Research Summary")
        parts.append(bundle.deep_research_summary)
        parts.append("")
    # Website assets (visual identity signals)
    if bundle.website_assets:
        wa = bundle.website_assets
        parts.append("## Website Analysis")
        if wa.meta_description:
            parts.append(f"Description: {wa.meta_description}")
        if wa.og_description and wa.og_description != wa.meta_description:
            parts.append(f"OG Description: {wa.og_description}")
        if wa.headlines:
            parts.append(f"Key Headlines: {', '.join(wa.headlines[:5])}")
        if wa.colors:
            parts.append(f"Brand Colors: {', '.join(wa.colors[:8])}")
        if wa.theme_color:
            parts.append(f"Theme Color: {wa.theme_color}")
        parts.append("")
    # Gap-fill results (lower priority)
    if bundle.gap_fill_results:
        parts.append("## Additional Research")
        for r in bundle.gap_fill_results[:2]:
            parts.append(r[:1000])
        parts.append("")
    # Sources (reference only)
    if bundle.deep_research_sources:
        parts.append(f"Sources: {', '.join(bundle.deep_research_sources[:5])}")
    concept = "\n".join(parts)
    # Truncate if needed
    if len(concept) > MAX_CONCEPT_CHARS:
        log.warning(
            "Concept length %d exceeds limit %d, truncating", len(concept), MAX_CONCEPT_CHARS
        )
        concept = concept[: MAX_CONCEPT_CHARS - 50] + "\n\n[...truncated]"
    return concept


class BrandCreationOrchestrator:
    """Orchestrates brand creation from website URL."""

    def __init__(self, brand_name: str, website_url: str, job_id: str | None = None):
        self.brand_name = brand_name
        self.website_url = website_url
        self.job_id = job_id or uuid.uuid4().hex
        self.slug: str | None = None
        self._research_wrapper: BrandResearchWrapper | None = None

    def _is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return is_cancellation_requested(self.job_id)

    def _update_progress(self, phase: str, phase_detail: str | None, percent: int) -> None:
        """Update job progress."""
        update_job_progress(
            self.job_id,
            status="running",
            phase=phase,
            phase_detail=phase_detail,
            percent_complete=percent,
        )

    async def _run_deep_research(self) -> tuple[str, list[str]]:
        """Run deep research with cancellation checks."""
        if self._research_wrapper is None:
            self._research_wrapper = BrandResearchWrapper()
        # Trigger research
        interaction_id = await self._research_wrapper.trigger_deep_research(
            self.brand_name, self.website_url
        )

        # Poll with cancellation callback
        def progress_cb(msg: str) -> None:
            if not self._is_cancelled():
                self._update_progress("researching", msg, 30)

        return await self._research_wrapper.poll_deep_research_with_cancellation(
            interaction_id, self._is_cancelled, progress_cb
        )

    async def _run_website_scrape(self):
        """Scrape website with error handling."""
        try:
            return await scrape_website(self.website_url)
        except SSRFError:
            raise  # Re-raise SSRF errors (security critical)
        except MaxRetriesError as e:
            log.warning("Website scrape failed after retries: %s", e)
            return None  # Non-fatal: proceed with deep research only
        except Exception as e:
            log.warning("Website scrape error: %s", e)
            return None  # Non-fatal

    async def _run_evaluation_and_gap_fill(
        self, bundle: BrandResearchBundle
    ) -> BrandResearchBundle:
        """Evaluate research completeness and gap-fill if needed."""
        if self._research_wrapper is None:
            self._research_wrapper = BrandResearchWrapper()
        for round_num in range(MAX_GAP_FILL_ROUNDS + 1):
            if self._is_cancelled():
                raise asyncio.CancelledError("Cancelled during evaluation")
            self._update_progress(
                "researching", f"Evaluating research (round {round_num + 1})", 50 + round_num * 10
            )
            try:
                completeness = await evaluate_research(bundle)
                bundle.completeness = completeness
            except EvaluationError as e:
                log.warning("Evaluation failed: %s", e)
                break  # Proceed without evaluation
            if completeness.is_complete or completeness.confidence >= CONFIDENCE_THRESHOLD:
                log.info("Research complete (confidence=%.2f)", completeness.confidence)
                break
            if round_num >= MAX_GAP_FILL_ROUNDS:
                log.warning("Max gap-fill rounds reached, proceeding with incomplete research")
                break
            # Gap-fill with suggested queries
            if completeness.suggested_queries:
                self._update_progress(
                    "researching", "Gap-filling missing information", 55 + round_num * 10
                )
                gap_results = await self._research_wrapper.gap_fill_search(
                    completeness.suggested_queries
                )
                bundle.gap_fill_results.extend(gap_results)
        return bundle

    async def _create_brand_identity(self, bundle: BrandResearchBundle):
        """Call brand director to create identity."""
        if self._is_cancelled():
            raise asyncio.CancelledError("Cancelled before brand creation")
        self._update_progress("creating", "Creating brand identity with AI agents", 70)
        concept = _truncate_concept(bundle)
        log.info("Concept length: %d chars", len(concept))
        # Run brand director
        output = await asyncio.to_thread(lambda: asyncio.run(develop_brand_with_output(concept)))
        return output.brand_identity

    async def run(self) -> str:
        """Execute full orchestration pipeline.
        Returns:
            Brand slug on success.
        Raises:
            OrchestrationError: On failure with error_code.
            asyncio.CancelledError: If cancelled.
        """
        # Phase 1: Initialize
        self._update_progress("researching", "Starting research", 5)
        # Phase 2: Parallel research + scrape
        try:
            research_task = asyncio.create_task(self._run_deep_research())
            scrape_task = asyncio.create_task(self._run_website_scrape())
            # Gather with exception handling
            results = await asyncio.gather(research_task, scrape_task, return_exceptions=True)
            # Process results
            research_result = results[0]
            scrape_result = results[1]
            # Handle research errors
            if isinstance(research_result, BaseException):
                if isinstance(research_result, asyncio.CancelledError):
                    raise research_result
                if isinstance(research_result, BrandResearchError):
                    raise OrchestrationError(str(research_result), research_result.error_code)
                raise OrchestrationError(f"Research failed: {research_result}")
            summary = research_result[0]
            sources = research_result[1]
            # Handle scrape errors
            website_assets: WebsiteAssets | None = None
            if isinstance(scrape_result, BaseException):
                if isinstance(scrape_result, SSRFError):
                    raise OrchestrationError(f"SSRF blocked: {scrape_result}", "SSRF_BLOCKED")
                log.warning("Scrape failed, continuing with research only: %s", scrape_result)
            else:
                website_assets = scrape_result
        except asyncio.CancelledError:
            raise
        except OrchestrationError:
            raise
        except Exception as e:
            log.exception("Research phase failed: %s", e)
            raise OrchestrationError(f"Research failed: {e}")
        # Check cancellation
        if self._is_cancelled():
            raise asyncio.CancelledError("Cancelled after research")
        # Build research bundle
        bundle = BrandResearchBundle(
            brand_name=self.brand_name,
            website_url=self.website_url,
            deep_research_summary=summary,
            deep_research_sources=sources,
            website_assets=website_assets,
        )
        # Phase 3: Evaluation and gap-filling
        try:
            bundle = await self._run_evaluation_and_gap_fill(bundle)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("Evaluation/gap-fill failed, proceeding: %s", e)
        # Check cancellation
        if self._is_cancelled():
            raise asyncio.CancelledError("Cancelled after evaluation")
        # Phase 4: Create brand identity
        try:
            identity = await self._create_brand_identity(bundle)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("Brand creation failed: %s", e)
            raise OrchestrationError(f"Brand creation failed: {e}", "BRAND_DIRECTOR_ERROR")
        # Phase 5: Save brand
        if self._is_cancelled():
            raise asyncio.CancelledError("Cancelled before save")
        self._update_progress("finalizing", "Saving brand", 90)
        slug = self.slug
        if not slug:
            raise OrchestrationError("Slug not set", "INTERNAL_ERROR")
        try:
            # Ensure slug matches our generated slug
            identity.slug = slug
            storage_create_brand(identity)
            log.info("Brand saved: %s", slug)
        except Exception as e:
            log.exception("Failed to save brand: %s", e)
            raise OrchestrationError(f"Failed to save brand: {e}", "STORAGE_ERROR")
        return slug


def start_brand_creation_job(brand_name: str, website_url: str) -> BrandCreationJob | None:
    """Start a new brand creation job in background.
    Returns:
        BrandCreationJob if started, None if job already running.
    """
    job_id = uuid.uuid4().hex
    slug = _generate_unique_slug(brand_name)
    job = create_job(brand_name, website_url, slug, job_id)
    if job is None:
        return None  # Job already running
    # Start background thread
    import threading

    def run_orchestration():
        orchestrator = BrandCreationOrchestrator(brand_name, website_url, job_id)
        orchestrator.slug = slug
        try:
            update_job_progress(job_id, status="running", phase="researching")
            result_slug = asyncio.run(orchestrator.run())
            complete_job(job_id)
            log.info("Brand creation job completed: %s", result_slug)
        except asyncio.CancelledError:
            log.info("Brand creation job cancelled: %s", job_id)
            cancel_job(job_id)
        except OrchestrationError as e:
            log.error("Brand creation job failed: %s (code=%s)", e, e.error_code)
            fail_job(job_id, str(e), e.error_code)
        except Exception as e:
            log.exception("Unexpected error in brand creation job: %s", e)
            fail_job(job_id, str(e))

    thread = threading.Thread(target=run_orchestration, daemon=True)
    thread.start()
    return job


async def run_brand_creation_async(
    brand_name: str,
    website_url: str,
    job_id: str,
    slug: str,
    on_progress: Callable[[str, str, int], None] | None = None,
) -> str:
    """Run brand creation pipeline directly (for testing/internal use).
    Args:
        brand_name: Brand name
        website_url: Brand website URL
        job_id: Job ID for cancellation checks
        slug: Pre-generated brand slug
        on_progress: Optional progress callback(phase, detail, percent)
    Returns:
        Brand slug on success.
    """
    orchestrator = BrandCreationOrchestrator(brand_name, website_url, job_id)
    orchestrator.slug = slug
    return await orchestrator.run()
