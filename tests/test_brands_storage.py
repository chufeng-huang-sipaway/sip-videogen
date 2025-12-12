"""Tests for brand storage functions."""

from pathlib import Path
from unittest.mock import patch

import pytest

from sip_videogen.brands.models import (
    BrandCoreIdentity,
    BrandIdentityFull,
    BrandIndex,
    BrandIndexEntry,
    ColorDefinition,
    CompetitivePositioning,
    VisualIdentity,
    VoiceGuidelines,
)
from sip_videogen.brands.storage import (
    create_brand,
    delete_brand,
    get_active_brand,
    get_brand_dir,
    get_brands_dir,
    get_index_path,
    list_brands,
    load_brand,
    load_brand_summary,
    load_index,
    save_brand,
    save_index,
    set_active_brand,
    slugify,
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
    )
    identity.voice = VoiceGuidelines(
        tone_attributes=["friendly", "clear", "helpful"],
    )
    identity.visual = VisualIdentity(
        primary_colors=[
            ColorDefinition(hex="#FF5733", name="Vibrant Orange"),
            ColorDefinition(hex="#2E86AB", name="Ocean Blue"),
        ],
        overall_aesthetic="Clean and modern with bold accents",
    )
    return identity


@pytest.fixture
def another_brand_identity() -> BrandIdentityFull:
    """Create another sample brand identity for testing multiple brands."""
    identity = BrandIdentityFull(slug="another-brand")
    identity.core = BrandCoreIdentity(
        name="Another Brand",
        tagline="Another great product",
    )
    identity.positioning = CompetitivePositioning(
        market_category="Consumer Goods",
    )
    return identity


class TestSlugify:
    """Tests for slugify function."""

    def test_simple_name(self) -> None:
        """Test slugifying a simple name with spaces."""
        assert slugify("Summit Coffee") == "summit-coffee"

    def test_name_with_dots(self) -> None:
        """Test slugifying a name with dots."""
        assert slugify("Summit Coffee Co.") == "summit-coffee-co"

    def test_camel_case(self) -> None:
        """Test slugifying CamelCase names."""
        assert slugify("EternaCare") == "eternacare"

    def test_special_characters(self) -> None:
        """Test slugifying a name with special characters."""
        assert slugify("Test & Brand!") == "test-brand"

    def test_multiple_spaces(self) -> None:
        """Test slugifying a name with multiple spaces."""
        assert slugify("Summit    Coffee") == "summit-coffee"

    def test_leading_trailing_spaces(self) -> None:
        """Test slugifying a name with leading/trailing spaces."""
        assert slugify("  Summit Coffee  ") == "summit-coffee"

    def test_hyphens_preserved(self) -> None:
        """Test that existing hyphens are preserved."""
        assert slugify("Summit-Coffee") == "summit-coffee"

    def test_numbers_preserved(self) -> None:
        """Test that numbers are preserved."""
        assert slugify("Brand 2024") == "brand-2024"

    def test_empty_string(self) -> None:
        """Test slugifying an empty string."""
        assert slugify("") == ""


class TestPathHelpers:
    """Tests for path helper functions."""

    def test_get_brands_dir(self) -> None:
        """Test get_brands_dir returns correct path."""
        brands_dir = get_brands_dir()
        assert brands_dir == Path.home() / ".sip-videogen" / "brands"

    def test_get_brand_dir(self) -> None:
        """Test get_brand_dir returns correct path for a brand."""
        brand_dir = get_brand_dir("test-brand")
        assert brand_dir == Path.home() / ".sip-videogen" / "brands" / "test-brand"

    def test_get_index_path(self) -> None:
        """Test get_index_path returns correct path."""
        index_path = get_index_path()
        assert index_path == Path.home() / ".sip-videogen" / "brands" / "index.json"


class TestIndexManagement:
    """Tests for index load/save functions."""

    def test_load_index_creates_new_if_not_exists(self, temp_brands_dir: Path) -> None:
        """Test that load_index creates a new empty index if file doesn't exist."""
        index = load_index()
        assert isinstance(index, BrandIndex)
        assert len(index.brands) == 0
        assert index.active_brand is None

    def test_save_and_load_index(self, temp_brands_dir: Path) -> None:
        """Test saving and loading an index."""
        # Create and save an index with a brand
        entry = BrandIndexEntry(slug="test-brand", name="Test Brand")
        index = BrandIndex(brands=[entry], active_brand="test-brand")
        save_index(index)

        # Verify file was created
        index_path = temp_brands_dir / "index.json"
        assert index_path.exists()

        # Load and verify
        loaded_index = load_index()
        assert len(loaded_index.brands) == 1
        assert loaded_index.brands[0].slug == "test-brand"
        assert loaded_index.active_brand == "test-brand"

    def test_load_index_handles_invalid_json(self, temp_brands_dir: Path) -> None:
        """Test that load_index handles invalid JSON gracefully."""
        index_path = temp_brands_dir / "index.json"
        index_path.write_text("not valid json")

        index = load_index()
        assert isinstance(index, BrandIndex)
        assert len(index.brands) == 0


