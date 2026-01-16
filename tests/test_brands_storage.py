"""Tests for brand storage functions."""

from pathlib import Path
from unittest.mock import patch

import pytest

from sip_studio.brands.models import (
    BrandCoreIdentity,
    BrandIdentityFull,
    BrandIndex,
    BrandIndexEntry,
    ColorDefinition,
    CompetitivePositioning,
    ProductAttribute,
    ProductFull,
    ProjectFull,
    ProjectStatus,
    VisualIdentity,
    VoiceGuidelines,
)
from sip_studio.brands.storage import (
    add_product_image,
    count_project_assets,
    create_brand,
    create_product,
    create_project,
    delete_brand,
    delete_product,
    delete_product_image,
    delete_project,
    get_active_brand,
    get_active_project,
    get_brand_dir,
    get_brands_dir,
    get_index_path,
    get_product_dir,
    get_products_dir,
    get_project_dir,
    get_projects_dir,
    list_brands,
    list_product_images,
    list_products,
    list_project_assets,
    list_projects,
    load_brand,
    load_brand_summary,
    load_index,
    load_product,
    load_product_index,
    load_product_summary,
    load_project,
    load_project_index,
    load_project_summary,
    save_brand,
    save_index,
    save_product,
    save_product_index,
    save_project,
    save_project_index,
    set_active_brand,
    set_active_project,
    set_primary_product_image,
    slugify,
)


@pytest.fixture
def temp_brands_dir(tmp_path: Path):
    """Create a temporary brands directory for testing."""
    brands_dir = tmp_path / ".sip-studio" / "brands"
    brands_dir.mkdir(parents=True)
    # Patch the base module where get_brands_dir is defined
    with patch("sip_studio.brands.storage.base.get_brands_dir", return_value=brands_dir):
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
        assert brands_dir == Path.home() / ".sip-studio" / "brands"

    def test_get_brand_dir(self) -> None:
        """Test get_brand_dir returns correct path for a brand."""
        brand_dir = get_brand_dir("test-brand")
        assert brand_dir == Path.home() / ".sip-studio" / "brands" / "test-brand"

    def test_get_index_path(self) -> None:
        """Test get_index_path returns correct path."""
        index_path = get_index_path()
        assert index_path == Path.home() / ".sip-studio" / "brands" / "index.json"


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


# =============================================================================
# Product Storage Tests
# =============================================================================


@pytest.fixture
def sample_product() -> ProductFull:
    """Create a sample product for testing."""
    return ProductFull(
        slug="night-cream",
        name="Restorative Night Cream",
        description="A luxurious night cream that repairs and hydrates skin.",
        images=[],
        primary_image="",
        attributes=[
            ProductAttribute(key="size", value="50ml", category="measurements"),
            ProductAttribute(key="texture", value="rich cream", category="texture"),
        ],
    )


@pytest.fixture
def another_product() -> ProductFull:
    """Create another sample product for testing."""
    return ProductFull(
        slug="day-serum",
        name="Brightening Day Serum",
        description="A lightweight serum for daily use.",
    )


class TestProductPathHelpers:
    """Tests for product path helper functions."""

    def test_get_products_dir(self) -> None:
        """Test get_products_dir returns correct path."""
        products_dir = get_products_dir("test-brand")
        expected = Path.home() / ".sip-studio" / "brands" / "test-brand" / "products"
        assert products_dir == expected

    def test_get_product_dir(self) -> None:
        """Test get_product_dir returns correct path."""
        product_dir = get_product_dir("test-brand", "night-cream")
        expected = (
            Path.home() / ".sip-studio" / "brands" / "test-brand" / "products" / "night-cream"
        )
        assert product_dir == expected


