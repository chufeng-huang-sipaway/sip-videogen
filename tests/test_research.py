"""Tests for research models and storage."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from sip_studio.research.models import (
    TTL_BY_CATEGORY,
    ClarificationOption,
    ClarificationQuestion,
    ClarificationResponse,
    DeepResearchClarification,
    PendingResearch,
    ResearchEntry,
    ResearchRegistry,
    ResearchResult,
    ResearchSource,
    extract_keywords,
)
from sip_studio.research.storage import ResearchStorage


# extract_keywords tests
class TestExtractKeywords:
    def test_basic(self):
        kw = extract_keywords("How do luxury brands present products?")
        assert "luxury" in kw
        assert "brands" in kw
        assert "products" in kw
        assert "how" not in kw
        assert "do" not in kw

    def test_short_words_filtered(self):
        kw = extract_keywords("AI is big")
        assert "ai" not in kw  # too short (2 chars)
        assert "big" in kw

    def test_stopwords_filtered(self):
        kw = extract_keywords("the best coffee for the morning")
        assert "the" not in kw
        assert "for" not in kw
        assert "best" in kw
        assert "coffee" in kw
        assert "morning" in kw


# Model validation tests
class TestResearchModels:
    def test_research_source_camelcase(self):
        s = ResearchSource(url="https://x.com", title="Title", snippet="Snip")
        d = s.model_dump(by_alias=True)
        assert d["url"] == "https://x.com"
        assert d["title"] == "Title"
        assert d["snippet"] == "Snip"

    def test_research_entry_ttl(self):
        e = ResearchEntry(id="abc", query="test", category="trends", ttl_days=14)
        assert not e.is_expired()
        # Simulate old entry
        e.created_at = datetime.utcnow() - timedelta(days=15)
        assert e.is_expired()

    def test_research_entry_category_ttl_default(self):
        assert TTL_BY_CATEGORY["trends"] == 14
        assert TTL_BY_CATEGORY["brand_analysis"] == 30
        assert TTL_BY_CATEGORY["techniques"] == 90

    def test_pending_research_defaults(self):
        p = PendingResearch(response_id="resp123", query="q", session_id="sess")
        assert p.estimated_minutes == 15
        assert p.brand_slug is None

    def test_research_result_states(self):
        r = ResearchResult(status="in_progress", progress_percent=50)
        assert r.status == "in_progress"
        assert r.progress_percent == 50
        r2 = ResearchResult(status="completed", final_summary="Done", sources=[])
        assert r2.final_summary == "Done"

    def test_clarification_models(self):
        opt = ClarificationOption(value="visual", label="Visual trends", recommended=True)
        q = ClarificationQuestion(
            id="focus", question="What aspect?", options=[opt], allow_custom=True
        )
        c = DeepResearchClarification(
            context_summary="Looking at trends",
            questions=[q],
            estimated_duration="15-20 min",
            query="luxury trends",
        )
        assert c.type == "deep_research_clarification"
        assert len(c.questions) == 1
        assert c.questions[0].allow_custom

    def test_clarification_response(self):
        r = ClarificationResponse(answers={"focus": "visual"}, confirmed=True)
        assert r.confirmed
        assert r.answers["focus"] == "visual"


# Registry matching tests
class TestResearchRegistry:
    def test_find_by_keywords_match(self):
        reg = ResearchRegistry()
        e = ResearchEntry(
            id="e1",
            query="luxury coffee packaging trends",
            keywords=["luxury", "coffee", "packaging", "trends"],
            category="trends",
            ttl_days=14,
        )
        reg.entries.append(e)
        found = reg.find_by_keywords("coffee packaging design")
        assert found is not None
        assert found.id == "e1"

    def test_find_by_keywords_no_match(self):
        reg = ResearchRegistry()
        e = ResearchEntry(
            id="e1",
            query="luxury coffee packaging",
            keywords=["luxury", "coffee", "packaging"],
            category="trends",
            ttl_days=14,
        )
        reg.entries.append(e)
        found = reg.find_by_keywords("minimal tech branding")
        assert found is None

    def test_find_respects_brand_slug(self):
        reg = ResearchRegistry()
        e = ResearchEntry(
            id="e1",
            query="coffee trends",
            keywords=["coffee", "trends"],
            category="trends",
            brand_slug="summit-coffee",
            ttl_days=14,
        )
        reg.entries.append(e)
        # Search with different brand
        found = reg.find_by_keywords("coffee trends", brand_slug="other-brand")
        assert found is None
        # Search with matching brand
        found = reg.find_by_keywords("coffee trends", brand_slug="summit-coffee")
        assert found is not None

    def test_find_respects_category(self):
        reg = ResearchRegistry()
        e = ResearchEntry(
            id="e1",
            query="coffee trends",
            keywords=["coffee", "trends"],
            category="trends",
            ttl_days=14,
        )
        reg.entries.append(e)
        found = reg.find_by_keywords("coffee trends", category="brand_analysis")
        assert found is None
        found = reg.find_by_keywords("coffee trends", category="trends")
        assert found is not None

    def test_find_skips_expired(self):
        reg = ResearchRegistry()
        e = ResearchEntry(
            id="e1",
            query="coffee trends",
            keywords=["coffee", "trends"],
            category="trends",
            ttl_days=14,
        )
        e.created_at = datetime.utcnow() - timedelta(days=15)
        reg.entries.append(e)
        found = reg.find_by_keywords("coffee trends")
        assert found is None


# Storage tests
class TestResearchStorage:
    @pytest.fixture
    def storage(self, tmp_path, monkeypatch):
        """Create storage with temp directory."""
        monkeypatch.setattr("sip_studio.research.storage._get_research_dir", lambda: tmp_path)
        return ResearchStorage()

    def test_empty_registry_on_first_load(self, storage):
        reg = storage.load_registry()
        assert reg.version == 1
        assert len(reg.entries) == 0

    def test_save_and_load_registry(self, storage):
        reg = ResearchRegistry()
        e = ResearchEntry(id="test1", query="test query", keywords=["test"], category="trends")
        reg.entries.append(e)
        storage.save_registry(reg)
        loaded = storage.load_registry()
        assert len(loaded.entries) == 1
        assert loaded.entries[0].id == "test1"

    def test_add_entry_generates_id(self, storage):
        e = storage.add_entry(
            query="luxury trends",
            category="trends",
            brand_slug=None,
            summary="Summary here",
            sources=[],
        )
        assert len(e.id) == 8
        assert e.category == "trends"
        assert e.ttl_days == 14

    def test_add_entry_with_full_report(self, storage):
        e = storage.add_entry(
            query="deep research",
            category="brand_analysis",
            brand_slug="test-brand",
            summary="Summary",
            sources=[],
            full_report="# Full Report\n\nDetails here.",
        )
        assert e.full_report_path != ""
        assert Path(e.full_report_path).exists()
        content = storage.get_full_report(e.id)
        assert "# Full Report" in content

    def test_find_cached(self, storage):
        storage.add_entry(
            "luxury coffee trends",
            category="trends",
            brand_slug=None,
            summary="Coffee is hot",
            sources=[],
        )
        found = storage.find_cached("coffee trends design")
        assert found is not None
        assert "Coffee is hot" in found.summary

    def test_cleanup_expired(self, storage):
        # Add fresh entry
        storage.add_entry(
            "fresh entry", category="trends", brand_slug=None, summary="Fresh", sources=[]
        )
        # Add expired entry
        reg = storage.load_registry()
        old = ResearchEntry(
            id="old1", query="old query", keywords=["old"], category="trends", ttl_days=1
        )
        old.created_at = datetime.utcnow() - timedelta(days=5)
        reg.entries.append(old)
        storage.save_registry(reg)
        removed = storage.cleanup_expired()
        assert removed == 1
        reg = storage.load_registry()
        assert len(reg.entries) == 1
        assert reg.entries[0].id != "old1"

    def test_corrupt_registry_recovery(self, storage, tmp_path):
        (tmp_path / "registry.json").write_text("{corrupt json", encoding="utf-8")
        reg = storage.load_registry()
        assert reg.version == 1
        assert len(reg.entries) == 0

    # Pending jobs tests
    def test_empty_pending_on_first_load(self, storage):
        pl = storage.load_pending()
        assert pl.version == 1
        assert len(pl.jobs) == 0

    def test_add_and_get_pending(self, storage):
        job = storage.add_pending(
            "resp123", "test query", brand_slug="test-brand", session_id="sess1"
        )
        assert job.response_id == "resp123"
        found = storage.get_pending("resp123")
        assert found is not None
        assert found.session_id == "sess1"

    def test_get_pending_by_session(self, storage):
        storage.add_pending("r1", "q1", None, "session_a")
        storage.add_pending("r2", "q2", None, "session_b")
        storage.add_pending("r3", "q3", None, "session_a")
        jobs = storage.get_pending_by_session("session_a")
        assert len(jobs) == 2
        assert all(j.session_id == "session_a" for j in jobs)

    def test_remove_pending(self, storage):
        storage.add_pending("resp1", "q1", None, "s1")
        assert storage.remove_pending("resp1")
        assert storage.get_pending("resp1") is None
        assert not storage.remove_pending("resp1")  # Already removed

    def test_get_all_pending_for_recovery(self, storage):
        storage.add_pending("r1", "q1", None, "s1")
        storage.add_pending("r2", "q2", None, "s2")
        all_jobs = storage.get_all_pending()
        assert len(all_jobs) == 2

    def test_corrupt_pending_recovery(self, storage, tmp_path):
        (tmp_path / "pending.json").write_text("{{bad", encoding="utf-8")
        pl = storage.load_pending()
        assert pl.version == 1
        assert len(pl.jobs) == 0


# ResearchService tests
class TestResearchService:
    @pytest.fixture
    def svc_mock_state(self):
        """Create mock BridgeState."""
        from unittest.mock import MagicMock

        state = MagicMock()
        state.get_active_slug.return_value = "test-brand"
        return state

    @pytest.fixture
    def service(self, tmp_path, monkeypatch, svc_mock_state):
        """Create ResearchService with temp storage."""
        monkeypatch.setattr("sip_studio.research.storage._get_research_dir", lambda: tmp_path)
        from sip_studio.studio.services.research_service import ResearchService

        return ResearchService(svc_mock_state)

    def test_find_cached_research_miss(self, service):
        """Test cache miss returns None."""
        result = service.find_cached_research("some query", "test-brand")
        assert result is None

    def test_find_cached_research_hit(self, service):
        """Test cache hit after adding entry."""
        service._storage.add_entry(
            "luxury coffee trends",
            category="trends",
            brand_slug="test-brand",
            summary="Coffee trends summary",
            sources=[],
        )
        result = service.find_cached_research("coffee trends", "test-brand")
        assert result is not None
        assert "coffee" in result.summary.lower()

    def test_get_research_entry_not_found(self, service):
        """Test getting non-existent entry."""
        result = service.get_research_entry("nonexistent")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_get_research_entry_found(self, service):
        """Test getting existing entry."""
        entry = service._storage.add_entry(
            "test query", category="trends", brand_slug=None, summary="Test summary", sources=[]
        )
        result = service.get_research_entry(entry.id)
        assert result["success"]
        assert result["data"]["summary"] == "Test summary"

    def test_list_research_empty(self, service):
        """Test listing with no entries."""
        result = service.list_research()
        assert result["success"]
        assert len(result["data"]["entries"]) == 0

    def test_list_research_filtered_by_brand(self, service):
        """Test listing filtered by brand."""
        service._storage.add_entry(
            "q1", category="trends", brand_slug="brand-a", summary="A", sources=[]
        )
        service._storage.add_entry(
            "q2", category="trends", brand_slug="brand-b", summary="B", sources=[]
        )
        result = service.list_research(brand_slug="brand-a")
        assert result["success"]
        assert len(result["data"]["entries"]) == 1
        assert result["data"]["entries"][0]["brandSlug"] == "brand-a"

    def test_list_research_filtered_by_category(self, service):
        """Test listing filtered by category."""
        service._storage.add_entry(
            "q1", category="trends", brand_slug=None, summary="Trends", sources=[]
        )
        service._storage.add_entry(
            "q2", category="techniques", brand_slug=None, summary="Tech", sources=[]
        )
        result = service.list_research(category="techniques")
        assert result["success"]
        assert len(result["data"]["entries"]) == 1
        assert result["data"]["entries"][0]["category"] == "techniques"

    def test_cleanup_expired(self, service):
        """Test cleanup removes expired entries."""
        service._storage.add_entry(
            "fresh", category="trends", brand_slug=None, summary="Fresh", sources=[]
        )
        # Add expired entry manually
        reg = service._storage.load_registry()
        old = ResearchEntry(id="old1", query="old", keywords=["old"], category="trends", ttl_days=1)
        old.created_at = datetime.utcnow() - timedelta(days=5)
        reg.entries.append(old)
        service._storage.save_registry(reg)
        result = service.cleanup_expired()
        assert result["success"]
        assert result["data"]["removed"] == 1

    def test_find_research_bridge_method(self, service):
        """Test find_research bridge method."""
        result = service.find_research("nonexistent query")
        assert result["success"]
        assert not result["data"]["found"]
        service._storage.add_entry(
            "coffee trends",
            category="trends",
            brand_slug="test-brand",
            summary="Coffee!",
            sources=[],
        )
        result = service.find_research("coffee trends")
        assert result["success"]
        assert result["data"]["found"]
        assert "Coffee" in result["data"]["entry"]["summary"]

    def test_pending_research_lifecycle(self, service):
        """Test pending research add/get/remove."""
        # Add pending job
        service._storage.add_pending("resp123", "test query", "test-brand", "session1")
        # Get pending via bridge method
        result = service.get_pending_research()
        assert result["success"]
        assert len(result["data"]["jobs"]) == 1
        assert result["data"]["jobs"][0]["responseId"] == "resp123"
        # Cancel pending
        result = service.cancel_research("resp123")
        assert result["success"]
        assert result["data"]["cancelled"]
        # Verify removed
        result = service.get_pending_research()
        assert len(result["data"]["jobs"]) == 0

    def test_get_pending_for_session(self, service):
        """Test getting pending jobs for a specific session."""
        service._storage.add_pending("r1", "q1", None, "sess1")
        service._storage.add_pending("r2", "q2", None, "sess2")
        service._storage.add_pending("r3", "q3", None, "sess1")
        jobs = service.get_pending_for_session("sess1")
        assert len(jobs) == 2

    def test_build_research_query(self):
        """Test query building from clarification answers."""
        from sip_studio.studio.services.research_service import _build_research_query

        q = _build_research_query("luxury packaging", {"focus": "visual", "depth": "thorough"})
        assert "luxury packaging" in q
        assert "visual" in q
        assert "comprehensive" in q.lower()
        q2 = _build_research_query("test", {"focus": "custom:specific detail"})
        assert "specific detail" in q2

    def test_poll_deep_research_persists_result_to_session_history(
        self, isolated_home, monkeypatch, svc_mock_state
    ):
        """Deep research completion should be persisted so it shows up in chat history."""
        import asyncio
        from unittest.mock import MagicMock

        from sip_studio.advisor.session_manager import SessionManager
        from sip_studio.studio.services.research_service import ResearchService

        brand_slug = "test-brand"
        mgr = SessionManager(brand_slug)
        session = mgr.create_session(title="Test Session")

        service = ResearchService(svc_mock_state)
        response_id = "resp123"
        summary = "This is the final deep research report."
        service._storage.add_pending(response_id, "test query", brand_slug, session.id)

        class _DummyOutput:
            def __init__(self, text: str):
                self.text = text

        class _DummyInteraction:
            def __init__(self, status: str, text: str):
                self.status = status
                self.outputs = [_DummyOutput(text)]
                self.grounding_metadata = None

        mock_client = MagicMock()
        mock_client.interactions.get.return_value = _DummyInteraction("completed", summary)
        monkeypatch.setattr(service, "_get_client", lambda: mock_client)

        result = asyncio.run(service.poll_deep_research(response_id))
        assert result.status == "completed"

        mf = mgr.load_messages_file(session.id)
        assert mf is not None
        assert any(
            m.role == "assistant" and "Deep Research Complete" in m.content and summary in m.content
            for m in mf.full_history
        )


# Research tools tests
class TestResearchTools:
    @pytest.fixture(autouse=True)
    def setup_tools(self, tmp_path, monkeypatch):
        """Set up research tools with mocked service."""
        from unittest.mock import MagicMock

        monkeypatch.setattr("sip_studio.research.storage._get_research_dir", lambda: tmp_path)
        # Import the module first, then patch on the imported module object
        from sip_studio.advisor.tools import _common, research_tools

        monkeypatch.setattr(_common, "get_active_brand", lambda: "test-brand")
        mock_state = MagicMock()
        mock_state.get_active_slug.return_value = "test-brand"
        from sip_studio.studio.services.research_service import ResearchService

        self.service = ResearchService(mock_state)
        research_tools.set_research_service_factory(lambda: self.service)
        yield
        research_tools.set_research_service_factory(None)

    def test_get_pending_research_clarification_initially_none(self):
        """Test that pending clarification is None initially."""
        from sip_studio.advisor.tools.research_tools import get_pending_research_clarification

        assert get_pending_research_clarification() is None

    def test_request_deep_research_sets_clarification(self):
        """Test that request_deep_research sets pending clarification."""
        from sip_studio.advisor.tools.research_tools import (
            _impl_request_deep_research,
            get_pending_research_clarification,
        )

        result = _impl_request_deep_research(
            "luxury coffee trends", "User wants to know about trends"
        )
        assert "[Presenting deep research options" in result
        clarification = get_pending_research_clarification()
        assert clarification is not None
        assert clarification["type"] == "deep_research_clarification"
        assert clarification["query"] == "luxury coffee trends"
        assert len(clarification["questions"]) == 2
        # Verify questions have expected structure
        q1 = clarification["questions"][0]
        assert q1["id"] == "focus"
        assert q1["allowCustom"] is True
        assert len(q1["options"]) == 3

    def test_get_pending_clears_after_read(self):
        """Test that get_pending_research_clarification clears after read."""
        from sip_studio.advisor.tools.research_tools import (
            _impl_request_deep_research,
            get_pending_research_clarification,
        )

        _impl_request_deep_research("test", "context")
        assert get_pending_research_clarification() is not None
        assert get_pending_research_clarification() is None

    def test_peek_pending_does_not_clear(self):
        """Test that peek_pending_research_clarification does not clear state."""
        from sip_studio.advisor.tools.research_tools import (
            _impl_request_deep_research,
            get_pending_research_clarification,
            peek_pending_research_clarification,
        )

        _impl_request_deep_research("test", "context")
        assert peek_pending_research_clarification() is not None
        assert peek_pending_research_clarification() is not None
        assert get_pending_research_clarification() is not None
        assert peek_pending_research_clarification() is None

    def test_has_pending_reflects_state(self):
        """Test has_pending_research_clarification reflects pending state."""
        from sip_studio.advisor.tools.research_tools import (
            _impl_request_deep_research,
            get_pending_research_clarification,
            has_pending_research_clarification,
        )

        assert has_pending_research_clarification() is False
        _impl_request_deep_research("test", "context")
        assert has_pending_research_clarification() is True
        assert get_pending_research_clarification() is not None
        assert has_pending_research_clarification() is False

    def test_search_research_cache_no_results(self):
        """Test search cache with no matching results."""
        from sip_studio.advisor.tools.research_tools import _impl_search_research_cache

        result = _impl_search_research_cache(["nonexistent", "keywords"])
        assert "No cached research found" in result

    def test_search_research_cache_with_results(self):
        """Test search cache with matching results."""
        self.service._storage.add_entry(
            "coffee packaging trends",
            category="trends",
            brand_slug="test-brand",
            summary="Coffee packaging is trending toward minimalism.",
            sources=[ResearchSource(url="https://example.com", title="Source", snippet="")],
        )
        from sip_studio.advisor.tools.research_tools import _impl_search_research_cache

        result = _impl_search_research_cache(["coffee", "trends"])
        assert "minimalism" in result
        assert "Source" in result or "example.com" in result

    def test_web_search_checks_cache_first(self, monkeypatch):
        """Test that web_search checks cache before making API call."""
        import asyncio

        self.service._storage.add_entry(
            "luxury skincare trends",
            category="trends",
            brand_slug="test-brand",
            summary="Cached skincare trends result.",
            sources=[ResearchSource(url="https://cached.com", title="Cached", snippet="")],
        )
        from sip_studio.advisor.tools.research_tools import _impl_web_search

        result = asyncio.run(_impl_web_search("skincare trends"))
        assert "[From cache" in result
        assert "Cached skincare trends result" in result

    def test_research_tools_list_contains_all_tools(self):
        """Test that RESEARCH_TOOLS list contains expected tools."""
        from sip_studio.advisor.tools.research_tools import RESEARCH_TOOLS

        assert len(RESEARCH_TOOLS) == 4
        tool_names = [t.name for t in RESEARCH_TOOLS]
        assert "web_search" in tool_names
        assert "request_deep_research" in tool_names
        assert "get_research_status" in tool_names
        assert "search_research_cache" in tool_names

    def test_function_tool_decorators(self):
        """Test that tools are properly decorated as function_tools."""
        from sip_studio.advisor.tools.research_tools import (
            get_research_status,
            request_deep_research,
            search_research_cache,
            web_search,
        )

        # function_tool decorated functions have a 'name' attribute
        assert hasattr(web_search, "name")
        assert hasattr(request_deep_research, "name")
        assert hasattr(get_research_status, "name")
        assert hasattr(search_research_cache, "name")

    def test_set_research_service_factory_none_raises(self):
        """Test that calling tools without factory raises error."""
        from sip_studio.advisor.tools.research_tools import (
            _get_research_service,
            set_research_service_factory,
        )

        set_research_service_factory(None)
        with pytest.raises(RuntimeError, match="factory not set"):
            _get_research_service()
        # Restore for other tests
        set_research_service_factory(lambda: self.service)
