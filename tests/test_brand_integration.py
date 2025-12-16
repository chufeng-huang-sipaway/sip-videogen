"""End-to-end integration tests for brand management system.

These tests verify complete workflows:
- Create brand flow
- Evolve brand flow
- Brand context in prompts
- Asset count updates after generation
- Active brand management
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from sip_videogen.brands.context import BrandContextBuilder, build_brand_context
from sip_videogen.brands.models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIdentityFull,
    ColorDefinition,
    CompetitivePositioning,
    TypographyRule,
    VisualIdentity,
    VoiceGuidelines,
)
from sip_videogen.brands.storage import (
    create_brand,
    delete_brand,
    get_active_brand,
    get_brand_dir,
    list_brands,
    load_brand,
    load_brand_summary,
    save_brand,
    set_active_brand,
)
from sip_videogen.brands.tools import (
    browse_brand_assets,
    fetch_brand_detail,
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
def complete_brand_identity() -> BrandIdentityFull:
    """Create a comprehensive brand identity for integration testing."""
    identity = BrandIdentityFull(slug="summit-coffee")
    identity.core = BrandCoreIdentity(
        name="Summit Coffee Co.",
        tagline="Elevate your morning ritual",
        mission="To bring sustainable, ethically-sourced coffee to busy professionals",
        brand_story="Founded by mountain climbers who wanted better coffee",
        values=["sustainability", "quality", "adventure"],
    )
    identity.positioning = CompetitivePositioning(
        market_category="Premium Coffee",
        unique_value_proposition="High-altitude coffee beans with exceptional flavor",
        primary_competitors=["Blue Bottle", "Stumptown"],
        differentiation="Only roaster specializing in high-altitude beans",
        positioning_statement="Summit Coffee is the premium coffee brand for adventurous professionals who want sustainable, exceptional coffee because we source exclusively from high-altitude farms.",
    )
    identity.voice = VoiceGuidelines(
        personality="Adventurous yet sophisticated",
        tone_attributes=["warm", "inspiring", "authentic"],
        key_messages=["Taste the altitude", "Sustainable from source to cup"],
        messaging_do=["Use nature imagery", "Emphasize origin story"],
        messaging_dont=["Be pretentious", "Use generic coffee clichés"],
        example_headlines=["Rise Above the Rest", "Peak Performance Coffee"],
        example_taglines=["Brew your adventure", "Where altitude meets attitude"],
    )
    identity.visual = VisualIdentity(
        primary_colors=[
            ColorDefinition(hex="#2C3E50", name="Mountain Slate", usage="Primary backgrounds"),
            ColorDefinition(hex="#8B7355", name="Coffee Bean", usage="Accents and highlights"),
        ],
        secondary_colors=[
            ColorDefinition(hex="#D4C4B0", name="Cream", usage="Secondary backgrounds"),
        ],
        accent_colors=[
            ColorDefinition(hex="#E67E22", name="Sunrise Orange", usage="CTA buttons"),
        ],
        typography=[
            TypographyRule(role="headings", family="Playfair Display", weight="bold"),
            TypographyRule(role="body", family="Source Sans Pro", weight="regular"),
        ],
        imagery_style="Professional photography with warm natural lighting, outdoor/mountain settings",
        imagery_keywords=["mountains", "sunrise", "coffee beans", "artisanal"],
        imagery_avoid=["generic stock photos", "cluttered compositions"],
        materials=["kraft paper", "recycled cardboard", "matte finishes"],
        logo_description="Stylized mountain peak forming a coffee cup",
        overall_aesthetic="Rustic premium - natural materials with sophisticated presentation",
        style_keywords=["artisanal", "premium", "sustainable", "natural"],
    )
    identity.audience = AudienceProfile(
        primary_summary="Urban professionals aged 28-45 who value sustainability",
        age_range="28-45",
        income_level="Upper middle class",
        interests=["outdoor activities", "sustainability", "premium foods"],
        values=["quality", "authenticity", "environmental responsibility"],
        lifestyle="Busy professionals who make time for quality experiences",
        pain_points=["Generic coffee options", "Lack of transparency in sourcing"],
        desires=["Better morning ritual", "Ethical consumption"],
    )
    identity.constraints = ["Must include recycled materials in packaging"]
    identity.avoid = ["Plastic packaging", "Generic coffee imagery"]
    return identity


@pytest.fixture
def brand_with_assets(temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull):
    """Create a brand with some pre-existing assets."""
    create_brand(complete_brand_identity)

    # Create asset files
    brand_dir = temp_brands_dir / "summit-coffee"
    (brand_dir / "assets" / "logo" / "primary-logo.png").write_bytes(b"fake png")
    (brand_dir / "assets" / "packaging" / "bag-front.jpg").write_bytes(b"fake jpg")
    (brand_dir / "assets" / "lifestyle" / "barista.webp").write_bytes(b"fake webp")
    (brand_dir / "assets" / "marketing" / "banner.png").write_bytes(b"fake png")

    return complete_brand_identity


# =============================================================================
# Full Workflow Tests: Create Brand → Generate Assets
# =============================================================================


class TestCreateBrandToGenerateAssetsFlow:
    """Tests for the create brand → generate assets integration flow."""

    def test_create_brand_generates_all_files(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that creating a brand generates all expected files and directories."""
        summary = create_brand(complete_brand_identity)

        # Verify brand files
        brand_dir = temp_brands_dir / "summit-coffee"
        assert (brand_dir / "identity.json").exists()
        assert (brand_dir / "identity_full.json").exists()

        # Verify directory structure
        assert (brand_dir / "assets" / "logo").is_dir()
        assert (brand_dir / "assets" / "packaging").is_dir()
        assert (brand_dir / "assets" / "lifestyle").is_dir()
        assert (brand_dir / "assets" / "mascot").is_dir()
        assert (brand_dir / "assets" / "marketing").is_dir()
        assert (brand_dir / "history").is_dir()

        # Verify summary content
        assert summary.slug == "summit-coffee"
        assert summary.name == "Summit Coffee Co."
        assert "#2C3E50" in summary.primary_colors


