"""Tests for lean context loading (Stage 3).
Tests SessionContextCache, knowledge_summary builders, and context tools.
"""

from pathlib import Path

import pytest

from sip_studio.advisor.session_context_cache import (
    CacheEntryData,
    SessionContextCache,
    _active_caches,
    invalidate_caches_for_brand,
)
from sip_studio.brands.knowledge_summary import (
    build_brand_knowledge_pointer,
    build_knowledge_context,
    build_product_knowledge_pointer,
    build_products_list_summary,
)


@pytest.fixture
def tmp_brand_dir(tmp_path, monkeypatch):
    """Create temporary brand directory and mock get_brand_dir/get_session_dir."""
    brand_slug = "test-brand"
    session_id = "test-session-123"
    brand_dir = tmp_path / ".sip-studio" / "brands" / brand_slug
    session_dir = brand_dir / "sessions" / session_id
    session_dir.mkdir(parents=True)

    def mock_get_brand_dir(slug: str) -> Path:
        return tmp_path / ".sip-studio" / "brands" / slug

    def mock_get_session_dir(slug: str, sid: str) -> Path:
        return tmp_path / ".sip-studio" / "brands" / slug / "sessions" / sid

    monkeypatch.setattr(
        "sip_studio.advisor.session_context_cache.get_session_dir", mock_get_session_dir
    )
    monkeypatch.setattr("sip_studio.advisor.session_manager.get_brand_dir", mock_get_brand_dir)
    return brand_slug, session_id, tmp_path


@pytest.fixture
def mock_brand_summary():
    """Create mock BrandSummary object."""

    class MockSummary:
        slug = "test-brand"
        name = "Test Brand Co"
        tagline = "Testing makes perfect"
        category = "Software"
        tone = "Professional, Modern"
        primary_colors = ["#FF0000", "#00FF00", "#0000FF"]
        visual_style = "Clean minimalist design with bold accents"
        audience_summary = "Developers who value quality"
        available_details = ["visual_identity", "voice_guidelines"]

    return MockSummary()


@pytest.fixture
def mock_product_summaries():
    """Create mock ProductSummary objects."""

    class MockProduct:
        def __init__(self, slug, name, desc, attrs, pkg):
            self.slug = slug
            self.name = name
            self.description = desc
            self.attribute_count = attrs
            self.has_packaging_text = pkg

    return [
        MockProduct("coffee-mug", "Coffee Mug", "A premium ceramic mug for coffee lovers", 5, True),
        MockProduct("tea-pot", "Tea Pot", "Elegant teapot for afternoon tea", 3, False),
    ]


class TestCacheEntryData:
    def test_to_dict(self):
        entry = CacheEntryData(
            value="test value", expires_at="2024-01-01T00:00:00Z", source_version="v1"
        )
        d = entry.to_dict()
        assert d["value"] == "test value"
        assert d["expires_at"] == "2024-01-01T00:00:00Z"
        assert d["source_version"] == "v1"

    def test_from_dict(self):
        d = {"value": "hello", "expires_at": "2024-06-01T12:00:00Z", "source_version": "v2"}
        entry = CacheEntryData.from_dict(d)
        assert entry.value == "hello"
        assert entry.expires_at == "2024-06-01T12:00:00Z"
        assert entry.source_version == "v2"


class TestSessionContextCache:
    def test_create_empty_cache(self, tmp_brand_dir):
        brand_slug, session_id, _ = tmp_brand_dir
        # Clear global registry
        _active_caches.clear()
        cache = SessionContextCache(brand_slug, session_id)
        assert cache.get_stats()["entry_count"] == 0

    def test_set_and_get(self, tmp_brand_dir):
        brand_slug, session_id, _ = tmp_brand_dir
        _active_caches.clear()
        cache = SessionContextCache(brand_slug, session_id)
        cache.set("product:mug", "Full product details here", "v1")
        result = cache.get("product:mug")
        assert result == "Full product details here"

    def test_version_invalidation(self, tmp_brand_dir):
        brand_slug, session_id, _ = tmp_brand_dir
        _active_caches.clear()
        cache = SessionContextCache(brand_slug, session_id)
        cache.set("product:mug", "Old details", "v1")
        # Same version - should return cached
        assert cache.get("product:mug", "v1") == "Old details"
        # Different version - should invalidate
        assert cache.get("product:mug", "v2") is None
        # Entry should be gone
        assert cache.get("product:mug") is None

    def test_ttl_expiration(self, tmp_brand_dir):
        brand_slug, session_id, tmp_path = tmp_brand_dir
        _active_caches.clear()
        cache = SessionContextCache(brand_slug, session_id)
        # Manually set expired entry
        cache._cache["expired_key"] = CacheEntryData(
            value="old", expires_at="2020-01-01T00:00:00Z", source_version="v1"
        )
        # Should return None and remove entry
        assert cache.get("expired_key") is None
        assert "expired_key" not in cache._cache

    def test_invalidate_pattern(self, tmp_brand_dir):
        brand_slug, session_id, _ = tmp_brand_dir
        _active_caches.clear()
        cache = SessionContextCache(brand_slug, session_id)
        cache.set("product:mug", "mug data", "v1")
        cache.set("product:pot", "pot data", "v1")
        cache.set("brand:identity", "brand data", "v1")
        cache.invalidate("product:*")
        assert cache.get("product:mug") is None
        assert cache.get("product:pot") is None
        assert cache.get("brand:identity") == "brand data"

    def test_persistence(self, tmp_brand_dir):
        brand_slug, session_id, tmp_path = tmp_brand_dir
        _active_caches.clear()
        cache1 = SessionContextCache(brand_slug, session_id)
        cache1.set("persistent_key", "persistent_value", "v1", ttl_minutes=60)
        # Create new cache instance - should load from disk
        _active_caches.clear()
        cache2 = SessionContextCache(brand_slug, session_id)
        assert cache2.get("persistent_key") == "persistent_value"

    def test_clear(self, tmp_brand_dir):
        brand_slug, session_id, _ = tmp_brand_dir
        _active_caches.clear()
        cache = SessionContextCache(brand_slug, session_id)
        cache.set("key1", "val1", "v1")
        cache.set("key2", "val2", "v1")
        cache.clear()
        assert cache.get_stats()["entry_count"] == 0


