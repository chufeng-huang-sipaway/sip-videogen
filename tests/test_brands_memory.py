"""Tests for brand memory access and context building functions."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from sip_videogen.advisor.tools import (
    _impl_browse_brand_assets as browse_brand_assets,
)
from sip_videogen.advisor.tools import (
    _impl_fetch_brand_detail as fetch_brand_detail,
)
from sip_videogen.brands.context import (
    DETAIL_DESCRIPTIONS,
    BrandContextBuilder,
    HierarchicalContextBuilder,
    ProductContextBuilder,
    ProjectContextBuilder,
    build_brand_context,
    build_product_context,
    build_project_context,
    build_turn_context,
)
from sip_videogen.brands.memory import (
    get_brand_detail,
    get_brand_summary,
    get_product_detail,
    get_product_full,
    get_product_images_for_generation,
    get_product_summary,
    get_project_detail,
    get_project_full,
    get_project_instructions,
    get_project_summary,
    list_brand_assets,
)
from sip_videogen.brands.models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIdentityFull,
    ColorDefinition,
    CompetitivePositioning,
    ProductAttribute,
    ProductFull,
    ProjectFull,
    ProjectStatus,
    VisualIdentity,
    VoiceGuidelines,
)
from sip_videogen.brands.storage import (
    create_brand,
    create_product,
    create_project,
    get_active_brand,
    set_active_brand,
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
    def test_set_and_get_active_brand(self,temp_brands_dir:Path,sample_brand_identity:BrandIdentityFull)->None:
        """Test setting and getting brand context."""
        create_brand(sample_brand_identity)
        set_active_brand("test-brand")
        assert get_active_brand()=="test-brand"
    def test_clear_brand_context(self,temp_brands_dir:Path,sample_brand_identity:BrandIdentityFull)->None:
        """Test clearing brand context."""
        create_brand(sample_brand_identity)
        set_active_brand("test-brand")
        set_active_brand(None)
        assert get_active_brand() is None
    def test_initial_context_is_none(self,temp_brands_dir:Path)->None:
        """Test that initial context is None."""
        set_active_brand(None)
        assert get_active_brand() is None


class TestFetchBrandDetailTool:
    """Tests for fetch_brand_detail tool function."""

    def test_returns_error_without_context(self) -> None:
        """Test that fetch_brand_detail returns error without brand context."""
        set_active_brand(None)

        result = fetch_brand_detail("visual_identity")

        assert result.startswith("Error:")
        assert "No brand context" in result

    def test_fetches_detail_with_context(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test fetching detail with brand context set."""
        create_brand(sample_brand_identity)
        set_active_brand("test-brand")

        result = fetch_brand_detail("visual_identity")

        # Should be valid JSON
        data = json.loads(result)
        assert "primary_colors" in data

    def test_set_active_brand_raises_for_nonexistent(self,temp_brands_dir:Path)->None:
        """Test that set_active_brand raises for nonexistent brand."""
        import pytest
        with pytest.raises(ValueError,match="not found"):
            set_active_brand("nonexistent")