# =============================================================================
# Evolve Brand Flow Tests
# =============================================================================


class TestEvolveBrandFlow:
    """Tests for the evolve brand workflow."""

    def test_save_brand_updates_existing(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that save_brand updates an existing brand."""
        create_brand(complete_brand_identity)

        # Modify the brand
        complete_brand_identity.core.tagline = "New tagline for evolved brand"
        complete_brand_identity.voice.tone_attributes = ["bold", "dynamic", "fresh"]

        # Save and verify
        summary = save_brand(complete_brand_identity)
        assert summary.tagline == "New tagline for evolved brand"
        assert "bold" in summary.tone

        # Verify persistence
        loaded = load_brand("summit-coffee")
        assert loaded.core.tagline == "New tagline for evolved brand"

    def test_visual_evolution_updates_colors(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test evolving visual identity updates colors in stored brand."""
        create_brand(complete_brand_identity)

        # Evolve colors
        complete_brand_identity.visual.primary_colors = [
            ColorDefinition(hex="#1A1A2E", name="Deep Navy", usage="Primary"),
            ColorDefinition(hex="#E94560", name="Vibrant Red", usage="Accent"),
        ]
        save_brand(complete_brand_identity)

        # Verify new colors are stored
        loaded = load_brand("summit-coffee")
        color_hexes = [c.hex for c in loaded.visual.primary_colors]
        assert "#1A1A2E" in color_hexes
        assert "#E94560" in color_hexes
        assert "#2C3E50" not in color_hexes  # Old color should be gone

    def test_audience_evolution_updates_targeting(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test evolving audience profile updates targeting."""
        create_brand(complete_brand_identity)

        # Evolve audience
        complete_brand_identity.audience.primary_summary = "Health-conscious millennials who love specialty coffee"
        save_brand(complete_brand_identity)

        # Verify audience is stored
        loaded = load_brand("summit-coffee")
        assert "Health-conscious millennials" in loaded.audience.primary_summary

    def test_slug_preserved_on_evolution(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that slug is preserved when brand is evolved."""
        create_brand(complete_brand_identity)

        complete_brand_identity.core.name = "Summit Coffee Premium"
        save_brand(complete_brand_identity)

        # Slug should remain the same
        brands = list_brands()
        assert len(brands) == 1
        assert brands[0].slug == "summit-coffee"

        # But name should be updated
        assert brands[0].name == "Summit Coffee Premium"


# =============================================================================
# Brand Context in Prompts Tests
# =============================================================================


class TestBrandContextInPrompts:
    """Tests for brand context appearing in generated prompts."""

    def test_context_includes_all_brand_sections(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that brand context includes all major sections."""
        create_brand(complete_brand_identity)

        context = build_brand_context("summit-coffee")

        # Core identity
        assert "Summit Coffee Co." in context
        assert "Elevate your morning ritual" in context

        # Visual
        assert "#2C3E50" in context or "#8B7355" in context

        # Category
        assert "Premium Coffee" in context

        # Tone
        assert any(tone in context for tone in ["warm", "inspiring", "authentic"])

    def test_context_builder_generates_valid_prompt_injection(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that context builder can inject into prompts."""
        create_brand(complete_brand_identity)

        builder = BrandContextBuilder("summit-coffee")
        base_prompt = """You are a brand specialist.

{brand_context}

Generate marketing copy for the brand."""

        result = builder.inject_into_prompt(base_prompt)

        assert "{brand_context}" not in result
        assert "Summit Coffee Co." in result
        assert "Memory Exploration Protocol" in result

    def test_fetch_brand_detail_returns_correct_sections(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that fetch_brand_detail returns correct sections for agents."""
        create_brand(complete_brand_identity)
        set_brand_context("summit-coffee")

        # Test visual identity
        visual_json = fetch_brand_detail("visual_identity")
        visual_data = json.loads(visual_json)
        assert "primary_colors" in visual_data
        assert len(visual_data["primary_colors"]) == 2

        # Test voice guidelines
        voice_json = fetch_brand_detail("voice_guidelines")
        voice_data = json.loads(voice_json)
        assert "tone_attributes" in voice_data
        assert "warm" in voice_data["tone_attributes"]

        # Test audience profile
        audience_json = fetch_brand_detail("audience_profile")
        audience_data = json.loads(audience_json)
        assert "primary_summary" in audience_data

        # Test positioning
        positioning_json = fetch_brand_detail("positioning")
        positioning_data = json.loads(positioning_json)
        assert positioning_data["market_category"] == "Premium Coffee"


# =============================================================================
# Asset Count Update Tests
# =============================================================================


class TestAssetCountUpdates:
    """Tests for asset count updates after generation."""

    def test_initial_asset_count_is_zero(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that new brand has zero asset count."""
        summary = create_brand(complete_brand_identity)
        assert summary.asset_count == 0

    def test_asset_count_reflects_actual_files(
        self, brand_with_assets: BrandIdentityFull, temp_brands_dir: Path
    ) -> None:
        """Test that asset count matches actual files when updated."""
        # Manually update the summary stats (simulating what CLI does)
        brand_dir = temp_brands_dir / "summit-coffee"
        summary_path = brand_dir / "identity.json"

        # Count assets
        assets_dir = brand_dir / "assets"
        asset_count = 0
        for category in ["logo", "packaging", "lifestyle", "mascot", "marketing"]:
            cat_dir = assets_dir / category
            if cat_dir.exists():
                asset_count += sum(
                    1
                    for f in cat_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]
                )

        # Update summary
        summary = load_brand_summary("summit-coffee")
        summary.asset_count = asset_count
        summary.last_generation = datetime.utcnow().isoformat()
        summary_path.write_text(summary.model_dump_json(indent=2))

        # Reload and verify
        updated_summary = load_brand_summary("summit-coffee")
        assert updated_summary.asset_count == 4  # 1 logo + 1 packaging + 1 lifestyle + 1 marketing

    def test_last_generation_timestamp_updates(
        self, brand_with_assets: BrandIdentityFull, temp_brands_dir: Path
    ) -> None:
        """Test that last_generation timestamp is updated."""
        brand_dir = temp_brands_dir / "summit-coffee"
        summary_path = brand_dir / "identity.json"

        initial_summary = load_brand_summary("summit-coffee")
        initial_generation = initial_summary.last_generation

        # Update with new timestamp
        summary = load_brand_summary("summit-coffee")
        summary.last_generation = datetime.utcnow().isoformat()
        summary_path.write_text(summary.model_dump_json(indent=2))

        updated_summary = load_brand_summary("summit-coffee")
        assert updated_summary.last_generation != initial_generation
        assert updated_summary.last_generation != ""


# =============================================================================
# Browse Assets Tool Tests
# =============================================================================


class TestBrowseAssetsIntegration:
    """Tests for browse_brand_assets tool integration."""

    def test_browse_assets_returns_all_assets(
        self, brand_with_assets: BrandIdentityFull
    ) -> None:
        """Test that browse_brand_assets returns all assets."""
        set_brand_context("summit-coffee")

        result = browse_brand_assets()
        assets = json.loads(result)

        assert len(assets) == 4
        categories = {a["category"] for a in assets}
        assert categories == {"logo", "packaging", "lifestyle", "marketing"}

    def test_browse_assets_filters_by_category(
        self, brand_with_assets: BrandIdentityFull
    ) -> None:
        """Test filtering assets by category."""
        set_brand_context("summit-coffee")

        result = browse_brand_assets(category="logo")
        assets = json.loads(result)

        assert len(assets) == 1
        assert assets[0]["category"] == "logo"

    def test_browse_assets_returns_correct_paths(
        self, brand_with_assets: BrandIdentityFull, temp_brands_dir: Path
    ) -> None:
        """Test that asset paths are correct."""
        set_brand_context("summit-coffee")

        result = browse_brand_assets(category="logo")
        assets = json.loads(result)

        expected_path = str(temp_brands_dir / "summit-coffee" / "assets" / "logo" / "primary-logo.png")
        assert assets[0]["path"] == expected_path


# =============================================================================
# Active Brand Integration Tests
# =============================================================================


class TestActiveBrandIntegration:
    """Tests for active brand functionality in workflows."""

    def test_set_active_brand_persists(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that active brand setting persists across operations."""
        create_brand(complete_brand_identity)
        set_active_brand("summit-coffee")

        # Create another brand
        other_brand = BrandIdentityFull(slug="other-brand")
        other_brand.core = BrandCoreIdentity(name="Other Brand", tagline="Other tagline")
        create_brand(other_brand)

        # Active brand should still be summit-coffee
        assert get_active_brand() == "summit-coffee"

    def test_delete_active_brand_clears_active(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that deleting active brand clears the active setting."""
        create_brand(complete_brand_identity)
        set_active_brand("summit-coffee")

        delete_brand("summit-coffee")

        assert get_active_brand() is None


# =============================================================================
# Round-Trip Tests
# =============================================================================


class TestRoundTripIntegration:
    """Tests for complete round-trip operations."""

    def test_create_load_modify_save_cycle(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test complete create → load → modify → save cycle."""
        # Create
        create_brand(complete_brand_identity)

        # Load
        loaded = load_brand("summit-coffee")
        assert loaded.core.name == "Summit Coffee Co."

        # Modify
        loaded.core.tagline = "Modified tagline"
        loaded.visual.primary_colors.append(
            ColorDefinition(hex="#FF0000", name="New Red")
        )

        # Save
        save_brand(loaded)

        # Reload and verify
        reloaded = load_brand("summit-coffee")
        assert reloaded.core.tagline == "Modified tagline"
        assert len(reloaded.visual.primary_colors) == 3
        assert reloaded.visual.primary_colors[2].hex == "#FF0000"

    def test_summary_stays_in_sync_with_full(
        self, temp_brands_dir: Path, complete_brand_identity: BrandIdentityFull
    ) -> None:
        """Test that summary (L0) stays in sync with full identity (L1)."""
        create_brand(complete_brand_identity)

        # Modify full identity
        loaded = load_brand("summit-coffee")
        loaded.core.tagline = "New sync test tagline"
        loaded.voice.tone_attributes = ["bold", "energetic"]
        save_brand(loaded)

        # Summary should reflect changes
        summary = load_brand_summary("summit-coffee")
        assert summary.tagline == "New sync test tagline"
        assert "bold" in summary.tone
