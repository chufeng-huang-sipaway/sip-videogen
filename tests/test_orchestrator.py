"""Tests for brand creation orchestrator."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sip_studio.brands.research.models import (
    BrandResearchBundle,
    ResearchCompleteness,
    WebsiteAssets,
)
from sip_studio.brands.research.orchestrator import (
    BrandCreationOrchestrator,
    OrchestrationError,
    _generate_unique_slug,
    _truncate_concept,
    start_brand_creation_job,
)


class TestGenerateUniqueSlug:
    def test_simple_name(self):
        with (
            patch("sip_studio.brands.research.orchestrator.list_brands") as m_lb,
            patch("sip_studio.brands.research.orchestrator.get_brand_dir") as m_gbd,
        ):
            m_lb.return_value = []
            m_gbd.return_value = MagicMock(exists=lambda: False)
            slug = _generate_unique_slug("Acme Corp")
            assert slug == "acme-corp"

    def test_collision_appends_number(self):
        with (
            patch("sip_studio.brands.research.orchestrator.list_brands") as m_lb,
            patch("sip_studio.brands.research.orchestrator.get_brand_dir") as m_gbd,
        ):
            entry = MagicMock()
            entry.slug = "acme-corp"
            m_lb.return_value = [entry]
            m_gbd.return_value = MagicMock(exists=lambda: False)
            slug = _generate_unique_slug("Acme Corp")
            assert slug == "acme-corp-2"

    def test_multiple_collisions(self):
        with (
            patch("sip_studio.brands.research.orchestrator.list_brands") as m_lb,
            patch("sip_studio.brands.research.orchestrator.get_brand_dir") as m_gbd,
        ):
            e1 = MagicMock()
            e1.slug = "acme-corp"
            e2 = MagicMock()
            e2.slug = "acme-corp-2"
            e3 = MagicMock()
            e3.slug = "acme-corp-3"
            m_lb.return_value = [e1, e2, e3]
            m_gbd.return_value = MagicMock(exists=lambda: False)
            slug = _generate_unique_slug("Acme Corp")
            assert slug == "acme-corp-4"

    def test_empty_name_fallback(self):
        with (
            patch("sip_studio.brands.research.orchestrator.list_brands") as m_lb,
            patch("sip_studio.brands.research.orchestrator.get_brand_dir") as m_gbd,
        ):
            m_lb.return_value = []
            m_gbd.return_value = MagicMock(exists=lambda: False)
            slug = _generate_unique_slug("   ")
            assert slug == "brand"


class TestTruncateConcept:
    def test_basic_bundle(self):
        bundle = BrandResearchBundle(
            brand_name="Test Brand",
            website_url="https://test.com",
            deep_research_summary="This is a test summary.",
        )
        concept = _truncate_concept(bundle)
        assert "Test Brand" in concept
        assert "https://test.com" in concept
        assert "test summary" in concept

    def test_with_website_assets(self):
        bundle = BrandResearchBundle(
            brand_name="Test",
            website_url="https://test.com",
            deep_research_summary="Summary",
            website_assets=WebsiteAssets(
                colors=["#FF0000", "#00FF00"],
                meta_description="Test description",
                headlines=["Welcome", "About Us"],
            ),
        )
        concept = _truncate_concept(bundle)
        assert "#FF0000" in concept
        assert "Test description" in concept
        assert "Welcome" in concept

    def test_truncation_long_content(self):
        bundle = BrandResearchBundle(
            brand_name="Test", website_url="https://test.com", deep_research_summary="A" * 10000
        )
        concept = _truncate_concept(bundle)
        assert len(concept) <= 4800
        assert "[...truncated]" in concept

    def test_gap_fill_results(self):
        bundle = BrandResearchBundle(
            brand_name="Test",
            website_url="https://test.com",
            gap_fill_results=["Gap fill result 1", "Gap fill result 2"],
        )
        concept = _truncate_concept(bundle)
        assert "Gap fill result 1" in concept


class TestBrandCreationOrchestrator:
    @pytest.mark.asyncio
    async def test_cancelled_during_research(self):
        orchestrator = BrandCreationOrchestrator("Test", "https://test.com", "test-job-id")
        orchestrator.slug = "test"

        # Mock _run_deep_research to check cancellation and raise
        async def mock_research():
            if orchestrator._is_cancelled():
                raise asyncio.CancelledError("Cancelled")
            return ("summary", [])

        with (
            patch.object(orchestrator, "_is_cancelled", return_value=True),
            patch.object(orchestrator, "_update_progress"),
            patch.object(orchestrator, "_run_deep_research", side_effect=mock_research),
            patch.object(orchestrator, "_run_website_scrape", return_value=None),
        ):
            with pytest.raises(asyncio.CancelledError):
                await orchestrator.run()

    @pytest.mark.asyncio
    async def test_research_error_propagated(self):
        from sip_studio.brands.research.deep_research import BrandResearchError

        orchestrator = BrandCreationOrchestrator("Test", "https://test.com", "test-job-id")
        orchestrator.slug = "test"
        with (
            patch.object(orchestrator, "_is_cancelled", return_value=False),
            patch.object(orchestrator, "_update_progress"),
            patch.object(
                orchestrator,
                "_run_deep_research",
                side_effect=BrandResearchError("API error", "API_KEY_MISSING"),
            ),
            patch.object(orchestrator, "_run_website_scrape", return_value=None),
        ):
            with pytest.raises(OrchestrationError) as exc_info:
                await orchestrator.run()
            assert exc_info.value.error_code == "API_KEY_MISSING"

    @pytest.mark.asyncio
    async def test_ssrf_error_propagated(self):
        from sip_studio.brands.research.website_scraper import SSRFError

        orchestrator = BrandCreationOrchestrator("Test", "https://test.com", "test-job-id")
        orchestrator.slug = "test"
        with (
            patch.object(orchestrator, "_is_cancelled", return_value=False),
            patch.object(orchestrator, "_update_progress"),
            patch.object(orchestrator, "_run_deep_research", return_value=("summary", [])),
            patch.object(orchestrator, "_run_website_scrape", side_effect=SSRFError("Blocked")),
        ):
            with pytest.raises(OrchestrationError) as exc_info:
                await orchestrator.run()
            assert exc_info.value.error_code == "SSRF_BLOCKED"

    @pytest.mark.asyncio
    async def test_scrape_failure_continues(self):
        orchestrator = BrandCreationOrchestrator("Test", "https://test.com", "test-job-id")
        orchestrator.slug = "test"
        mock_identity = MagicMock()
        mock_identity.slug = "test"
        mock_evaluation = ResearchCompleteness(
            confidence=0.9, is_complete=True, missing_aspects=[], suggested_queries=[]
        )
        with (
            patch.object(orchestrator, "_is_cancelled", return_value=False),
            patch.object(orchestrator, "_update_progress"),
            patch.object(
                orchestrator, "_run_deep_research", return_value=("Summary", ["https://source.com"])
            ),
            patch.object(
                orchestrator, "_run_website_scrape", side_effect=Exception("Network error")
            ),
            patch(
                "sip_studio.brands.research.orchestrator.evaluate_research",
                return_value=mock_evaluation,
            ),
            patch.object(orchestrator, "_create_brand_identity", return_value=mock_identity),
            patch("sip_studio.brands.research.orchestrator.storage_create_brand"),
        ):
            result = await orchestrator.run()
            assert result == "test"

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self):
        orchestrator = BrandCreationOrchestrator("Test Brand", "https://test.com", "test-job-id")
        orchestrator.slug = "test-brand"
        mock_assets = WebsiteAssets(colors=["#FF0000"])
        mock_identity = MagicMock()
        mock_identity.slug = "test-brand"
        mock_evaluation = ResearchCompleteness(
            confidence=0.95, is_complete=True, missing_aspects=[], suggested_queries=[]
        )
        with (
            patch.object(orchestrator, "_is_cancelled", return_value=False),
            patch.object(orchestrator, "_update_progress"),
            patch.object(
                orchestrator,
                "_run_deep_research",
                return_value=("Research summary", ["https://source.com"]),
            ),
            patch.object(orchestrator, "_run_website_scrape", return_value=mock_assets),
            patch(
                "sip_studio.brands.research.orchestrator.evaluate_research",
                return_value=mock_evaluation,
            ),
            patch.object(orchestrator, "_create_brand_identity", return_value=mock_identity),
            patch("sip_studio.brands.research.orchestrator.storage_create_brand"),
        ):
            result = await orchestrator.run()
            assert result == "test-brand"


class TestStartBrandCreationJob:
    def test_creates_job_and_returns(self):
        with (
            patch(
                "sip_studio.brands.research.orchestrator._generate_unique_slug",
                return_value="test-brand",
            ),
            patch("sip_studio.brands.research.orchestrator.create_job") as m_cj,
            patch("threading.Thread") as m_thread,
        ):
            mock_job = MagicMock()
            mock_job.job_id = "test-job-id"
            mock_job.slug = "test-brand"
            m_cj.return_value = mock_job
            result = start_brand_creation_job("Test Brand", "https://test.com")
            assert result is not None
            assert result.slug == "test-brand"
            m_thread.assert_called_once()
            m_thread.return_value.start.assert_called_once()

    def test_returns_none_if_job_running(self):
        with (
            patch(
                "sip_studio.brands.research.orchestrator._generate_unique_slug", return_value="test"
            ),
            patch("sip_studio.brands.research.orchestrator.create_job", return_value=None),
        ):
            result = start_brand_creation_job("Test", "https://test.com")
            assert result is None


class TestOrchestratorGapFilling:
    @pytest.mark.asyncio
    async def test_gap_fill_called_when_incomplete(self):
        orchestrator = BrandCreationOrchestrator("Test", "https://test.com", "job-id")
        orchestrator.slug = "test"
        orchestrator._research_wrapper = MagicMock()
        orchestrator._research_wrapper.gap_fill_search = AsyncMock(return_value=["Gap result"])
        bundle = BrandResearchBundle(
            brand_name="Test", website_url="https://test.com", deep_research_summary="Short summary"
        )
        # First evaluation: incomplete, second: complete
        call_count = [0]

        async def mock_evaluate(b):
            call_count[0] += 1
            if call_count[0] == 1:
                return ResearchCompleteness(
                    confidence=0.5,
                    is_complete=False,
                    missing_aspects=["visual_identity"],
                    suggested_queries=["test visual query"],
                )
            return ResearchCompleteness(
                confidence=0.9, is_complete=True, missing_aspects=[], suggested_queries=[]
            )

        with (
            patch.object(orchestrator, "_is_cancelled", return_value=False),
            patch.object(orchestrator, "_update_progress"),
            patch(
                "sip_studio.brands.research.orchestrator.evaluate_research",
                side_effect=mock_evaluate,
            ),
        ):
            result = await orchestrator._run_evaluation_and_gap_fill(bundle)
            assert len(result.gap_fill_results) == 1
            assert result.gap_fill_results[0] == "Gap result"
            orchestrator._research_wrapper.gap_fill_search.assert_called_once()
