"""Tests for brand memory access and context building functions."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from sip_videogen.brands.context import (
    DETAIL_DESCRIPTIONS,
    BrandContextBuilder,
    build_brand_context,
)
from sip_videogen.brands.memory import (
    get_brand_detail,
    get_brand_summary,
    list_brand_assets,
)
from sip_videogen.brands.models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIdentityFull,
    ColorDefinition,
    CompetitivePositioning,
    VisualIdentity,
    VoiceGuidelines,
)
from sip_videogen.brands.storage import create_brand
from sip_videogen.brands.tools import (
    _impl_browse_brand_assets as browse_brand_assets,
    _impl_fetch_brand_detail as fetch_brand_detail,
    get_brand_context,
    set_brand_context,
)


@pytest.fixture
def temp_brands_dir(tmp_path: Path):
    """Create a temporary brands directory for testing."""
    brands_dir = tmp_path / ".sip-videogen" / "brands"
    brands_dir.mkdir(parents=True)

    with patch("sip_videogen.brands.storage.get_brands_dir", return_value=brands_dir):
        yield brands_dir


@pytest.fixture
def sample_brand_identity() -> BrandIdentityFull:
    """Create a sample brand identity for testing."""
    identity = BrandIdentityFull(slug="test-brand")
    identity.core = BrandCoreIdentity(
        name="Test Brand",
        tagline="Testing made easy",
        mission="To make testing accessible to everyone",
        values=["quality", "simplicity", "reliability"],
    )
    identity.positioning = CompetitivePositioning(
        market_category="Testing Tools",
        unique_value_proposition="The simplest testing solution",
        primary_competitors=["Competitor A", "Competitor B"],
        differentiation="We focus on simplicity above all",
    )
    identity.voice = VoiceGuidelines(
        personality="Friendly and approachable expert",
        tone_attributes=["friendly", "clear", "helpful"],
        key_messages=["Testing should be simple", "Quality matters"],
        messaging_do=["Be concise", "Use examples"],
        messaging_dont=["Be condescending", "Use jargon"],
    )
    identity.visual = VisualIdentity(
        primary_colors=[
            ColorDefinition(hex="#FF5733", name="Vibrant Orange", usage="Call to action"),
            ColorDefinition(hex="#2E86AB", name="Ocean Blue", usage="Primary brand"),
        ],
        overall_aesthetic="Clean and modern with bold accents",
        imagery_style="Professional photography with natural lighting",
        style_keywords=["modern", "clean", "professional"],
    )
    identity.audience = AudienceProfile(
        primary_summary="Software developers who value simplicity",
        age_range="25-45",
        interests=["technology", "productivity", "automation"],
        pain_points=["Complex tools", "Steep learning curves"],
    )
    return identity


@pytest.fixture
def brand_with_assets(temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull):
    """Create a brand with some assets for testing."""
    create_brand(sample_brand_identity)

    # Create some asset files
    brand_dir = temp_brands_dir / "test-brand"
    (brand_dir / "assets" / "logo" / "primary-logo.png").write_bytes(b"fake png")
    (brand_dir / "assets" / "logo" / "secondary-logo.jpg").write_bytes(b"fake jpg")
    (brand_dir / "assets" / "marketing" / "banner.webp").write_bytes(b"fake webp")
    (brand_dir / "assets" / "lifestyle" / "hero-shot.jpeg").write_bytes(b"fake jpeg")
    (brand_dir / "assets" / "generated").mkdir(parents=True, exist_ok=True)
    (brand_dir / "assets" / "generated" / "concept.png").write_bytes(b"fake png")
    # Non-image file should be ignored
    (brand_dir / "assets" / "logo" / "readme.txt").write_text("ignore this")

    return sample_brand_identity


# ============================================================================
# Tests for memory.py functions
# ============================================================================


class TestGetBrandSummary:
    """Tests for get_brand_summary function."""

    def test_returns_summary_for_existing_brand(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that get_brand_summary returns a summary for an existing brand."""
        create_brand(sample_brand_identity)

        summary = get_brand_summary("test-brand")

        assert summary is not None
        assert summary.slug == "test-brand"
        assert summary.name == "Test Brand"
        assert summary.tagline == "Testing made easy"

    def test_returns_none_for_nonexistent_brand(self, temp_brands_dir: Path) -> None:
        """Test that get_brand_summary returns None for nonexistent brand."""
        summary = get_brand_summary("nonexistent")
        assert summary is None