class TestProductIndexManagement:
    """Tests for product index load/save functions."""

    def test_load_product_index_creates_new(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that load_product_index creates empty index if not exists."""
        create_brand(sample_brand_identity)
        index = load_product_index("test-brand")
        assert len(index.products) == 0

    def test_save_and_load_product_index(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test saving and loading a product index."""
        create_brand(sample_brand_identity)

        from sip_studio.brands.models import ProductIndex, ProductSummary

        summary = ProductSummary(slug="test-product", name="Test Product", description="Test")
        index = ProductIndex(products=[summary])
        save_product_index("test-brand", index)

        loaded = load_product_index("test-brand")
        assert len(loaded.products) == 1
        assert loaded.products[0].slug == "test-product"


class TestProductCRUD:
    """Tests for product CRUD operations."""

    def test_create_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test creating a new product."""
        create_brand(sample_brand_identity)
        summary = create_product("test-brand", sample_product)

        assert summary.slug == "night-cream"
        assert summary.name == "Restorative Night Cream"
        assert summary.attribute_count == 2

        # Verify files created
        product_dir = temp_brands_dir / "test-brand" / "products" / "night-cream"
        assert (product_dir / "product.json").exists()
        assert (product_dir / "product_full.json").exists()
        assert (product_dir / "images").is_dir()

    def test_create_product_brand_not_found(
        self, temp_brands_dir: Path, sample_product: ProductFull
    ) -> None:
        """Test creating product for nonexistent brand raises error."""
        with pytest.raises(ValueError, match="Brand .* not found"):
            create_product("nonexistent", sample_product)

    def test_create_duplicate_product_raises(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test creating duplicate product raises error."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)

        with pytest.raises(ValueError, match="already exists"):
            create_product("test-brand", sample_product)

    def test_load_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test loading a product."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)

        loaded = load_product("test-brand", "night-cream")

        assert loaded is not None
        assert loaded.slug == "night-cream"
        assert loaded.name == "Restorative Night Cream"
        assert len(loaded.attributes) == 2

    def test_load_product_not_found(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test loading nonexistent product returns None."""
        create_brand(sample_brand_identity)
        assert load_product("test-brand", "nonexistent") is None

    def test_load_product_summary(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test loading just the product summary."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)

        summary = load_product_summary("test-brand", "night-cream")

        assert summary is not None
        assert summary.slug == "night-cream"
        assert summary.attribute_count == 2

    def test_save_product_updates_existing(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test updating an existing product."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)

        sample_product.description = "Updated description"
        save_product("test-brand", sample_product)

        loaded = load_product("test-brand", "night-cream")
        assert loaded.description == "Updated description"

    def test_save_product_creates_if_not_exists(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test that save_product creates product if not exists."""
        create_brand(sample_brand_identity)
        summary = save_product("test-brand", sample_product)

        assert summary.slug == "night-cream"
        assert load_product("test-brand", "night-cream") is not None

    def test_delete_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test deleting a product."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)

        result = delete_product("test-brand", "night-cream")

        assert result is True
        assert load_product("test-brand", "night-cream") is None

        # Verify index updated
        index = load_product_index("test-brand")
        assert len(index.products) == 0

    def test_delete_product_not_found(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test deleting nonexistent product returns False."""
        create_brand(sample_brand_identity)
        assert delete_product("test-brand", "nonexistent") is False

    def test_list_products(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
        another_product: ProductFull,
    ) -> None:
        """Test listing products for a brand."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        create_product("test-brand", another_product)

        products = list_products("test-brand")

        assert len(products) == 2
        slugs = [p.slug for p in products]
        assert "night-cream" in slugs
        assert "day-serum" in slugs

    def test_list_products_sorted_by_name(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
        another_product: ProductFull,
    ) -> None:
        """Test that list_products returns products sorted by name."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)  # Restorative Night Cream
        create_product("test-brand", another_product)  # Brightening Day Serum

        products = list_products("test-brand")

        # Brightening comes before Restorative alphabetically
        assert products[0].name == "Brightening Day Serum"
        assert products[1].name == "Restorative Night Cream"


class TestProductImages:
    """Tests for product image management."""

    def test_add_product_image(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test adding an image to a product."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)

        # Add an image
        image_data = b"fake image data"
        path = add_product_image("test-brand", "night-cream", "main.png", image_data)

        assert path == "products/night-cream/images/main.png"

        # Verify file exists
        image_file = (
            temp_brands_dir / "test-brand" / "products" / "night-cream" / "images" / "main.png"
        )
        assert image_file.exists()
        assert image_file.read_bytes() == image_data

        # Verify product updated
        product = load_product("test-brand", "night-cream")
        assert path in product.images
        assert product.primary_image == path  # First image becomes primary

    def test_add_product_image_product_not_found(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test adding image to nonexistent product raises error."""
        create_brand(sample_brand_identity)

        with pytest.raises(ValueError, match="not found"):
            add_product_image("test-brand", "nonexistent", "main.png", b"data")

    def test_delete_product_image(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test deleting an image from a product."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        add_product_image("test-brand", "night-cream", "main.png", b"data")

        result = delete_product_image("test-brand", "night-cream", "main.png")

        assert result is True

        # Verify file deleted
        image_file = (
            temp_brands_dir / "test-brand" / "products" / "night-cream" / "images" / "main.png"
        )
        assert not image_file.exists()

        # Verify product updated
        product = load_product("test-brand", "night-cream")
        assert "products/night-cream/images/main.png" not in product.images
        assert product.primary_image == ""

    def test_delete_product_image_not_found(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test deleting nonexistent image returns False."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)

        assert delete_product_image("test-brand", "night-cream", "nonexistent.png") is False

    def test_list_product_images(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test listing images for a product."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        add_product_image("test-brand", "night-cream", "main.png", b"data1")
        add_product_image("test-brand", "night-cream", "detail.jpg", b"data2")

        images = list_product_images("test-brand", "night-cream")

        assert len(images) == 2
        assert "products/night-cream/images/detail.jpg" in images
        assert "products/night-cream/images/main.png" in images

    def test_set_primary_product_image(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test setting the primary image for a product."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        add_product_image("test-brand", "night-cream", "main.png", b"data1")
        add_product_image("test-brand", "night-cream", "detail.png", b"data2")

        result = set_primary_product_image(
            "test-brand", "night-cream", "products/night-cream/images/detail.png"
        )

        assert result is True
        product = load_product("test-brand", "night-cream")
        assert product.primary_image == "products/night-cream/images/detail.png"

    def test_set_primary_image_not_in_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Test setting primary to image not in product returns False."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)

        result = set_primary_product_image(
            "test-brand", "night-cream", "products/night-cream/images/nonexistent.png"
        )

        assert result is False


# =============================================================================
# Packaging Text Model Tests
# =============================================================================


class TestPackagingTextModels:
    """Tests for PackagingTextElement and PackagingTextDescription models."""

    def test_packaging_text_element_minimal(self) -> None:
        """Test PackagingTextElement with only required field."""
        from sip_studio.brands.models import PackagingTextElement

        elem = PackagingTextElement(text="SUMMIT")
        assert elem.text == "SUMMIT"
        assert elem.notes == ""
        assert elem.role == "other"
        assert elem.typography == ""
        assert elem.size == ""
        assert elem.color == ""
        assert elem.position == ""
        assert elem.emphasis == ""

    def test_packaging_text_element_full(self) -> None:
        """Test PackagingTextElement with all fields populated."""
        from sip_studio.brands.models import PackagingTextElement

        elem = PackagingTextElement(
            text="SUMMIT COFFEE",
            notes="letter O not zero",
            role="brand_name",
            typography="sans-serif",
            size="large",
            color="white",
            position="front-center",
            emphasis="all-caps",
        )
        assert elem.text == "SUMMIT COFFEE"
        assert elem.notes == "letter O not zero"
        assert elem.role == "brand_name"
        assert elem.typography == "sans-serif"
        assert elem.size == "large"
        assert elem.color == "white"
        assert elem.position == "front-center"
        assert elem.emphasis == "all-caps"

    def test_packaging_text_description_empty(self) -> None:
        """Test PackagingTextDescription with no elements (analyzed, no text found)."""
        from sip_studio.brands.models import PackagingTextDescription

        desc = PackagingTextDescription()
        assert desc.summary == ""
        assert desc.elements == []
        assert desc.layout_notes == ""
        assert desc.source_image == ""
        assert desc.generated_at is None
        assert desc.edited_at is None
        assert desc.is_human_edited is False

    def test_packaging_text_description_populated(self) -> None:
        """Test PackagingTextDescription with elements."""
        from datetime import datetime

        from sip_studio.brands.models import PackagingTextDescription, PackagingTextElement

        now = datetime.utcnow()
        desc = PackagingTextDescription(
            summary="Brand name centered, tagline below",
            elements=[
                PackagingTextElement(text="SUMMIT", role="brand_name"),
                PackagingTextElement(text="PREMIUM ROAST", role="tagline"),
            ],
            layout_notes="Vertical hierarchy",
            source_image="products/coffee/images/bag.png",
            generated_at=now,
            is_human_edited=False,
        )
        assert len(desc.elements) == 2
        assert desc.elements[0].text == "SUMMIT"
        assert desc.elements[1].role == "tagline"
        assert desc.source_image == "products/coffee/images/bag.png"
        assert desc.generated_at == now

    def test_product_full_backward_compatibility(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test ProductFull loads without packaging_text field (backward compat)."""
        import json

        create_brand(sample_brand_identity)
        # Create product dir
        prod_dir = temp_brands_dir / "test-brand" / "products" / "legacy-product"
        prod_dir.mkdir(parents=True)
        # Write product_full.json WITHOUT packaging_text field
        legacy_data = {
            "slug": "legacy-product",
            "name": "Legacy Product",
            "description": "A product from before packaging_text existed",
            "images": [],
            "primary_image": "",
            "attributes": [],
        }
        (prod_dir / "product_full.json").write_text(json.dumps(legacy_data))
        # Load and verify
        product = load_product("test-brand", "legacy-product")
        assert product is not None
        assert product.slug == "legacy-product"
        assert product.packaging_text is None

    def test_to_summary_sets_has_packaging_text_true(self) -> None:
        """Test to_summary() sets has_packaging_text=True when packaging_text exists."""
        from sip_studio.brands.models import PackagingTextDescription, PackagingTextElement

        product = ProductFull(
            slug="test-product",
            name="Test Product",
            description="Test",
            packaging_text=PackagingTextDescription(elements=[PackagingTextElement(text="TEST")]),
        )
        summary = product.to_summary()
        assert summary.has_packaging_text is True

    def test_to_summary_sets_has_packaging_text_false(self) -> None:
        """Test to_summary() sets has_packaging_text=False when packaging_text is None."""
        product = ProductFull(
            slug="test-product", name="Test Product", description="Test", packaging_text=None
        )
        summary = product.to_summary()
        assert summary.has_packaging_text is False


# =============================================================================
# Project Storage Tests
# =============================================================================


@pytest.fixture
def sample_project() -> ProjectFull:
    """Create a sample project for testing."""
    return ProjectFull(
        slug="christmas-campaign",
        name="Christmas 2024 Campaign",
        status=ProjectStatus.ACTIVE,
        instructions="# Christmas Campaign\n\nUse festive red and green colors.",
    )


@pytest.fixture
def another_project() -> ProjectFull:
    """Create another sample project for testing."""
    return ProjectFull(
        slug="summer-sale",
        name="Summer Sale 2024",
        status=ProjectStatus.ACTIVE,
        instructions="Use bright, sunny imagery.",
    )


class TestProjectPathHelpers:
    """Tests for project path helper functions."""

    def test_get_projects_dir(self) -> None:
        """Test get_projects_dir returns correct path."""
        projects_dir = get_projects_dir("test-brand")
        expected = Path.home() / ".sip-studio" / "brands" / "test-brand" / "projects"
        assert projects_dir == expected

    def test_get_project_dir(self) -> None:
        """Test get_project_dir returns correct path."""
        project_dir = get_project_dir("test-brand", "christmas-campaign")
        expected = (
            Path.home()
            / ".sip-studio"
            / "brands"
            / "test-brand"
            / "projects"
            / "christmas-campaign"
        )
        assert project_dir == expected


class TestProjectIndexManagement:
    """Tests for project index load/save functions."""

    def test_load_project_index_creates_new(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that load_project_index creates empty index if not exists."""
        create_brand(sample_brand_identity)
        index = load_project_index("test-brand")
        assert len(index.projects) == 0
        assert index.active_project is None

    def test_save_and_load_project_index(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test saving and loading a project index."""
        create_brand(sample_brand_identity)

        from sip_studio.brands.models import ProjectIndex, ProjectSummary

        summary = ProjectSummary(
            slug="test-project", name="Test Project", status=ProjectStatus.ACTIVE
        )
        index = ProjectIndex(projects=[summary], active_project="test-project")
        save_project_index("test-brand", index)

        loaded = load_project_index("test-brand")
        assert len(loaded.projects) == 1
        assert loaded.active_project == "test-project"


class TestProjectCRUD:
    """Tests for project CRUD operations."""

    def test_create_project(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test creating a new project."""
        create_brand(sample_brand_identity)
        summary = create_project("test-brand", sample_project)

        assert summary.slug == "christmas-campaign"
        assert summary.name == "Christmas 2024 Campaign"
        assert summary.status == ProjectStatus.ACTIVE
        assert summary.asset_count == 0

        # Verify files created
        project_dir = temp_brands_dir / "test-brand" / "projects" / "christmas-campaign"
        assert (project_dir / "project.json").exists()
        assert (project_dir / "project_full.json").exists()

    def test_create_project_brand_not_found(
        self, temp_brands_dir: Path, sample_project: ProjectFull
    ) -> None:
        """Test creating project for nonexistent brand raises error."""
        with pytest.raises(ValueError, match="Brand .* not found"):
            create_project("nonexistent", sample_project)

    def test_create_duplicate_project_raises(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test creating duplicate project raises error."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)

        with pytest.raises(ValueError, match="already exists"):
            create_project("test-brand", sample_project)

    def test_load_project(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test loading a project."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)

        loaded = load_project("test-brand", "christmas-campaign")

        assert loaded is not None
        assert loaded.slug == "christmas-campaign"
        assert loaded.name == "Christmas 2024 Campaign"
        assert "festive" in loaded.instructions

    def test_load_project_not_found(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test loading nonexistent project returns None."""
        create_brand(sample_brand_identity)
        assert load_project("test-brand", "nonexistent") is None

    def test_load_project_summary(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test loading just the project summary."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)

        summary = load_project_summary("test-brand", "christmas-campaign")

        assert summary is not None
        assert summary.slug == "christmas-campaign"
        assert summary.status == ProjectStatus.ACTIVE

    def test_save_project_updates_existing(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test updating an existing project."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)

        sample_project.instructions = "Updated instructions"
        save_project("test-brand", sample_project)

        loaded = load_project("test-brand", "christmas-campaign")
        assert loaded.instructions == "Updated instructions"

    def test_save_project_creates_if_not_exists(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test that save_project creates project if not exists."""
        create_brand(sample_brand_identity)
        summary = save_project("test-brand", sample_project)

        assert summary.slug == "christmas-campaign"
        assert load_project("test-brand", "christmas-campaign") is not None

    def test_delete_project(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test deleting a project."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)

        result = delete_project("test-brand", "christmas-campaign")

        assert result is True
        assert load_project("test-brand", "christmas-campaign") is None

        # Verify index updated
        index = load_project_index("test-brand")
        assert len(index.projects) == 0

    def test_delete_project_not_found(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test deleting nonexistent project returns False."""
        create_brand(sample_brand_identity)
        assert delete_project("test-brand", "nonexistent") is False

    def test_list_projects(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
        another_project: ProjectFull,
    ) -> None:
        """Test listing projects for a brand."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)
        create_project("test-brand", another_project)

        projects = list_projects("test-brand")

        assert len(projects) == 2
        slugs = [p.slug for p in projects]
        assert "christmas-campaign" in slugs
        assert "summer-sale" in slugs

    def test_list_projects_sorted_by_name(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
        another_project: ProjectFull,
    ) -> None:
        """Test that list_projects returns projects sorted by name."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)  # Christmas 2024 Campaign
        create_project("test-brand", another_project)  # Summer Sale 2024

        projects = list_projects("test-brand")

        # Christmas comes before Summer alphabetically
        assert projects[0].name == "Christmas 2024 Campaign"
        assert projects[1].name == "Summer Sale 2024"


class TestActiveProject:
    """Tests for active project management."""

    def test_get_active_project_initially_none(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that active project is initially None."""
        create_brand(sample_brand_identity)
        assert get_active_project("test-brand") is None

    def test_set_and_get_active_project(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test setting and getting active project."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)

        set_active_project("test-brand", "christmas-campaign")

        assert get_active_project("test-brand") == "christmas-campaign"

    def test_set_nonexistent_project_raises(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that setting nonexistent project raises ValueError."""
        create_brand(sample_brand_identity)

        with pytest.raises(ValueError, match="not found"):
            set_active_project("test-brand", "nonexistent")

    def test_clear_active_project(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test clearing active project by setting to None."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)
        set_active_project("test-brand", "christmas-campaign")

        set_active_project("test-brand", None)

        assert get_active_project("test-brand") is None

    def test_delete_active_project_clears_active(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test that deleting the active project clears the active setting."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)
        set_active_project("test-brand", "christmas-campaign")

        delete_project("test-brand", "christmas-campaign")

        assert get_active_project("test-brand") is None


class TestProjectAssets:
    """Tests for project asset tracking via filename prefix."""

    def test_count_project_assets_empty(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test counting assets when none exist."""
        create_brand(sample_brand_identity)
        count = count_project_assets("test-brand", "christmas-campaign")
        assert count == 0

    def test_count_project_assets(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test counting assets by project prefix."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)

        # Create some fake generated assets with project prefix
        generated_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        generated_dir.mkdir(parents=True)
        (generated_dir / "christmas-campaign__20241201_120000_abc123.png").write_bytes(b"fake")
        (generated_dir / "christmas-campaign__20241202_130000_def456.png").write_bytes(b"fake")
        (generated_dir / "other-project__20241201_140000_ghi789.png").write_bytes(b"fake")

        count = count_project_assets("test-brand", "christmas-campaign")

        assert count == 2

    def test_list_project_assets(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test listing assets by project prefix."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)

        # Create some fake generated assets
        generated_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        generated_dir.mkdir(parents=True)
        (generated_dir / "christmas-campaign__20241201_120000_abc123.png").write_bytes(b"fake")
        (generated_dir / "christmas-campaign__20241202_130000_def456.png").write_bytes(b"fake")
        (generated_dir / "other-project__20241201_140000_ghi789.png").write_bytes(b"fake")

        assets = list_project_assets("test-brand", "christmas-campaign")

        assert len(assets) == 2
        # Should return assets-relative paths
        assert "generated/christmas-campaign__20241201_120000_abc123.png" in assets
        assert "generated/christmas-campaign__20241202_130000_def456.png" in assets
        assert "generated/other-project__20241201_140000_ghi789.png" not in assets

    def test_list_project_assets_empty(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Test listing assets when none exist."""
        create_brand(sample_brand_identity)
        assets = list_project_assets("test-brand", "christmas-campaign")
        assert assets == []

    def test_project_asset_count_updates_on_save(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Test that project asset_count is recalculated on save."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)

        # Create some assets
        generated_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        generated_dir.mkdir(parents=True)
        (generated_dir / "christmas-campaign__asset1.png").write_bytes(b"fake")
        (generated_dir / "christmas-campaign__asset2.png").write_bytes(b"fake")

        # Save project (should recalculate asset_count)
        sample_project.instructions = "Updated"
        summary = save_project("test-brand", sample_project)

        assert summary.asset_count == 2


# =============================================================================
# Stage 0: Characterization Tests for Base Class Refactoring
# =============================================================================
# These tests document the exact current behavior of the storage modules
# to ensure the base class refactoring does not introduce regressions.


@pytest.fixture
def sample_style_reference():
    """Create a sample style reference for testing."""
    from sip_studio.brands.models import StyleReferenceFull

    return StyleReferenceFull(
        slug="hero-centered",
        name="Hero Centered Layout",
        description="Centered hero image with text overlay",
    )


class TestCharacterizationCreateSaveSemantics:
    """Tests documenting create vs save behavior differences."""

    def test_create_duplicate_raises_error_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Verify create_product raises DuplicateEntityError for existing product."""
        from sip_studio.exceptions import DuplicateEntityError

        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        with pytest.raises(DuplicateEntityError):
            create_product("test-brand", sample_product)

    def test_create_duplicate_raises_error_project(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Verify create_project raises DuplicateEntityError for existing project."""
        from sip_studio.exceptions import DuplicateEntityError

        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)
        with pytest.raises(DuplicateEntityError):
            create_project("test-brand", sample_project)

    def test_create_duplicate_raises_error_style_reference(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_style_reference,
    ) -> None:
        """Verify create_style_reference raises DuplicateEntityError."""
        from sip_studio.brands.storage import create_style_reference
        from sip_studio.exceptions import DuplicateEntityError

        create_brand(sample_brand_identity)
        create_style_reference("test-brand", sample_style_reference)
        with pytest.raises(DuplicateEntityError):
            create_style_reference("test-brand", sample_style_reference)

    def test_save_nonexistent_creates_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Verify save_product creates product if not exists."""
        create_brand(sample_brand_identity)
        summary = save_product("test-brand", sample_product)
        assert summary.slug == "night-cream"
        assert load_product("test-brand", "night-cream") is not None

    def test_save_nonexistent_creates_project(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Verify save_project creates project if not exists."""
        create_brand(sample_brand_identity)
        summary = save_project("test-brand", sample_project)
        assert summary.slug == "christmas-campaign"
        assert load_project("test-brand", "christmas-campaign") is not None

    def test_save_nonexistent_creates_style_reference(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_style_reference,
    ) -> None:
        """Verify save_style_reference creates if not exists."""
        from sip_studio.brands.storage import load_style_reference, save_style_reference

        create_brand(sample_brand_identity)
        summary = save_style_reference("test-brand", sample_style_reference)
        assert summary.slug == "hero-centered"
        assert load_style_reference("test-brand", "hero-centered") is not None

    def test_save_existing_overwrites_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Verify save_product overwrites existing product."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        sample_product.description = "Updated description"
        save_product("test-brand", sample_product)
        loaded = load_product("test-brand", "night-cream")
        assert loaded.description == "Updated description"

    def test_save_existing_overwrites_project(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Verify save_project overwrites existing project."""
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)
        sample_project.instructions = "Updated instructions"
        save_project("test-brand", sample_project)
        loaded = load_project("test-brand", "christmas-campaign")
        assert loaded.instructions == "Updated instructions"

    def test_save_existing_overwrites_style_reference(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_style_reference,
    ) -> None:
        """Verify save_style_reference overwrites existing."""
        from sip_studio.brands.storage import (
            create_style_reference,
            load_style_reference,
            save_style_reference,
        )

        create_brand(sample_brand_identity)
        create_style_reference("test-brand", sample_style_reference)
        sample_style_reference.description = "Updated description"
        save_style_reference("test-brand", sample_style_reference)
        loaded = load_style_reference("test-brand", "hero-centered")
        assert loaded.description == "Updated description"


class TestCharacterizationTimestampHandling:
    """Tests documenting timestamp behavior."""

    def test_create_sets_timestamps_product(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify create_product preserves entity timestamps (set at model creation)."""
        from datetime import datetime

        create_brand(sample_brand_identity)
        before = datetime.utcnow()
        prod = ProductFull(slug="test-prod", name="Test", description="Test")
        after = datetime.utcnow()
        create_product("test-brand", prod)
        loaded = load_product("test-brand", "test-prod")
        # Timestamps are set when model is created, not when create_product is called
        assert before <= loaded.created_at <= after
        assert before <= loaded.updated_at <= after

    def test_save_updates_updated_at_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Verify save_product updates updated_at timestamp."""
        import time

        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        first = load_product("test-brand", "night-cream")
        first_updated = first.updated_at
        time.sleep(0.01)
        sample_product.description = "Changed"
        save_product("test-brand", sample_product)
        second = load_product("test-brand", "night-cream")
        assert second.updated_at > first_updated

    def test_save_updates_updated_at_project(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Verify save_project updates updated_at timestamp."""
        import time

        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)
        first = load_project("test-brand", "christmas-campaign")
        first_updated = first.updated_at
        time.sleep(0.01)
        sample_project.instructions = "Changed"
        save_project("test-brand", sample_project)
        second = load_project("test-brand", "christmas-campaign")
        assert second.updated_at > first_updated

    def test_save_updates_updated_at_style_reference(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_style_reference,
    ) -> None:
        """Verify save_style_reference updates updated_at."""
        import time

        from sip_studio.brands.storage import (
            create_style_reference,
            load_style_reference,
            save_style_reference,
        )

        create_brand(sample_brand_identity)
        create_style_reference("test-brand", sample_style_reference)
        first = load_style_reference("test-brand", "hero-centered")
        first_updated = first.updated_at
        time.sleep(0.01)
        sample_style_reference.description = "Changed"
        save_style_reference("test-brand", sample_style_reference)
        second = load_style_reference("test-brand", "hero-centered")
        assert second.updated_at > first_updated


class TestCharacterizationIndexBehavior:
    """Tests documenting index add/replace behavior."""

    def test_index_add_replaces_existing_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Verify ProductIndex.add_product replaces existing entry."""
        from sip_studio.brands.models import ProductIndex, ProductSummary

        idx = ProductIndex()
        s1 = ProductSummary(slug="test", name="Original", description="D")
        s2 = ProductSummary(slug="test", name="Updated", description="D")
        idx.add_product(s1)
        idx.add_product(s2)
        assert len(idx.products) == 1
        assert idx.products[0].name == "Updated"

    def test_index_add_replaces_existing_project(self, temp_brands_dir: Path) -> None:
        """Verify ProjectIndex.add_project replaces existing entry."""
        from sip_studio.brands.models import ProjectIndex, ProjectSummary

        idx = ProjectIndex()
        s1 = ProjectSummary(slug="test", name="Original")
        s2 = ProjectSummary(slug="test", name="Updated")
        idx.add_project(s1)
        idx.add_project(s2)
        assert len(idx.projects) == 1
        assert idx.projects[0].name == "Updated"

    def test_index_add_replaces_existing_style_reference(self, temp_brands_dir: Path) -> None:
        """Verify StyleReferenceIndex.add_style_reference replaces existing."""
        from sip_studio.brands.models import StyleReferenceIndex, StyleReferenceSummary

        idx = StyleReferenceIndex()
        s1 = StyleReferenceSummary(slug="test", name="Original")
        s2 = StyleReferenceSummary(slug="test", name="Updated")
        idx.add_style_reference(s1)
        idx.add_style_reference(s2)
        assert len(idx.style_references) == 1
        assert idx.style_references[0].name == "Updated"

    def test_list_sorted_by_name_case_insensitive_product(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify list_products sorts case-insensitively by name."""
        create_brand(sample_brand_identity)
        create_product("test-brand", ProductFull(slug="z-prod", name="Zebra", description="D"))
        create_product("test-brand", ProductFull(slug="a-prod", name="alpha", description="D"))
        create_product("test-brand", ProductFull(slug="m-prod", name="Middle", description="D"))
        products = list_products("test-brand")
        names = [p.name for p in products]
        assert names == ["alpha", "Middle", "Zebra"]

    def test_list_sorted_by_name_case_insensitive_project(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify list_projects sorts case-insensitively by name."""
        create_brand(sample_brand_identity)
        create_project("test-brand", ProjectFull(slug="z-proj", name="Zebra"))
        create_project("test-brand", ProjectFull(slug="a-proj", name="alpha"))
        create_project("test-brand", ProjectFull(slug="m-proj", name="Middle"))
        projects = list_projects("test-brand")
        names = [p.name for p in projects]
        assert names == ["alpha", "Middle", "Zebra"]

    def test_list_sorted_by_name_case_insensitive_style_reference(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify list_style_references sorts case-insensitively by name."""
        from sip_studio.brands.models import StyleReferenceFull
        from sip_studio.brands.storage import create_style_reference, list_style_references

        create_brand(sample_brand_identity)
        create_style_reference("test-brand", StyleReferenceFull(slug="z-ref", name="Zebra"))
        create_style_reference("test-brand", StyleReferenceFull(slug="a-ref", name="alpha"))
        create_style_reference("test-brand", StyleReferenceFull(slug="m-ref", name="Middle"))
        refs = list_style_references("test-brand")
        names = [r.name for r in refs]
        assert names == ["alpha", "Middle", "Zebra"]


class TestCharacterizationNotFoundHandling:
    """Tests documenting not-found behavior."""

    def test_load_nonexistent_returns_none_product(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify load_product returns None for nonexistent."""
        create_brand(sample_brand_identity)
        assert load_product("test-brand", "nonexistent") is None

    def test_load_nonexistent_returns_none_project(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify load_project returns None for nonexistent."""
        create_brand(sample_brand_identity)
        assert load_project("test-brand", "nonexistent") is None

    def test_load_nonexistent_returns_none_style_reference(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify load_style_reference returns None for nonexistent."""
        from sip_studio.brands.storage import load_style_reference

        create_brand(sample_brand_identity)
        assert load_style_reference("test-brand", "nonexistent") is None

    def test_load_corrupted_json_returns_none_product(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify load_product returns None for corrupted JSON."""
        create_brand(sample_brand_identity)
        prod_dir = temp_brands_dir / "test-brand" / "products" / "bad-product"
        prod_dir.mkdir(parents=True)
        (prod_dir / "product_full.json").write_text("not valid json")
        assert load_product("test-brand", "bad-product") is None

    def test_load_corrupted_json_returns_none_project(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify load_project returns None for corrupted JSON."""
        create_brand(sample_brand_identity)
        proj_dir = temp_brands_dir / "test-brand" / "projects" / "bad-project"
        proj_dir.mkdir(parents=True)
        (proj_dir / "project_full.json").write_text("not valid json")
        assert load_project("test-brand", "bad-project") is None

    def test_load_corrupted_json_returns_none_style_reference(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify load_style_reference returns None for corrupted JSON."""
        from sip_studio.brands.storage import load_style_reference

        create_brand(sample_brand_identity)
        ref_dir = temp_brands_dir / "test-brand" / "style_references" / "bad-ref"
        ref_dir.mkdir(parents=True)
        (ref_dir / "style_reference_full.json").write_text("not valid json")
        assert load_style_reference("test-brand", "bad-ref") is None

    def test_delete_nonexistent_returns_false_product(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify delete_product returns False for nonexistent."""
        create_brand(sample_brand_identity)
        assert delete_product("test-brand", "nonexistent") is False

    def test_delete_nonexistent_returns_false_project(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify delete_project returns False for nonexistent."""
        create_brand(sample_brand_identity)
        assert delete_project("test-brand", "nonexistent") is False

    def test_delete_nonexistent_returns_false_style_reference(
        self, temp_brands_dir: Path, sample_brand_identity: BrandIdentityFull
    ) -> None:
        """Verify delete_style_reference returns False for nonexistent."""
        from sip_studio.brands.storage import delete_style_reference

        create_brand(sample_brand_identity)
        assert delete_style_reference("test-brand", "nonexistent") is False


class TestCharacterizationImageOperations:
    """Tests documenting image management behavior."""

    def test_add_image_sets_primary_if_first_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Verify add_product_image sets primary_image if first."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        path = add_product_image("test-brand", "night-cream", "first.png", b"data")
        prod = load_product("test-brand", "night-cream")
        assert prod.primary_image == path

    def test_add_image_sets_primary_if_first_style_reference(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_style_reference,
    ) -> None:
        """Verify add_style_reference_image sets primary_image if first."""
        from sip_studio.brands.storage import (
            add_style_reference_image,
            create_style_reference,
            load_style_reference,
        )

        create_brand(sample_brand_identity)
        create_style_reference("test-brand", sample_style_reference)
        path = add_style_reference_image("test-brand", "hero-centered", "first.png", b"data")
        ref = load_style_reference("test-brand", "hero-centered")
        assert ref.primary_image == path

    def test_delete_primary_falls_back_to_next_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Verify deleting primary image falls back to next available."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        add_product_image("test-brand", "night-cream", "first.png", b"data1")
        add_product_image("test-brand", "night-cream", "second.png", b"data2")
        delete_product_image("test-brand", "night-cream", "first.png")
        prod = load_product("test-brand", "night-cream")
        assert prod.primary_image == "products/night-cream/images/second.png"

    def test_delete_primary_falls_back_to_next_style_reference(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_style_reference,
    ) -> None:
        """Verify deleting primary falls back to next for style reference."""
        from sip_studio.brands.storage import (
            add_style_reference_image,
            create_style_reference,
            delete_style_reference_image,
            load_style_reference,
        )

        create_brand(sample_brand_identity)
        create_style_reference("test-brand", sample_style_reference)
        add_style_reference_image("test-brand", "hero-centered", "first.png", b"data1")
        add_style_reference_image("test-brand", "hero-centered", "second.png", b"data2")
        delete_style_reference_image("test-brand", "hero-centered", "first.png")
        ref = load_style_reference("test-brand", "hero-centered")
        assert ref.primary_image == "style_references/hero-centered/images/second.png"

    def test_delete_only_image_clears_primary_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Verify deleting only image sets primary to empty string."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        add_product_image("test-brand", "night-cream", "only.png", b"data")
        delete_product_image("test-brand", "night-cream", "only.png")
        prod = load_product("test-brand", "night-cream")
        assert prod.primary_image == ""

    def test_delete_only_image_clears_primary_style_reference(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_style_reference,
    ) -> None:
        """Verify deleting only image sets primary to empty for style ref."""
        from sip_studio.brands.storage import (
            add_style_reference_image,
            create_style_reference,
            delete_style_reference_image,
            load_style_reference,
        )

        create_brand(sample_brand_identity)
        create_style_reference("test-brand", sample_style_reference)
        add_style_reference_image("test-brand", "hero-centered", "only.png", b"data")
        delete_style_reference_image("test-brand", "hero-centered", "only.png")
        ref = load_style_reference("test-brand", "hero-centered")
        assert ref.primary_image == ""

    def test_set_primary_nonexistent_returns_false_product(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_product: ProductFull,
    ) -> None:
        """Verify set_primary returns False if image not in product."""
        create_brand(sample_brand_identity)
        create_product("test-brand", sample_product)
        result = set_primary_product_image(
            "test-brand", "night-cream", "products/night-cream/images/nonexistent.png"
        )
        assert result is False

    def test_set_primary_nonexistent_returns_false_style_reference(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_style_reference,
    ) -> None:
        """Verify set_primary returns False if image not in style ref."""
        from sip_studio.brands.storage import (
            create_style_reference,
            set_primary_style_reference_image,
        )

        create_brand(sample_brand_identity)
        create_style_reference("test-brand", sample_style_reference)
        result = set_primary_style_reference_image(
            "test-brand", "hero-centered", "style_references/hero-centered/images/nonexistent.png"
        )
        assert result is False


class TestCharacterizationProjectAssetCount:
    """Tests documenting project asset_count behavior."""

    def test_project_summary_has_asset_count(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Verify ProjectSummary includes asset_count field."""
        create_brand(sample_brand_identity)
        summary = create_project("test-brand", sample_project)
        assert hasattr(summary, "asset_count")
        assert summary.asset_count == 0

    def test_list_projects_uses_cached_asset_count(
        self,
        temp_brands_dir: Path,
        sample_brand_identity: BrandIdentityFull,
        sample_project: ProjectFull,
    ) -> None:
        """Verify list_projects returns cached asset_count from index.
        Note: asset_count in index is only updated on save, not on list.
        """
        create_brand(sample_brand_identity)
        create_project("test-brand", sample_project)
        # Create assets after project creation
        generated_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        generated_dir.mkdir(parents=True)
        (generated_dir / "christmas-campaign__asset1.png").write_bytes(b"fake")
        # list_projects returns index value (0), not recalculated
        projects = list_projects("test-brand")
        assert projects[0].asset_count == 0
        # After save, asset_count is recalculated
        sample_project.instructions = "Updated"
        save_project("test-brand", sample_project)
        projects = list_projects("test-brand")
        assert projects[0].asset_count == 1


class TestCharacterizationBrandNotFound:
    """Tests documenting BrandNotFoundError behavior."""

    def test_create_product_brand_not_found(
        self, temp_brands_dir: Path, sample_product: ProductFull
    ) -> None:
        """Verify create_product raises BrandNotFoundError."""
        from sip_studio.exceptions import BrandNotFoundError

        with pytest.raises(BrandNotFoundError):
            create_product("nonexistent-brand", sample_product)

    def test_create_project_brand_not_found(
        self, temp_brands_dir: Path, sample_project: ProjectFull
    ) -> None:
        """Verify create_project raises BrandNotFoundError."""
        from sip_studio.exceptions import BrandNotFoundError

        with pytest.raises(BrandNotFoundError):
            create_project("nonexistent-brand", sample_project)

    def test_create_style_reference_brand_not_found(
        self, temp_brands_dir: Path, sample_style_reference
    ) -> None:
        """Verify create_style_reference raises BrandNotFoundError."""
        from sip_studio.brands.storage import create_style_reference
        from sip_studio.exceptions import BrandNotFoundError

        with pytest.raises(BrandNotFoundError):
            create_style_reference("nonexistent-brand", sample_style_reference)