class TestBrowseBrandAssetsTool:
    """Tests for browse_brand_assets tool function."""

    def test_returns_error_without_context(self) -> None:
        """Test that browse_brand_assets returns error without brand context."""
        set_active_brand(None)

        result = browse_brand_assets()

        assert result.startswith("Error:")
        assert "No brand context" in result

    def test_returns_no_assets_message(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that brand without assets returns appropriate message."""
        create_brand(sample_brand_identity)
        set_active_brand("test-brand")

        result = browse_brand_assets()

        assert "No assets found" in result

    def test_returns_json_with_assets(self, brand_with_assets: BrandIdentityFull) -> None:
        """Test that assets are returned as JSON."""
        set_active_brand("test-brand")

        result = browse_brand_assets()

        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 5  # logo(2) + marketing(1) + lifestyle(1) + generated(1)

    def test_filters_by_category(self, brand_with_assets: BrandIdentityFull) -> None:
        """Test that category filter works."""
        set_active_brand("test-brand")

        result = browse_brand_assets(category="logo")

        data = json.loads(result)
        assert len(data) == 2
        assert all(a["category"] == "logo" for a in data)

    def test_no_assets_with_category_filter(
        self, brand_with_assets: BrandIdentityFull
    ) -> None:
        """Test message when category has no assets."""
        set_active_brand("test-brand")

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


# ============================================================================
# Product Fixtures
# ============================================================================


@pytest.fixture
def sample_product() -> ProductFull:
    """Create a sample product for testing."""
    return ProductFull(
        slug="night-cream",
        name="Restorative Night Cream",
        description="A luxurious night cream that rejuvenates skin while you sleep.",
        images=[
            "products/night-cream/images/main.png",
            "products/night-cream/images/texture.png",
        ],
        primary_image="products/night-cream/images/main.png",
        attributes=[
            ProductAttribute(key="volume", value="50ml", category="measurements"),
            ProductAttribute(key="texture", value="Rich cream", category="texture"),
            ProductAttribute(key="key_ingredient", value="Retinol", category="ingredients"),
        ],
    )


@pytest.fixture
def brand_with_product(
    temp_brands_dir: Path,
    sample_brand_identity: BrandIdentityFull,
    sample_product: ProductFull,
):
    """Create a brand with a product for testing."""
    create_brand(sample_brand_identity)
    create_product("test-brand", sample_product)

    # Create actual image files
    brand_dir = temp_brands_dir / "test-brand"
    images_dir = brand_dir / "products" / "night-cream" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    (images_dir / "main.png").write_bytes(b"fake png")
    (images_dir / "texture.png").write_bytes(b"fake png")

    return sample_brand_identity


# ============================================================================
# Project Fixtures
# ============================================================================


@pytest.fixture
def sample_project() -> ProjectFull:
    """Create a sample project for testing."""
    return ProjectFull(
        slug="christmas-campaign",
        name="Christmas 2024 Campaign",
        status=ProjectStatus.ACTIVE,
        instructions="""# Christmas Campaign Guidelines

## Theme
- Use festive winter imagery
- Feature red and gold accent colors
- Include snowflakes and gift motifs

## Messaging
- Emphasize gift-giving and celebration
- Highlight limited-time holiday offers
- Use warm, inviting language
""",
    )


@pytest.fixture
def brand_with_project(
    temp_brands_dir: Path,
    sample_brand_identity: BrandIdentityFull,
    sample_project: ProjectFull,
):
    """Create a brand with a project for testing."""
    create_brand(sample_brand_identity)
    create_project("test-brand", sample_project)
    return sample_brand_identity


@pytest.fixture
def brand_with_product_and_project(
    temp_brands_dir: Path,
    sample_brand_identity: BrandIdentityFull,
    sample_product: ProductFull,
    sample_project: ProjectFull,
):
    """Create a brand with both a product and a project for testing."""
    create_brand(sample_brand_identity)
    create_product("test-brand", sample_product)
    create_project("test-brand", sample_project)

    # Create actual image files
    brand_dir = temp_brands_dir / "test-brand"
    images_dir = brand_dir / "products" / "night-cream" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    (images_dir / "main.png").write_bytes(b"fake png")
    (images_dir / "texture.png").write_bytes(b"fake png")

    return sample_brand_identity


# ============================================================================
# Tests for Product Memory Functions
# ============================================================================


class TestGetProductSummary:
    """Tests for get_product_summary function."""

    def test_returns_summary_for_existing_product(
        self, brand_with_product: BrandIdentityFull, sample_product: ProductFull
    ) -> None:
        """Test that get_product_summary returns a summary for an existing product."""
        summary = get_product_summary("test-brand", "night-cream")

        assert summary is not None
        assert summary.slug == "night-cream"
        assert summary.name == "Restorative Night Cream"
        assert "rejuvenates" in summary.description

    def test_returns_none_for_nonexistent_product(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that get_product_summary returns None for nonexistent product."""
        summary = get_product_summary("test-brand", "nonexistent")
        assert summary is None

    def test_returns_none_for_nonexistent_brand(
        self, temp_brands_dir: Path
    ) -> None:
        """Test that get_product_summary returns None for nonexistent brand."""
        summary = get_product_summary("nonexistent", "night-cream")
        assert summary is None


class TestGetProductDetail:
    """Tests for get_product_detail function."""

    def test_returns_json_for_existing_product(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that get_product_detail returns valid JSON."""
        result = get_product_detail("test-brand", "night-cream")

        data = json.loads(result)
        assert data["slug"] == "night-cream"
        assert data["name"] == "Restorative Night Cream"
        assert len(data["attributes"]) == 3

    def test_returns_error_for_nonexistent_product(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that get_product_detail returns error for nonexistent product."""
        result = get_product_detail("test-brand", "nonexistent")

        assert result.startswith("Error:")
        assert "not found" in result


class TestGetProductImagesForGeneration:
    """Tests for get_product_images_for_generation function."""

    def test_returns_brand_relative_paths(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that get_product_images_for_generation returns brand-relative paths."""
        images = get_product_images_for_generation("test-brand", "night-cream")

        assert len(images) == 2
        assert all(img.startswith("products/night-cream/images/") for img in images)

    def test_returns_empty_for_nonexistent_product(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that get_product_images_for_generation returns empty for nonexistent product."""
        images = get_product_images_for_generation("test-brand", "nonexistent")
        assert images == []


class TestGetProductFull:
    """Tests for get_product_full function."""

    def test_returns_full_product(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that get_product_full returns complete product."""
        product = get_product_full("test-brand", "night-cream")

        assert product is not None
        assert product.slug == "night-cream"
        assert len(product.images) == 2
        assert len(product.attributes) == 3

    def test_returns_none_for_nonexistent_product(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that get_product_full returns None for nonexistent product."""
        product = get_product_full("test-brand", "nonexistent")
        assert product is None


# ============================================================================
# Tests for Project Memory Functions
# ============================================================================


class TestGetProjectSummary:
    """Tests for get_project_summary function."""

    def test_returns_summary_for_existing_project(
        self, brand_with_project: BrandIdentityFull, sample_project: ProjectFull
    ) -> None:
        """Test that get_project_summary returns a summary for an existing project."""
        summary = get_project_summary("test-brand", "christmas-campaign")

        assert summary is not None
        assert summary.slug == "christmas-campaign"
        assert summary.name == "Christmas 2024 Campaign"
        assert summary.status == ProjectStatus.ACTIVE

    def test_returns_none_for_nonexistent_project(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that get_project_summary returns None for nonexistent project."""
        summary = get_project_summary("test-brand", "nonexistent")
        assert summary is None


class TestGetProjectInstructions:
    """Tests for get_project_instructions function."""

    def test_returns_instructions_markdown(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that get_project_instructions returns markdown."""
        instructions = get_project_instructions("test-brand", "christmas-campaign")

        assert "# Christmas Campaign Guidelines" in instructions
        assert "festive winter imagery" in instructions

    def test_returns_error_for_nonexistent_project(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that get_project_instructions returns error for nonexistent project."""
        result = get_project_instructions("test-brand", "nonexistent")

        assert result.startswith("Error:")
        assert "not found" in result


class TestGetProjectDetail:
    """Tests for get_project_detail function."""

    def test_returns_json_for_existing_project(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that get_project_detail returns valid JSON."""
        result = get_project_detail("test-brand", "christmas-campaign")

        data = json.loads(result)
        assert data["slug"] == "christmas-campaign"
        assert data["name"] == "Christmas 2024 Campaign"
        assert "Guidelines" in data["instructions"]

    def test_returns_error_for_nonexistent_project(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that get_project_detail returns error for nonexistent project."""
        result = get_project_detail("test-brand", "nonexistent")

        assert result.startswith("Error:")
        assert "not found" in result


class TestGetProjectFull:
    """Tests for get_project_full function."""

    def test_returns_full_project(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that get_project_full returns complete project."""
        project = get_project_full("test-brand", "christmas-campaign")

        assert project is not None
        assert project.slug == "christmas-campaign"
        assert "Guidelines" in project.instructions

    def test_returns_none_for_nonexistent_project(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that get_project_full returns None for nonexistent project."""
        project = get_project_full("test-brand", "nonexistent")
        assert project is None


# ============================================================================
# Tests for Product Context Builder
# ============================================================================


class TestProductContextBuilder:
    """Tests for ProductContextBuilder class."""

    def test_raises_for_nonexistent_product(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that ProductContextBuilder raises ValueError for nonexistent product."""
        with pytest.raises(ValueError, match="not found"):
            ProductContextBuilder("test-brand", "nonexistent")

    def test_raises_for_nonexistent_brand(self, temp_brands_dir: Path) -> None:
        """Test that ProductContextBuilder raises ValueError for nonexistent brand."""
        with pytest.raises(ValueError, match="not found"):
            ProductContextBuilder("nonexistent", "night-cream")

    def test_builds_context_with_product_info(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that context includes product information."""
        builder = ProductContextBuilder("test-brand", "night-cream")
        context = builder.build_context_section()

        assert "Restorative Night Cream" in context
        assert "night-cream" in context
        assert "rejuvenates" in context

    def test_includes_attributes(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that context includes product attributes."""
        builder = ProductContextBuilder("test-brand", "night-cream")
        context = builder.build_context_section()

        assert "volume" in context
        assert "50ml" in context
        assert "Retinol" in context

    def test_includes_images_with_primary_marker(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that context includes images with primary marker."""
        builder = ProductContextBuilder("test-brand", "night-cream")
        context = builder.build_context_section()

        assert "products/night-cream/images/main.png" in context
        assert "[PRIMARY - use as reference]" in context


class TestBuildProductContext:
    """Tests for build_product_context convenience function."""

    def test_returns_context_for_existing_product(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that build_product_context returns context for existing product."""
        context = build_product_context("test-brand", "night-cream")

        assert "Restorative Night Cream" in context
        assert "Error:" not in context

    def test_returns_error_for_nonexistent_product(
        self, brand_with_product: BrandIdentityFull
    ) -> None:
        """Test that build_product_context returns error for nonexistent product."""
        context = build_product_context("test-brand", "nonexistent")

        assert "Error:" in context
        assert "not found" in context


# ============================================================================
# Tests for Project Context Builder
# ============================================================================


class TestProjectContextBuilder:
    """Tests for ProjectContextBuilder class."""

    def test_raises_for_nonexistent_project(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that ProjectContextBuilder raises ValueError for nonexistent project."""
        with pytest.raises(ValueError, match="not found"):
            ProjectContextBuilder("test-brand", "nonexistent")

    def test_raises_for_nonexistent_brand(self, temp_brands_dir: Path) -> None:
        """Test that ProjectContextBuilder raises ValueError for nonexistent brand."""
        with pytest.raises(ValueError, match="not found"):
            ProjectContextBuilder("nonexistent", "christmas-campaign")

    def test_builds_context_with_project_info(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that context includes project information."""
        builder = ProjectContextBuilder("test-brand", "christmas-campaign")
        context = builder.build_context_section()

        assert "Christmas 2024 Campaign" in context
        assert "christmas-campaign" in context
        assert "active" in context.lower()

    def test_includes_instructions(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that context includes project instructions."""
        builder = ProjectContextBuilder("test-brand", "christmas-campaign")
        context = builder.build_context_section()

        assert "festive winter imagery" in context
        assert "red and gold" in context


class TestBuildProjectContext:
    """Tests for build_project_context convenience function."""

    def test_returns_context_for_existing_project(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that build_project_context returns context for existing project."""
        context = build_project_context("test-brand", "christmas-campaign")

        assert "Christmas 2024 Campaign" in context
        assert "Error:" not in context

    def test_returns_error_for_nonexistent_project(
        self, brand_with_project: BrandIdentityFull
    ) -> None:
        """Test that build_project_context returns error for nonexistent project."""
        context = build_project_context("test-brand", "nonexistent")

        assert "Error:" in context
        assert "not found" in context


# ============================================================================
# Tests for Hierarchical Context Builder
# ============================================================================


class TestHierarchicalContextBuilder:
    """Tests for HierarchicalContextBuilder class."""

    def test_returns_empty_without_project_or_products(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that builder returns empty string without project or products."""
        builder = HierarchicalContextBuilder("test-brand")
        context = builder.build_turn_context()

        assert context == ""

    def test_includes_project_context(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that builder includes project context when project is active."""
        builder = HierarchicalContextBuilder(
            "test-brand", project_slug="christmas-campaign"
        )
        context = builder.build_turn_context()

        assert "Christmas 2024 Campaign" in context
        assert "festive winter imagery" in context

    def test_includes_product_context(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that builder includes product context when products are attached."""
        builder = HierarchicalContextBuilder(
            "test-brand", product_slugs=["night-cream"]
        )
        context = builder.build_turn_context()

        assert "Restorative Night Cream" in context
        assert "Attached Product" in context

    def test_includes_both_project_and_products(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that builder includes both project and products."""
        builder = HierarchicalContextBuilder(
            "test-brand",
            product_slugs=["night-cream"],
            project_slug="christmas-campaign",
        )
        context = builder.build_turn_context()

        assert "Christmas 2024 Campaign" in context
        assert "Restorative Night Cream" in context
        assert "---" in context  # Separator between sections

    def test_project_comes_before_products(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that project context comes before product context."""
        builder = HierarchicalContextBuilder(
            "test-brand",
            product_slugs=["night-cream"],
            project_slug="christmas-campaign",
        )
        context = builder.build_turn_context()

        project_pos = context.find("Christmas 2024 Campaign")
        product_pos = context.find("Restorative Night Cream")

        assert project_pos < product_pos

    def test_skips_nonexistent_project(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that builder skips nonexistent project silently."""
        builder = HierarchicalContextBuilder(
            "test-brand",
            product_slugs=["night-cream"],
            project_slug="nonexistent",
        )
        context = builder.build_turn_context()

        # Should still include product
        assert "Restorative Night Cream" in context
        # But no project
        assert "nonexistent" not in context

    def test_skips_nonexistent_product(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that builder skips nonexistent products silently."""
        builder = HierarchicalContextBuilder(
            "test-brand",
            product_slugs=["night-cream", "nonexistent"],
            project_slug="christmas-campaign",
        )
        context = builder.build_turn_context()

        # Should include existing product
        assert "Restorative Night Cream" in context
        # Should include project
        assert "Christmas 2024 Campaign" in context


class TestBuildTurnContext:
    """Tests for build_turn_context convenience function."""

    def test_returns_empty_without_project_or_products(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that build_turn_context returns empty without project or products."""
        context = build_turn_context("test-brand")
        assert context == ""

    def test_returns_context_with_project(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that build_turn_context returns context with project."""
        context = build_turn_context(
            "test-brand", project_slug="christmas-campaign"
        )

        assert "Christmas 2024 Campaign" in context

    def test_returns_context_with_products(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that build_turn_context returns context with products."""
        context = build_turn_context(
            "test-brand", product_slugs=["night-cream"]
        )

        assert "Restorative Night Cream" in context

    def test_returns_combined_context(
        self, brand_with_product_and_project: BrandIdentityFull
    ) -> None:
        """Test that build_turn_context returns combined context."""
        context = build_turn_context(
            "test-brand",
            product_slugs=["night-cream"],
            project_slug="christmas-campaign",
        )

        assert "Christmas 2024 Campaign" in context
        assert "Restorative Night Cream" in context
