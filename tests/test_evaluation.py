"""Tests for research evaluation module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sip_studio.brands.research.evaluation import (
    REQUIRED_ASPECTS,
    EvaluationError,
    ResearchEvaluator,
    _build_evaluation_prompt,
    _parse_evaluation_response,
    evaluate_research,
)
from sip_studio.brands.research.models import BrandResearchBundle, WebsiteAssets


# Helper to build mock JSON responses
def _mk_eval(conf: float, complete: bool, missing: list, queries: list) -> str:
    import json

    return json.dumps(
        {
            "confidence": conf,
            "is_complete": complete,
            "missing_aspects": missing,
            "suggested_queries": queries,
        }
    )


class TestBuildEvaluationPrompt:
    def test_includes_brand_name(self):
        b = BrandResearchBundle(brand_name="TestBrand", website_url="https://test.com")
        assert "TestBrand" in _build_evaluation_prompt(b)

    def test_includes_website_url(self):
        b = BrandResearchBundle(brand_name="Test", website_url="https://example.com")
        assert "https://example.com" in _build_evaluation_prompt(b)

    def test_includes_deep_research_summary(self):
        b = BrandResearchBundle(
            brand_name="Test",
            website_url="https://test.com",
            deep_research_summary="This is a test summary about the brand.",
        )
        p = _build_evaluation_prompt(b)
        assert "Deep Research Summary" in p
        assert "test summary about the brand" in p

    def test_truncates_long_summary(self):
        b = BrandResearchBundle(
            brand_name="Test", website_url="https://test.com", deep_research_summary="x" * 10000
        )
        assert len(_build_evaluation_prompt(b)) < 10000

    def test_includes_website_assets(self):
        a = WebsiteAssets(
            meta_description="Test description",
            og_description="OG description",
            headlines=["Headline 1", "Headline 2"],
            colors=["#ff0000", "#00ff00"],
        )
        b = BrandResearchBundle(brand_name="Test", website_url="https://test.com", website_assets=a)
        p = _build_evaluation_prompt(b)
        assert "Website Scraping Results" in p and "Test description" in p
        assert "Headline 1" in p and "#ff0000" in p

    def test_includes_gap_fill_results(self):
        b = BrandResearchBundle(
            brand_name="Test",
            website_url="https://test.com",
            gap_fill_results=["Result 1", "Result 2"],
        )
        p = _build_evaluation_prompt(b)
        assert "Gap Fill Results" in p and "Result 1" in p


class TestParseEvaluationResponse:
    def test_parses_valid_json(self):
        r = _parse_evaluation_response(_mk_eval(0.85, True, [], []))
        assert r.confidence == 0.85 and r.is_complete is True and r.missing_aspects == []

    def test_parses_json_with_code_block(self):
        resp = "```json\n" + _mk_eval(0.7, False, ["visual_identity"], ["brand colors"]) + "\n```"
        r = _parse_evaluation_response(resp)
        assert r.confidence == 0.7 and r.is_complete is False
        assert "visual_identity" in r.missing_aspects

    def test_clamps_confidence_to_valid_range(self):
        r1 = _parse_evaluation_response(_mk_eval(1.5, True, [], []))
        assert r1.confidence == 1.0
        r2 = _parse_evaluation_response(_mk_eval(-0.5, False, [], []))
        assert r2.confidence == 0.0

    def test_handles_malformed_json(self):
        r = _parse_evaluation_response("This is not JSON at all")
        assert r.confidence == 0.3 and r.is_complete is False
        assert "parsing_failed" in r.missing_aspects

    def test_handles_partial_json(self):
        r = _parse_evaluation_response('{"confidence": 0.5}')
        assert r.confidence == 0.5 and r.is_complete is False


class TestResearchEvaluator:
    @pytest.fixture
    def evaluator(self):
        with patch("sip_studio.brands.research.evaluation.genai.Client"):
            yield ResearchEvaluator()

    def test_get_client_missing_api_key(self):
        with patch("sip_studio.config.settings.get_settings") as ms:
            ms.return_value.gemini_api_key = ""
            with pytest.raises(EvaluationError) as exc:
                ResearchEvaluator()._get_client()
            assert exc.value.error_code == "API_KEY_MISSING"

    def test_get_client_creates_client(self):
        with (
            patch("sip_studio.config.settings.get_settings") as ms,
            patch("sip_studio.brands.research.evaluation.genai.Client") as mc,
        ):
            ms.return_value.gemini_api_key = "test-key"
            ResearchEvaluator()._get_client()
            mc.assert_called_once_with(api_key="test-key", vertexai=False)

    def test_get_client_caches(self):
        with (
            patch("sip_studio.config.settings.get_settings") as ms,
            patch("sip_studio.brands.research.evaluation.genai.Client") as mc,
        ):
            ms.return_value.gemini_api_key = "test-key"
            e = ResearchEvaluator()
            c1, c2 = e._get_client(), e._get_client()
            assert c1 is c2
            mc.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_empty_research_returns_low_confidence(self):
        with patch("sip_studio.config.settings.get_settings") as ms:
            ms.return_value.gemini_api_key = "test-key"
            b = BrandResearchBundle(brand_name="Test", website_url="https://test.com")
            r = await ResearchEvaluator().evaluate(b)
            assert r.confidence == 0.0 and r.is_complete is False
            assert len(r.missing_aspects) == len(REQUIRED_ASPECTS)
            assert len(r.suggested_queries) >= 1

    @pytest.mark.asyncio
    async def test_evaluate_success(self):
        with (
            patch("sip_studio.config.settings.get_settings") as ms,
            patch("sip_studio.brands.research.evaluation.genai.Client") as mcc,
        ):
            ms.return_value.gemini_api_key = "test-key"
            mc = MagicMock()
            mr = MagicMock()
            mr.text = _mk_eval(0.9, True, [], [])
            mc.models.generate_content.return_value = mr
            mcc.return_value = mc
            b = BrandResearchBundle(
                brand_name="TestBrand",
                website_url="https://test.com",
                deep_research_summary="Comprehensive brand research...",
            )
            r = await ResearchEvaluator().evaluate(b)
            assert r.confidence == 0.9 and r.is_complete is True

    @pytest.mark.asyncio
    async def test_evaluate_with_gaps(self):
        with (
            patch("sip_studio.config.settings.get_settings") as ms,
            patch("sip_studio.brands.research.evaluation.genai.Client") as mcc,
        ):
            ms.return_value.gemini_api_key = "test-key"
            mc = MagicMock()
            mr = MagicMock()
            mr.text = _mk_eval(
                0.6,
                False,
                ["visual_identity", "competitors"],
                ["brand colors", "competitors in market"],
            )
            mc.models.generate_content.return_value = mr
            mcc.return_value = mc
            b = BrandResearchBundle(
                brand_name="TestBrand",
                website_url="https://test.com",
                deep_research_summary="Partial brand research...",
            )
            r = await ResearchEvaluator().evaluate(b)
            assert r.confidence == 0.6 and r.is_complete is False
            assert "visual_identity" in r.missing_aspects
            assert len(r.suggested_queries) == 2

    @pytest.mark.asyncio
    async def test_evaluate_empty_response_fallback(self):
        with (
            patch("sip_studio.config.settings.get_settings") as ms,
            patch("sip_studio.brands.research.evaluation.genai.Client") as mcc,
        ):
            ms.return_value.gemini_api_key = "test-key"
            mc = MagicMock()
            mr = MagicMock()
            mr.text = ""
            mc.models.generate_content.return_value = mr
            mcc.return_value = mc
            b = BrandResearchBundle(
                brand_name="Test",
                website_url="https://test.com",
                deep_research_summary="Some research",
            )
            r = await ResearchEvaluator().evaluate(b)
            assert r.confidence == 0.4 and r.is_complete is False

    @pytest.mark.asyncio
    async def test_evaluate_api_error(self):
        from google.genai import errors as ge

        with (
            patch("sip_studio.config.settings.get_settings") as ms,
            patch("sip_studio.brands.research.evaluation.genai.Client") as mcc,
        ):
            ms.return_value.gemini_api_key = "test-key"
            mc = MagicMock()
            ej = {"error": {"message": "API error", "status": "ERROR"}}
            mc.models.generate_content.side_effect = ge.ClientError(400, ej)
            mcc.return_value = mc
            b = BrandResearchBundle(
                brand_name="Test", website_url="https://test.com", deep_research_summary="Research"
            )
            with pytest.raises(EvaluationError) as exc:
                await ResearchEvaluator().evaluate(b)
            assert exc.value.error_code == "EVALUATION_API_ERROR"


class TestEvaluationError:
    def test_with_error_code(self):
        e = EvaluationError("API key missing", "API_KEY_MISSING")
        assert str(e) == "API key missing" and e.error_code == "API_KEY_MISSING"

    def test_without_error_code(self):
        e = EvaluationError("Generic error")
        assert str(e) == "Generic error" and e.error_code is None


class TestEvaluateResearchConvenience:
    @pytest.mark.asyncio
    async def test_evaluate_research_function(self):
        with (
            patch("sip_studio.config.settings.get_settings") as ms,
            patch("sip_studio.brands.research.evaluation.genai.Client") as mcc,
        ):
            ms.return_value.gemini_api_key = "test-key"
            mc = MagicMock()
            mr = MagicMock()
            mr.text = _mk_eval(0.8, True, [], [])
            mc.models.generate_content.return_value = mr
            mcc.return_value = mc
            b = BrandResearchBundle(
                brand_name="Test",
                website_url="https://test.com",
                deep_research_summary="Complete research",
            )
            r = await evaluate_research(b)
            assert r.confidence == 0.8 and r.is_complete is True
