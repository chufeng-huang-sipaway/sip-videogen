"""Tests for brand deep research integration."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from sip_studio.brands.research.deep_research import (
    BrandResearchError,
    BrandResearchWrapper,
    _build_brand_research_query,
    _extract_deep_research_result,
    _extract_grounding_sources,
    research_brand,
)


class TestBuildBrandResearchQuery:
    def test_contains_brand_name(self):
        q = _build_brand_research_query("Acme Corp", "https://acme.com")
        assert "Acme Corp" in q

    def test_contains_website_url(self):
        q = _build_brand_research_query("Test", "https://test.example.com")
        assert "https://test.example.com" in q

    def test_contains_key_aspects(self):
        q = _build_brand_research_query("Brand", "https://brand.com")
        # Should request brand identity info
        assert "history" in q.lower() or "background" in q.lower()
        assert "visual identity" in q.lower() or "colors" in q.lower()
        assert "target audience" in q.lower() or "positioning" in q.lower()
        assert "voice" in q.lower() or "tone" in q.lower()


class TestExtractGroundingSources:
    def test_empty_response(self):
        response = MagicMock()
        response.text = ""
        response.candidates = []
        text, sources = _extract_grounding_sources(response)
        assert text == ""
        assert sources == []

    def test_text_only(self):
        response = MagicMock()
        response.text = "Research results"
        response.candidates = []
        text, sources = _extract_grounding_sources(response)
        assert text == "Research results"
        assert sources == []

    def test_with_sources(self):
        response = MagicMock()
        response.text = "Results with sources"
        web1 = MagicMock()
        web1.uri = "https://source1.com"
        web1.title = "Source 1"
        web2 = MagicMock()
        web2.uri = "https://source2.com"
        web2.title = "Source 2"
        chunk1 = MagicMock()
        chunk1.web = web1
        chunk2 = MagicMock()
        chunk2.web = web2
        gm = MagicMock()
        gm.grounding_chunks = [chunk1, chunk2]
        cand = MagicMock()
        cand.grounding_metadata = gm
        response.candidates = [cand]
        text, sources = _extract_grounding_sources(response)
        assert text == "Results with sources"
        assert len(sources) == 2
        assert sources[0].url == "https://source1.com"
        assert sources[1].title == "Source 2"


class TestExtractDeepResearchResult:
    def test_empty_interaction(self):
        interaction = MagicMock()
        interaction.outputs = []
        text, sources = _extract_deep_research_result(interaction)
        assert text == ""
        assert sources == []

    def test_with_output(self):
        output = MagicMock()
        output.text = "Deep research summary"
        interaction = MagicMock()
        interaction.outputs = [output]
        interaction.grounding_metadata = None
        text, sources = _extract_deep_research_result(interaction)
        assert text == "Deep research summary"
        assert sources == []

    def test_with_grounding(self):
        output = MagicMock()
        output.text = "Summary"
        web = MagicMock()
        web.uri = "https://source.com"
        web.title = "Source"
        chunk = MagicMock()
        chunk.web = web
        gm = MagicMock()
        gm.grounding_chunks = [chunk]
        interaction = MagicMock()
        interaction.outputs = [output]
        interaction.grounding_metadata = gm
        text, sources = _extract_deep_research_result(interaction)
        assert text == "Summary"
        assert len(sources) == 1
        assert sources[0].url == "https://source.com"


class TestBrandResearchError:
    def test_with_error_code(self):
        e = BrandResearchError("API key missing", "API_KEY_MISSING")
        assert str(e) == "API key missing"
        assert e.error_code == "API_KEY_MISSING"

    def test_without_error_code(self):
        e = BrandResearchError("Generic error")
        assert str(e) == "Generic error"
        assert e.error_code is None


class TestBrandResearchWrapper:
    @pytest.fixture
    def wrapper(self):
        with patch("sip_studio.brands.research.deep_research.genai.Client"):
            w = BrandResearchWrapper()
            yield w

    def test_get_client_missing_api_key(self):
        with patch("sip_studio.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.gemini_api_key = ""
            w = BrandResearchWrapper()
            with pytest.raises(BrandResearchError) as exc_info:
                w._get_client()
            assert exc_info.value.error_code == "API_KEY_MISSING"

    def test_get_client_creates_client(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            w = BrandResearchWrapper()
            w._get_client()
            mock_client.assert_called_once_with(api_key="test-key", vertexai=False)

    def test_get_client_caches(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            w = BrandResearchWrapper()
            c1 = w._get_client()
            c2 = w._get_client()
            assert c1 is c2
            mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_deep_research_success(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client_cls,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            mock_client = MagicMock()
            mock_interaction = MagicMock()
            mock_interaction.id = "interaction-123"
            mock_client.interactions.create.return_value = mock_interaction
            mock_client_cls.return_value = mock_client
            w = BrandResearchWrapper()
            result = await w.trigger_deep_research("Test Brand", "https://test.com")
            assert result == "interaction-123"

    @pytest.mark.asyncio
    async def test_web_search_success(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client_cls,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Search results"
            mock_response.candidates = []
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client
            w = BrandResearchWrapper()
            text, sources = await w.web_search("test query")
            assert text == "Search results"
            assert sources == []

    @pytest.mark.asyncio
    async def test_web_search_no_results(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client_cls,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = ""
            mock_response.candidates = []
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client
            w = BrandResearchWrapper()
            text, sources = await w.web_search("no results query")
            assert text == "No results found."
            assert sources == []

    @pytest.mark.asyncio
    async def test_gap_fill_search(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client_cls,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Result text"
            mock_response.candidates = []
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client
            w = BrandResearchWrapper()
            results = await w.gap_fill_search(["query1", "query2", "query3", "query4"])
            # Should only run max 3 queries
            assert len(results) == 3
            assert "query1" in results[0]
            assert "query2" in results[1]
            assert "query3" in results[2]


class TestPollWithCancellation:
    @pytest.mark.asyncio
    async def test_cancellation_during_poll(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client_cls,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            w = BrandResearchWrapper()

            # Cancel immediately
            def is_cancelled():
                return True

            with pytest.raises(asyncio.CancelledError):
                await w.poll_deep_research_with_cancellation("id-123", is_cancelled)

    @pytest.mark.asyncio
    async def test_completed_research(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client_cls,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            mock_client = MagicMock()
            output = MagicMock()
            output.text = "Research complete"
            interaction = MagicMock()
            interaction.status = "completed"
            interaction.outputs = [output]
            interaction.grounding_metadata = None
            mock_client.interactions.get.return_value = interaction
            mock_client_cls.return_value = mock_client
            w = BrandResearchWrapper()
            text, sources = await w.poll_deep_research_with_cancellation("id-123", lambda: False)
            assert text == "Research complete"
            assert sources == []

    @pytest.mark.asyncio
    async def test_progress_callback(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client_cls,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            mock_client = MagicMock()
            output = MagicMock()
            output.text = "Done"
            interaction = MagicMock()
            interaction.status = "completed"
            interaction.outputs = [output]
            interaction.grounding_metadata = None
            interaction.thinking_summary = "Analyzing brand..."
            mock_client.interactions.get.return_value = interaction
            mock_client_cls.return_value = mock_client
            w = BrandResearchWrapper()
            progress_updates = []

            def on_progress(stage):
                progress_updates.append(stage)

            await w.poll_deep_research_with_cancellation("id-123", lambda: False, on_progress)
            assert len(progress_updates) == 1
            assert "Analyzing" in progress_updates[0]

    @pytest.mark.asyncio
    async def test_failed_research(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client_cls,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            mock_client = MagicMock()
            interaction = MagicMock()
            interaction.status = "failed"
            interaction.error = "API error"
            mock_client.interactions.get.return_value = interaction
            mock_client_cls.return_value = mock_client
            w = BrandResearchWrapper()
            with pytest.raises(BrandResearchError) as exc_info:
                await w.poll_deep_research_with_cancellation("id-123", lambda: False)
            assert "failed" in str(exc_info.value).lower()
            assert exc_info.value.error_code == "RESEARCH_FAILED"


class TestResearchBrand:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        with (
            patch("sip_studio.config.settings.get_settings") as mock_settings,
            patch("sip_studio.brands.research.deep_research.genai.Client") as mock_client_cls,
        ):
            mock_settings.return_value.gemini_api_key = "test-key"
            mock_client = MagicMock()
            # Mock trigger
            trigger_interaction = MagicMock()
            trigger_interaction.id = "int-123"
            mock_client.interactions.create.return_value = trigger_interaction
            # Mock poll completion
            output = MagicMock()
            output.text = "Brand research summary"
            web = MagicMock()
            web.uri = "https://source.com"
            web.title = "Source"
            chunk = MagicMock()
            chunk.web = web
            gm = MagicMock()
            gm.grounding_chunks = [chunk]
            poll_interaction = MagicMock()
            poll_interaction.status = "completed"
            poll_interaction.outputs = [output]
            poll_interaction.grounding_metadata = gm
            mock_client.interactions.get.return_value = poll_interaction
            mock_client_cls.return_value = mock_client
            bundle = await research_brand("TestBrand", "https://test.com", lambda: False)
            assert bundle.brand_name == "TestBrand"
            assert bundle.website_url == "https://test.com"
            assert bundle.deep_research_summary == "Brand research summary"
            assert len(bundle.deep_research_sources) == 1
            assert "source.com" in bundle.deep_research_sources[0]
