"""Tests for brand migration utility."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from sip_videogen.brands.migration import (
    convert_brief_and_direction_to_identity,
    find_legacy_brand_kits,
    load_legacy_brand_kit,
    migrate_all_brand_kits,
    migrate_brand_kit,
)
from sip_videogen.brands.models import BrandIdentityFull
from sip_videogen.brands.storage import get_brands_dir, load_brand
from sip_videogen.models.brand_kit import (
    BrandAssetCategory,
    BrandAssetResult,
    BrandDirection,
    BrandKitBrief,
    BrandKitPackage,
)


@pytest.fixture
def sample_brief() -> BrandKitBrief:
    """Create a sample BrandKitBrief for testing."""
    return BrandKitBrief(
        brand_name="EternaCare",
        product_category="Skincare",
        core_product="Nourishing Face Cream",
        target_audience="Senior citizens seeking gentle, effective skin care",
        tone="Caring, trustworthy, uplifting",
        style_keywords=["gentle", "soothing", "clean", "inclusive", "timeless"],
        constraints=["Accessible typography", "Soothing colors"],
        avoid=["Harsh aesthetics", "Small fonts"],
    )


@pytest.fixture
def sample_direction() -> BrandDirection:
    """Create a sample BrandDirection for testing."""
    return BrandDirection(
        id="classic_serenity",
        label="Classic Serenity",
        summary="A timeless, elegant direction using classic design cues",
        tone="Elegant, timeless, reassuring",
        style_keywords=["classic", "elegant", "refined", "welcoming"],
        color_palette=["#F5EDE1", "#B8A898", "#6E6658", "#405060"],
        typography="Serif typeface with generous spacing (e.g., Merriweather, Georgia)",
        materials=["Matte paper", "Brushed metallic accents"],
        settings=["Bright vanity table", "Comfortable bedroom"],
        differentiator="Leverages warmth and tradition to cultivate trust",
    )


@pytest.fixture
def sample_brand_kit_package(
    sample_brief: BrandKitBrief, sample_direction: BrandDirection
) -> BrandKitPackage:
    """Create a sample BrandKitPackage for testing."""
    return BrandKitPackage(
        brief=sample_brief,
        selected_direction=sample_direction,
        asset_results=[
            BrandAssetResult(
                prompt_id="logo_primary",
                category=BrandAssetCategory.LOGO,
                label="Primary Logo",
                prompt_used="Create a logo...",
                image_paths=["assets/logo/logo_primary.png"],
            )
        ],
        output_dir="output/brandkit_test",
        selected_logo_path="assets/logo/selected_logo.png",
    )


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory with sample brand kit."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def temp_brands_dir(tmp_path: Path):
    """Create a temporary brands directory for testing."""
    brands_dir = tmp_path / ".sip-videogen" / "brands"
    brands_dir.mkdir(parents=True)

    with patch("sip_videogen.brands.storage.get_brands_dir", return_value=brands_dir):
        with patch("sip_videogen.brands.migration.get_brand_dir") as mock_get_brand_dir:
            mock_get_brand_dir.side_effect = lambda slug: brands_dir / slug
            yield brands_dir


class TestConvertBriefAndDirection:
    """Tests for convert_brief_and_direction_to_identity function."""

    def test_basic_conversion(
        self, sample_brief: BrandKitBrief, sample_direction: BrandDirection
    ) -> None:
        """Test basic conversion of brief and direction to identity."""
        identity = convert_brief_and_direction_to_identity(
            sample_brief, sample_direction
        )

        assert identity.slug == "eternacare"
        assert identity.core.name == "EternaCare"
        assert identity.positioning.market_category == "Skincare"
        assert len(identity.visual.primary_colors) == 2
        assert len(identity.visual.secondary_colors) == 2

    def test_slug_override(
        self, sample_brief: BrandKitBrief, sample_direction: BrandDirection
    ) -> None:
        """Test that slug can be overridden."""
        identity = convert_brief_and_direction_to_identity(
            sample_brief, sample_direction, slug="custom-slug"
        )

        assert identity.slug == "custom-slug"

    def test_color_palette_mapping(
        self, sample_brief: BrandKitBrief, sample_direction: BrandDirection
    ) -> None:
        """Test that color palette is correctly mapped."""
        identity = convert_brief_and_direction_to_identity(
            sample_brief, sample_direction
        )

        # First 2 colors should be primary
        assert identity.visual.primary_colors[0].hex == "#F5EDE1"
        assert identity.visual.primary_colors[1].hex == "#B8A898"
        # Remaining should be secondary
        assert identity.visual.secondary_colors[0].hex == "#6E6658"
        assert identity.visual.secondary_colors[1].hex == "#405060"

    def test_typography_extraction(
        self, sample_brief: BrandKitBrief, sample_direction: BrandDirection
    ) -> None:
        """Test that typography is extracted from direction."""
        identity = convert_brief_and_direction_to_identity(
            sample_brief, sample_direction
        )

        assert len(identity.visual.typography) >= 1
        assert identity.visual.typography[0].family == "Merriweather"
        assert identity.visual.typography[0].role == "headings"

    def test_constraints_and_avoid_copied(
        self, sample_brief: BrandKitBrief, sample_direction: BrandDirection
    ) -> None:
        """Test that constraints and avoid lists are copied."""
        identity = convert_brief_and_direction_to_identity(
            sample_brief, sample_direction
        )

        assert identity.constraints == sample_brief.constraints
        assert identity.avoid == sample_brief.avoid

    def test_audience_profile_populated(
        self, sample_brief: BrandKitBrief, sample_direction: BrandDirection
    ) -> None:
        """Test that audience profile is populated."""
        identity = convert_brief_and_direction_to_identity(
            sample_brief, sample_direction
        )

        assert identity.audience.primary_summary == sample_brief.target_audience

    def test_positioning_statement_generated(
        self, sample_brief: BrandKitBrief, sample_direction: BrandDirection
    ) -> None:
        """Test that positioning statement is generated."""
        identity = convert_brief_and_direction_to_identity(
            sample_brief, sample_direction
        )

        assert "EternaCare" in identity.positioning.positioning_statement
        assert "Skincare" in identity.positioning.positioning_statement

    def test_voice_tone_attributes_parsed(
        self, sample_brief: BrandKitBrief, sample_direction: BrandDirection
    ) -> None:
        """Test that tone attributes are parsed from comma-separated string."""
        identity = convert_brief_and_direction_to_identity(
            sample_brief, sample_direction
        )

        assert "Elegant" in identity.voice.tone_attributes
        assert "timeless" in identity.voice.tone_attributes


class TestFindLegacyBrandKits:
    """Tests for find_legacy_brand_kits function."""

    def test_finds_brand_kit_files(
        self, temp_output_dir: Path, sample_brand_kit_package: BrandKitPackage
    ) -> None:
        """Test that brand_kit.json files are found."""
        # Create a brand kit directory with brand_kit.json
        kit_dir = temp_output_dir / "brandkit_test"
        kit_dir.mkdir()
        (kit_dir / "brand_kit.json").write_text(
            sample_brand_kit_package.model_dump_json()
        )

        files = find_legacy_brand_kits(temp_output_dir)

        assert len(files) == 1
        assert files[0].name == "brand_kit.json"

    def test_returns_empty_for_missing_dir(self, tmp_path: Path) -> None:
        """Test that empty list is returned for missing directory."""
        files = find_legacy_brand_kits(tmp_path / "nonexistent")

        assert files == []

    def test_finds_multiple_kits(
        self, temp_output_dir: Path, sample_brand_kit_package: BrandKitPackage
    ) -> None:
        """Test that multiple brand_kit.json files are found."""
        for i in range(3):
            kit_dir = temp_output_dir / f"brandkit_{i}"
            kit_dir.mkdir()
            (kit_dir / "brand_kit.json").write_text(
                sample_brand_kit_package.model_dump_json()
            )

        files = find_legacy_brand_kits(temp_output_dir)

        assert len(files) == 3


class TestLoadLegacyBrandKit:
    """Tests for load_legacy_brand_kit function."""

    def test_loads_valid_brand_kit(
        self, temp_output_dir: Path, sample_brand_kit_package: BrandKitPackage
    ) -> None:
        """Test loading a valid brand_kit.json."""
        kit_dir = temp_output_dir / "brandkit_test"
        kit_dir.mkdir()
        kit_path = kit_dir / "brand_kit.json"
        kit_path.write_text(sample_brand_kit_package.model_dump_json())

        package = load_legacy_brand_kit(kit_path)

        assert package is not None
        assert package.brief.brand_name == "EternaCare"

    def test_returns_none_for_invalid_json(self, temp_output_dir: Path) -> None:
        """Test that None is returned for invalid JSON."""
        kit_dir = temp_output_dir / "brandkit_invalid"
        kit_dir.mkdir()
        kit_path = kit_dir / "brand_kit.json"
        kit_path.write_text("not valid json")

        package = load_legacy_brand_kit(kit_path)

        assert package is None

    def test_returns_none_for_missing_file(self, temp_output_dir: Path) -> None:
        """Test that None is returned for missing file."""
        package = load_legacy_brand_kit(temp_output_dir / "missing.json")

        assert package is None


class TestMigrateBrandKit:
    """Tests for migrate_brand_kit function."""

    def test_migrates_brand_kit(
        self,
        tmp_path: Path,
        sample_brand_kit_package: BrandKitPackage,
    ) -> None:
        """Test migrating a single brand kit."""
        # Set up temp directories
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        brands_dir = tmp_path / ".sip-videogen" / "brands"
        brands_dir.mkdir(parents=True)

        # Create brand kit
        kit_dir = output_dir / "brandkit_test"
        kit_dir.mkdir()
        kit_path = kit_dir / "brand_kit.json"
        kit_path.write_text(sample_brand_kit_package.model_dump_json())

        with patch("sip_videogen.brands.storage.get_brands_dir", return_value=brands_dir):
            with patch(
                "sip_videogen.brands.migration.get_brand_dir",
                side_effect=lambda slug: brands_dir / slug,
            ):
                slug = migrate_brand_kit(kit_path, copy_assets=False)

        assert slug == "eternacare"
        assert (brands_dir / "eternacare" / "identity.json").exists()
        assert (brands_dir / "eternacare" / "identity_full.json").exists()

    def test_skips_existing_brand(
        self,
        tmp_path: Path,
        sample_brand_kit_package: BrandKitPackage,
    ) -> None:
        """Test that existing brands are skipped."""
        # Set up temp directories
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        brands_dir = tmp_path / ".sip-videogen" / "brands"
        brands_dir.mkdir(parents=True)

        # Create brand kit
        kit_dir = output_dir / "brandkit_test"
        kit_dir.mkdir()
        kit_path = kit_dir / "brand_kit.json"
        kit_path.write_text(sample_brand_kit_package.model_dump_json())

        # Pre-create the brand directory
        (brands_dir / "eternacare").mkdir()

        with patch("sip_videogen.brands.storage.get_brands_dir", return_value=brands_dir):
            with patch(
                "sip_videogen.brands.migration.get_brand_dir",
                side_effect=lambda slug: brands_dir / slug,
            ):
                slug = migrate_brand_kit(kit_path, copy_assets=False)

        assert slug is None

    def test_copies_assets_when_enabled(
        self,
        tmp_path: Path,
        sample_brand_kit_package: BrandKitPackage,
    ) -> None:
        """Test that assets are copied when enabled."""
        # Set up temp directories
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        brands_dir = tmp_path / ".sip-videogen" / "brands"
        brands_dir.mkdir(parents=True)

        # Create brand kit with assets
        kit_dir = output_dir / "brandkit_test"
        kit_dir.mkdir()
        kit_path = kit_dir / "brand_kit.json"
        kit_path.write_text(sample_brand_kit_package.model_dump_json())

        # Create source assets
        assets_dir = kit_dir / "assets" / "logo"
        assets_dir.mkdir(parents=True)
        (assets_dir / "logo_primary.png").write_bytes(b"fake png data")

        with patch("sip_videogen.brands.storage.get_brands_dir", return_value=brands_dir):
            with patch(
                "sip_videogen.brands.migration.get_brand_dir",
                side_effect=lambda slug: brands_dir / slug,
            ):
                slug = migrate_brand_kit(kit_path, copy_assets=True)

        assert slug == "eternacare"
        # Check asset was copied
        copied_asset = brands_dir / "eternacare" / "assets" / "logo" / "logo_primary.png"
        assert copied_asset.exists()


class TestMigrateAllBrandKits:
    """Tests for migrate_all_brand_kits function."""

    def test_migrates_all_kits(
        self,
        tmp_path: Path,
        sample_brand_kit_package: BrandKitPackage,
    ) -> None:
        """Test migrating all brand kits."""
        # Set up temp directories
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        brands_dir = tmp_path / ".sip-videogen" / "brands"
        brands_dir.mkdir(parents=True)

        # Create multiple brand kits with different names
        for i, name in enumerate(["BrandA", "BrandB", "BrandC"]):
            kit_dir = output_dir / f"brandkit_{i}"
            kit_dir.mkdir()

            package = sample_brand_kit_package.model_copy(deep=True)
            package.brief.brand_name = name
            (kit_dir / "brand_kit.json").write_text(package.model_dump_json())

        with patch("sip_videogen.brands.storage.get_brands_dir", return_value=brands_dir):
            with patch(
                "sip_videogen.brands.migration.get_brand_dir",
                side_effect=lambda slug: brands_dir / slug,
            ):
                results = migrate_all_brand_kits(output_dir, copy_assets=False)

        migrated = [v for v in results.values() if v is not None]
        assert len(migrated) == 3
        assert "branda" in migrated
        assert "brandb" in migrated
        assert "brandc" in migrated

    def test_skips_existing_brands(
        self,
        tmp_path: Path,
        sample_brand_kit_package: BrandKitPackage,
    ) -> None:
        """Test that existing brands are skipped."""
        # Set up temp directories
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        brands_dir = tmp_path / ".sip-videogen" / "brands"
        brands_dir.mkdir(parents=True)

        # Create brand kit
        kit_dir = output_dir / "brandkit_test"
        kit_dir.mkdir()
        kit_path = kit_dir / "brand_kit.json"
        kit_path.write_text(sample_brand_kit_package.model_dump_json())

        # Pre-create the brand directory
        (brands_dir / "eternacare").mkdir()

        with patch("sip_videogen.brands.storage.get_brands_dir", return_value=brands_dir):
            with patch(
                "sip_videogen.brands.migration.get_brand_dir",
                side_effect=lambda slug: brands_dir / slug,
            ):
                results = migrate_all_brand_kits(
                    output_dir, copy_assets=False, skip_existing=True
                )

        assert results[str(kit_path)] is None