class TestGetBrandDetail:
    """Tests for get_brand_detail function."""

    def test_visual_identity_returns_json(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test fetching visual_identity returns valid JSON."""
        create_brand(sample_brand_identity)

        result = get_brand_detail("test-brand", "visual_identity")

        # Should be valid JSON
        data = json.loads(result)
        assert "primary_colors" in data
        assert len(data["primary_colors"]) == 2
        assert data["primary_colors"][0]["hex"] == "#FF5733"

    def test_voice_guidelines_returns_json(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test fetching voice_guidelines returns valid JSON."""
        create_brand(sample_brand_identity)

        result = get_brand_detail("test-brand", "voice_guidelines")

        data = json.loads(result)
        assert "tone_attributes" in data
        assert "friendly" in data["tone_attributes"]

    def test_audience_profile_returns_json(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test fetching audience_profile returns valid JSON."""
        create_brand(sample_brand_identity)

        result = get_brand_detail("test-brand", "audience_profile")

        data = json.loads(result)
        assert "primary_summary" in data
        assert "simplicity" in data["primary_summary"]

    def test_positioning_returns_json(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test fetching positioning returns valid JSON."""
        create_brand(sample_brand_identity)

        result = get_brand_detail("test-brand", "positioning")

        data = json.loads(result)
        assert "market_category" in data
        assert data["market_category"] == "Testing Tools"

    def test_full_identity_returns_json(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test fetching full_identity returns complete brand."""
        create_brand(sample_brand_identity)

        result = get_brand_detail("test-brand", "full_identity")

        data = json.loads(result)
        assert "slug" in data
        assert "core" in data
        assert "visual" in data
        assert "voice" in data
        assert data["slug"] == "test-brand"

    def test_nonexistent_brand_returns_error(self, temp_brands_dir: Path) -> None:
        """Test that nonexistent brand returns error message."""
        result = get_brand_detail("nonexistent", "visual_identity")
        assert result.startswith("Error:")
        assert "not found" in result

    def test_invalid_detail_type_returns_error(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that invalid detail type returns error message."""
        create_brand(sample_brand_identity)

        result = get_brand_detail("test-brand", "invalid_type")  # type: ignore

        assert result.startswith("Error:")
        assert "Unknown detail type" in result


class TestListBrandAssets:
    """Tests for list_brand_assets function."""

    def test_returns_empty_for_nonexistent_brand(self, temp_brands_dir: Path) -> None:
        """Test that nonexistent brand returns empty list."""
        assets = list_brand_assets("nonexistent")
        assert assets == []

    def test_returns_empty_for_brand_without_assets(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that brand without assets returns empty list."""
        create_brand(sample_brand_identity)

        assets = list_brand_assets("test-brand")
        assert assets == []

    def test_returns_all_assets(self, brand_with_assets: BrandIdentityFull) -> None:
        """Test that all assets are returned without category filter."""
        assets = list_brand_assets("test-brand")

        assert len(assets) == 5  # 2 logos + 1 marketing + 1 lifestyle + 1 generated
        categories = {a["category"] for a in assets}
        assert categories == {"logo", "marketing", "lifestyle", "generated"}

    def test_filters_by_category(self, brand_with_assets: BrandIdentityFull) -> None:
        """Test that category filter works correctly."""
        assets = list_brand_assets("test-brand", category="logo")

        assert len(assets) == 2
        assert all(a["category"] == "logo" for a in assets)

    def test_returns_correct_asset_info(self, brand_with_assets: BrandIdentityFull) -> None:
        """Test that asset info includes all required fields."""
        assets = list_brand_assets("test-brand", category="logo")

        for asset in assets:
            assert "path" in asset
            assert "category" in asset
            assert "name" in asset
            assert "filename" in asset
            assert asset["category"] == "logo"

    def test_filters_non_image_files(self, brand_with_assets: BrandIdentityFull) -> None:
        """Test that non-image files are excluded."""
        assets = list_brand_assets("test-brand", category="logo")

        filenames = [a["filename"] for a in assets]
        assert "readme.txt" not in filenames

    def test_filters_generated_category(self, brand_with_assets: BrandIdentityFull) -> None:
        """Test that generated assets category is supported."""
        assets = list_brand_assets("test-brand", category="generated")

        assert len(assets) == 1
        assert assets[0]["category"] == "generated"

    def test_empty_category_returns_empty(self, brand_with_assets: BrandIdentityFull) -> None:
        """Test that filtering by empty category returns empty list."""
        assets = list_brand_assets("test-brand", category="mascot")
        assert assets == []


# ============================================================================
# Tests for tools.py functions
# ============================================================================


class TestBrandContext:
    """Tests for brand context management."""

    def test_set_and_get_brand_context(self) -> None:
        """Test setting and getting brand context."""
        set_brand_context("my-brand")
        assert get_brand_context() == "my-brand"

    def test_clear_brand_context(self) -> None:
        """Test clearing brand context."""
        set_brand_context("my-brand")
        set_brand_context(None)
        assert get_brand_context() is None

    def test_initial_context_is_none(self) -> None:
        """Test that initial context is None."""
        # Reset first
        set_brand_context(None)
        assert get_brand_context() is None


class TestFetchBrandDetailTool:
    """Tests for fetch_brand_detail tool function."""

    def test_returns_error_without_context(self) -> None:
        """Test that fetch_brand_detail returns error without brand context."""
        set_brand_context(None)

        result = fetch_brand_detail("visual_identity")

        assert result.startswith("Error:")
        assert "No brand context" in result

    def test_fetches_detail_with_context(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test fetching detail with brand context set."""
        create_brand(sample_brand_identity)
        set_brand_context("test-brand")

        result = fetch_brand_detail("visual_identity")

        # Should be valid JSON
        data = json.loads(result)
        assert "primary_colors" in data

    def test_returns_error_for_nonexistent_brand(self, temp_brands_dir: Path) -> None:
        """Test that nonexistent brand returns error."""
        set_brand_context("nonexistent")

        result = fetch_brand_detail("visual_identity")

        assert result.startswith("Error:")
        assert "not found" in result


class TestBrowseBrandAssetsTool:
    """Tests for browse_brand_assets tool function."""

    def test_returns_error_without_context(self) -> None:
        """Test that browse_brand_assets returns error without brand context."""
        set_brand_context(None)

        result = browse_brand_assets()

        assert result.startswith("Error:")
        assert "No brand context" in result

    def test_returns_no_assets_message(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that brand without assets returns appropriate message."""
        create_brand(sample_brand_identity)
        set_brand_context("test-brand")

        result = browse_brand_assets()

        assert "No assets found" in result

    def test_returns_json_with_assets(self, brand_with_assets: BrandIdentityFull) -> None:
        """Test that assets are returned as JSON."""
        set_brand_context("test-brand")

        result = browse_brand_assets()

        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 5  # logo(2) + marketing(1) + lifestyle(1) + generated(1)

    def test_filters_by_category(self, brand_with_assets: BrandIdentityFull) -> None:
        """Test that category filter works."""
        set_brand_context("test-brand")

        result = browse_brand_assets(category="logo")

        data = json.loads(result)
        assert len(data) == 2
        assert all(a["category"] == "logo" for a in data)

    def test_no_assets_with_category_filter(
        self, brand_with_assets: BrandIdentityFull
    ) -> None:
        """Test message when category has no assets."""
        set_brand_context("test-brand")

        result = browse_brand_assets(category="mascot")

        assert "No assets found" in result
        assert "mascot" in result


# ============================================================================
# Tests for context.py functions
# ============================================================================


class TestBrandContextBuilder:
    """Tests for BrandContextBuilder class."""

    def test_raises_for_nonexistent_brand(self, temp_brands_dir: Path) -> None:
        """Test that BrandContextBuilder raises ValueError for nonexistent brand."""
        with pytest.raises(ValueError, match="not found"):
            BrandContextBuilder("nonexistent")

    def test_builds_context_with_brand_info(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that context includes brand information."""
        create_brand(sample_brand_identity)

        builder = BrandContextBuilder("test-brand")
        context = builder.build_context_section()

        assert "Test Brand" in context
        assert "Testing made easy" in context
        assert "Testing Tools" in context

    def test_includes_primary_colors(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that context includes primary colors."""
        create_brand(sample_brand_identity)

        builder = BrandContextBuilder("test-brand")
        context = builder.build_context_section()

        assert "#FF5733" in context
        assert "#2E86AB" in context

    def test_includes_available_details_section(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that context includes available details section."""
        create_brand(sample_brand_identity)

        builder = BrandContextBuilder("test-brand")
        context = builder.build_context_section()

        assert "Available Brand Details" in context
        assert "fetch_brand_detail" in context
        assert "visual_identity" in context
        assert "voice_guidelines" in context

    def test_includes_memory_exploration_protocol(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that context includes memory exploration protocol."""
        create_brand(sample_brand_identity)

        builder = BrandContextBuilder("test-brand")
        context = builder.build_context_section()

        assert "Memory Exploration Protocol" in context
        assert "IMPORTANT" in context
        assert "fetch_brand_detail()" in context
        assert "browse_brand_assets()" in context

    def test_includes_asset_count(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that context includes asset count."""
        create_brand(sample_brand_identity)

        builder = BrandContextBuilder("test-brand")
        context = builder.build_context_section()

        assert "Asset Library" in context
        assert "existing assets" in context

    def test_inject_into_prompt(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that inject_into_prompt replaces placeholder."""
        create_brand(sample_brand_identity)

        builder = BrandContextBuilder("test-brand")
        base_prompt = "You are an agent. {brand_context} Do your work."

        result = builder.inject_into_prompt(base_prompt)

        assert "{brand_context}" not in result
        assert "Test Brand" in result
        assert "You are an agent." in result
        assert "Do your work." in result

    def test_inject_with_custom_placeholder(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test inject_into_prompt with custom placeholder."""
        create_brand(sample_brand_identity)

        builder = BrandContextBuilder("test-brand")
        base_prompt = "You are an agent. {{BRAND}} Do your work."

        result = builder.inject_into_prompt(base_prompt, placeholder="{{BRAND}}")

        assert "{{BRAND}}" not in result
        assert "Test Brand" in result


class TestBuildBrandContext:
    """Tests for build_brand_context convenience function."""

    def test_returns_context_for_existing_brand(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that build_brand_context returns context for existing brand."""
        create_brand(sample_brand_identity)

        context = build_brand_context("test-brand")

        assert "Test Brand" in context
        assert "Error:" not in context

    def test_returns_error_for_nonexistent_brand(self, temp_brands_dir: Path) -> None:
        """Test that build_brand_context returns error for nonexistent brand."""
        context = build_brand_context("nonexistent")

        assert "Error:" in context
        assert "not found" in context


class TestDetailDescriptions:
    """Tests for DETAIL_DESCRIPTIONS constant."""

    def test_has_all_detail_types(self) -> None:
        """Test that DETAIL_DESCRIPTIONS includes all detail types."""
        expected_types = [
            "visual_identity",
            "voice_guidelines",
            "audience_profile",
            "positioning",
        ]
        for detail_type in expected_types:
            assert detail_type in DETAIL_DESCRIPTIONS
            assert len(DETAIL_DESCRIPTIONS[detail_type]) > 0

    def test_descriptions_are_meaningful(self) -> None:
        """Test that descriptions are meaningful strings."""
        for detail_type, desc in DETAIL_DESCRIPTIONS.items():
            assert isinstance(desc, str)
            assert len(desc) >= 10  # Meaningful descriptions should be at least 10 chars