class TestGlobalCacheRegistry:
    def test_invalidate_caches_for_brand(self, tmp_brand_dir):
        brand_slug, session_id, _ = tmp_brand_dir
        _active_caches.clear()
        cache = SessionContextCache(brand_slug, session_id)
        cache.set("product:mug", "mug data", "v1")
        invalidate_caches_for_brand(brand_slug, "product:*")
        assert cache.get("product:mug") is None

    def test_no_cross_brand_invalidation(self, tmp_brand_dir):
        brand_slug, session_id, tmp_path = tmp_brand_dir
        _active_caches.clear()
        # Create dir for other brand
        other_dir = tmp_path / ".sip-studio" / "brands" / "other-brand" / "sessions" / "sess2"
        other_dir.mkdir(parents=True)
        cache1 = SessionContextCache(brand_slug, session_id)
        cache1.set("product:mug", "brand1 mug", "v1")
        # Manually register cache2 since mock only handles one brand
        # (In real usage, each brand would have separate get_session_dir)
        _active_caches["other-brand:sess2"] = cache1  # Simulate wrong brand
        invalidate_caches_for_brand("different-brand", "product:*")
        assert cache1.get("product:mug") == "brand1 mug"


class TestBrandKnowledgePointer:
    def test_builds_compact_context(self, mock_brand_summary):
        result = build_brand_knowledge_pointer(mock_brand_summary)
        assert "Test Brand Co" in result
        assert "Testing makes perfect" in result
        assert "Software" in result
        assert "#FF0000" in result
        assert "fetch_brand_detail" in result

    def test_handles_missing_fields(self):
        class MinimalSummary:
            slug = "minimal"
            name = "Minimal"
            tagline = ""
            category = ""
            tone = ""
            primary_colors = []
            visual_style = ""
            audience_summary = ""

        result = build_brand_knowledge_pointer(MinimalSummary())
        assert "Minimal" in result
        assert "Not defined" in result


class TestProductKnowledgePointer:
    def test_builds_compact_context(self, mock_product_summaries):
        result = build_product_knowledge_pointer(mock_product_summaries[0])
        assert "Coffee Mug" in result
        assert "coffee-mug" in result
        assert "5" in result
        assert "Yes" in result
        assert "get_product_detail" in result


class TestProductsListSummary:
    def test_empty_list(self):
        result = build_products_list_summary([])
        assert "No products" in result
        assert "manage_product(action='create')" in result

    def test_list_with_products(self, mock_product_summaries):
        result = build_products_list_summary(mock_product_summaries)
        assert "2 total" in result
        assert "coffee-mug" in result
        assert "tea-pot" in result
        assert "📦" in result  # packaging indicator

    def test_truncates_long_list(self, mock_product_summaries):
        # Create 15 products
        many = [
            type(mock_product_summaries[0])(f"prod-{i}", f"Product {i}", "desc", 1, False)
            for i in range(15)
        ]
        result = build_products_list_summary(many)
        assert "15 total" in result
        assert "...and 5 more" in result


class TestBuildKnowledgeContext:
    def test_combines_all_sections(self, mock_brand_summary, mock_product_summaries):
        result = build_knowledge_context(
            brand_summary=mock_brand_summary,
            products=mock_product_summaries,
            conversation_summary="User asked about product photos.",
        )
        assert "Test Brand Co" in result
        assert "Previous Conversation" in result
        assert "2 total" in result

    def test_with_no_context(self):
        result = build_knowledge_context()
        assert "No brand context" in result

    def test_with_summary_only(self):
        result = build_knowledge_context(conversation_summary="We discussed marketing.")
        assert "Previous Conversation" in result
        assert "We discussed marketing" in result
