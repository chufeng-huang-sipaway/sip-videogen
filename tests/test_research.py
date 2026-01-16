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