class TestBrandCRUD:
    """Tests for brand CRUD operations."""

    def test_create_brand(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test creating a new brand."""
        summary = create_brand(sample_brand_identity)

        assert summary.slug == "test-brand"
        assert summary.name == "Test Brand"
        assert summary.tagline == "Testing made easy"
        assert summary.category == "Testing Tools"
        assert (temp_brands_dir / "test-brand" / "identity.json").exists()
        assert (temp_brands_dir / "test-brand" / "identity_full.json").exists()

    def test_create_brand_creates_directory_structure(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that create_brand creates the correct directory structure."""
        create_brand(sample_brand_identity)

        brand_dir = temp_brands_dir / "test-brand"
        assert (brand_dir / "assets").is_dir()
        assert (brand_dir / "assets" / "logo").is_dir()
        assert (brand_dir / "assets" / "packaging").is_dir()
        assert (brand_dir / "assets" / "lifestyle").is_dir()
        assert (brand_dir / "assets" / "mascot").is_dir()
        assert (brand_dir / "assets" / "marketing").is_dir()
        assert (brand_dir / "history").is_dir()

    def test_create_brand_updates_index(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that create_brand updates the brand index."""
        create_brand(sample_brand_identity)

        index = load_index()
        assert len(index.brands) == 1
        assert index.brands[0].slug == "test-brand"
        assert index.brands[0].name == "Test Brand"

    def test_create_duplicate_raises(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that creating a duplicate brand raises ValueError."""
        create_brand(sample_brand_identity)

        with pytest.raises(ValueError, match="already exists"):
            create_brand(sample_brand_identity)

    def test_load_brand(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test loading a brand."""
        create_brand(sample_brand_identity)

        loaded = load_brand("test-brand")

        assert loaded is not None
        assert loaded.slug == "test-brand"
        assert loaded.core.name == "Test Brand"
        assert loaded.core.tagline == "Testing made easy"
        assert loaded.positioning.market_category == "Testing Tools"

    def test_load_brand_updates_last_accessed(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that loading a brand updates its last_accessed timestamp."""
        create_brand(sample_brand_identity)

        # Get initial last_accessed
        index = load_index()
        initial_accessed = index.get_brand("test-brand").last_accessed

        # Load the brand
        load_brand("test-brand")

        # Check last_accessed was updated
        index = load_index()
        new_accessed = index.get_brand("test-brand").last_accessed
        assert new_accessed >= initial_accessed

    def test_load_nonexistent_returns_none(self, temp_brands_dir: Path) -> None:
        """Test that loading nonexistent brand returns None."""
        assert load_brand("nonexistent") is None

    def test_load_brand_summary(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test loading just the brand summary (L0 layer)."""
        create_brand(sample_brand_identity)

        summary = load_brand_summary("test-brand")

        assert summary is not None
        assert summary.slug == "test-brand"
        assert summary.name == "Test Brand"
        assert summary.tagline == "Testing made easy"
        assert summary.category == "Testing Tools"
        assert "friendly" in summary.tone

    def test_load_brand_summary_nonexistent(self, temp_brands_dir: Path) -> None:
        """Test that loading summary of nonexistent brand returns None."""
        assert load_brand_summary("nonexistent") is None

    def test_save_brand_updates_existing(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test updating an existing brand."""
        create_brand(sample_brand_identity)

        # Modify and save
        sample_brand_identity.core.tagline = "Updated tagline"
        summary = save_brand(sample_brand_identity)

        assert summary.tagline == "Updated tagline"

        # Verify persistence
        loaded = load_brand("test-brand")
        assert loaded.core.tagline == "Updated tagline"

    def test_save_brand_creates_if_not_exists(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that save_brand creates a new brand if it doesn't exist."""
        # Save without creating first
        summary = save_brand(sample_brand_identity)

        assert summary.slug == "test-brand"
        assert (temp_brands_dir / "test-brand" / "identity.json").exists()

    def test_save_brand_updates_index(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that save_brand updates the brand index."""
        create_brand(sample_brand_identity)

        # Modify name and save
        sample_brand_identity.core.name = "Updated Brand Name"
        save_brand(sample_brand_identity)

        index = load_index()
        entry = index.get_brand("test-brand")
        assert entry.name == "Updated Brand Name"

    def test_delete_brand(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test deleting a brand."""
        create_brand(sample_brand_identity)

        result = delete_brand("test-brand")

        assert result is True
        assert not (temp_brands_dir / "test-brand").exists()
        assert load_brand("test-brand") is None

    def test_delete_brand_updates_index(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that delete_brand updates the brand index."""
        create_brand(sample_brand_identity)

        delete_brand("test-brand")

        index = load_index()
        assert len(index.brands) == 0

    def test_delete_nonexistent_returns_false(self, temp_brands_dir: Path) -> None:
        """Test that deleting nonexistent brand returns False."""
        result = delete_brand("nonexistent")
        assert result is False

    def test_list_brands(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        another_brand_identity: BrandIdentityFull,
    ) -> None:
        """Test listing brands."""
        create_brand(sample_brand_identity)
        create_brand(another_brand_identity)

        brands = list_brands()

        assert len(brands) == 2
        slugs = [b.slug for b in brands]
        assert "test-brand" in slugs
        assert "another-brand" in slugs

    def test_list_brands_sorted_by_last_accessed(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        another_brand_identity: BrandIdentityFull,
    ) -> None:
        """Test that list_brands returns brands sorted by last_accessed."""
        create_brand(sample_brand_identity)
        create_brand(another_brand_identity)

        # Load the first brand to update its last_accessed
        load_brand("test-brand")

        brands = list_brands()

        # Most recently accessed should be first
        assert brands[0].slug == "test-brand"

    def test_list_brands_empty(self, temp_brands_dir: Path) -> None:
        """Test listing brands when none exist."""
        brands = list_brands()
        assert brands == []


class TestActiveBrand:
    """Tests for active brand management."""

    def test_get_active_brand_initially_none(self, temp_brands_dir: Path) -> None:
        """Test that active brand is initially None."""
        assert get_active_brand() is None

    def test_set_and_get_active_brand(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test setting and getting active brand."""
        create_brand(sample_brand_identity)

        set_active_brand("test-brand")

        assert get_active_brand() == "test-brand"

    def test_set_nonexistent_raises(self, temp_brands_dir: Path) -> None:
        """Test that setting nonexistent brand raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            set_active_brand("nonexistent")

    def test_clear_active_brand(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test clearing active brand by setting to None."""
        create_brand(sample_brand_identity)
        set_active_brand("test-brand")

        set_active_brand(None)

        assert get_active_brand() is None

    def test_delete_active_brand_clears_active(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that deleting the active brand clears the active setting."""
        create_brand(sample_brand_identity)
        set_active_brand("test-brand")

        delete_brand("test-brand")

        assert get_active_brand() is None


class TestBrandToSummaryConversion:
    """Tests for BrandIdentityFull.to_summary() method."""

    def test_to_summary_extracts_core_fields(
        self, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that to_summary extracts core identity fields."""
        summary = sample_brand_identity.to_summary()

        assert summary.slug == "test-brand"
        assert summary.name == "Test Brand"
        assert summary.tagline == "Testing made easy"

    def test_to_summary_extracts_category(self, sample_brand_identity: BrandIdentityFull) -> None:
        """Test that to_summary extracts category from positioning."""
        summary = sample_brand_identity.to_summary()
        assert summary.category == "Testing Tools"

    def test_to_summary_extracts_tone(self, sample_brand_identity: BrandIdentityFull) -> None:
        """Test that to_summary extracts tone from voice guidelines."""
        summary = sample_brand_identity.to_summary()
        # Should have "friendly, clear, helpful" joined
        assert "friendly" in summary.tone
        assert "clear" in summary.tone
        assert "helpful" in summary.tone

    def test_to_summary_extracts_primary_colors(
        self, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that to_summary extracts primary colors."""
        summary = sample_brand_identity.to_summary()
        assert "#FF5733" in summary.primary_colors
        assert "#2E86AB" in summary.primary_colors

    def test_to_summary_limits_colors_to_three(
        self, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that to_summary limits colors to 3."""
        # Add more colors
        sample_brand_identity.visual.primary_colors = [
            ColorDefinition(hex="#000001", name="Color 1"),
            ColorDefinition(hex="#000002", name="Color 2"),
            ColorDefinition(hex="#000003", name="Color 3"),
            ColorDefinition(hex="#000004", name="Color 4"),
            ColorDefinition(hex="#000005", name="Color 5"),
        ]

        summary = sample_brand_identity.to_summary()
        assert len(summary.primary_colors) == 3

    def test_to_summary_handles_empty_category(self) -> None:
        """Test that to_summary uses 'Uncategorized' for empty category."""
        identity = BrandIdentityFull(slug="minimal")
        summary = identity.to_summary()
        assert summary.category == "Uncategorized"

    def test_to_summary_handles_empty_visual(self) -> None:
        """Test that to_summary handles empty visual fields."""
        identity = BrandIdentityFull(slug="minimal")
        summary = identity.to_summary()
        assert summary.primary_colors == []
        assert summary.visual_style == ""
