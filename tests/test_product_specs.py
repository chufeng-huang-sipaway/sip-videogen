"""Tests for product specs builder (Phase 1 implementation)."""

import pytest

from sip_studio.advisor.product_specs import (
    ProductSpecs,
    build_product_specs,
    extract_dimensions_from_text,
    parse_measurement_to_mm,
)
from sip_studio.brands.models import (
    PackagingTextDescription,
    PackagingTextElement,
    ProductAttribute,
    ProductFull,
)


class TestParseMeasurementToMm:
    """Tests for measurement parsing."""

    def test_parse_mm(self):
        """Test parsing millimeters."""
        assert parse_measurement_to_mm("50mm") == 50.0
        assert parse_measurement_to_mm("50 mm") == 50.0
        assert parse_measurement_to_mm("50.5mm") == 50.5

    def test_parse_cm(self):
        """Test parsing centimeters."""
        assert parse_measurement_to_mm("5cm") == 50.0
        assert parse_measurement_to_mm("5 cm") == 50.0
        assert parse_measurement_to_mm("5.5cm") == 55.0

    def test_parse_inches(self):
        """Test parsing inches."""
        assert parse_measurement_to_mm("2in") == pytest.approx(50.8)
        assert parse_measurement_to_mm('2"') == pytest.approx(50.8)
        assert parse_measurement_to_mm("2 inch") == pytest.approx(50.8)
        assert parse_measurement_to_mm("2 inches") == pytest.approx(50.8)

    def test_parse_dimensionless(self):
        """Test parsing numbers without units (assumed mm)."""
        assert parse_measurement_to_mm("50") == 50.0

    def test_parse_invalid(self):
        """Test parsing invalid input."""
        assert parse_measurement_to_mm("") is None
        assert parse_measurement_to_mm("abc") is None
        assert parse_measurement_to_mm(None) is None  # type: ignore

    def test_parse_with_whitespace(self):
        """Test parsing with extra whitespace."""
        assert parse_measurement_to_mm("  50 mm  ") == 50.0


class TestExtractDimensionsFromText:
    """Tests for dimension extraction from free text."""

    def test_extract_triplet(self):
        """Test extracting dimension triplets."""
        dims = extract_dimensions_from_text("50 x 30 x 20 mm")
        assert "dimension_1" in dims
        assert dims["dimension_1"] == 50.0
        assert dims["dimension_2"] == 30.0
        assert dims["dimension_3"] == 20.0

    def test_extract_labeled(self):
        """Test extracting labeled dimensions."""
        dims = extract_dimensions_from_text("height: 100mm, width: 50mm")
        assert dims.get("height") == 100.0
        assert dims.get("width") == 50.0

    def test_extract_with_units(self):
        """Test extracting with different units."""
        dims = extract_dimensions_from_text("height: 10cm")
        assert dims.get("height") == 100.0

    def test_empty_text(self):
        """Test with empty text."""
        dims = extract_dimensions_from_text("")
        assert dims == {}

    def test_no_dimensions(self):
        """Test with text without dimensions."""
        dims = extract_dimensions_from_text("A beautiful product")
        assert dims == {}


class TestProductSpecs:
    """Tests for ProductSpecs dataclass."""

    def test_compute_ratios(self):
        """Test ratio computation."""
        specs = ProductSpecs(
            product_name="Test",
            product_slug="test",
            height_mm=100.0,
            width_mm=50.0,
            depth_mm=25.0,
        )
        specs.compute_ratios()
        assert specs.height_width_ratio == 2.0
        assert specs.height_depth_ratio == 4.0

    def test_compute_ratios_missing_dimensions(self):
        """Test ratio computation with missing dimensions."""
        specs = ProductSpecs(
            product_name="Test",
            product_slug="test",
            height_mm=100.0,
        )
        specs.compute_ratios()
        assert specs.height_width_ratio is None
        assert specs.height_depth_ratio is None

    def test_to_prompt_block_basic(self):
        """Test generating basic prompt block."""
        specs = ProductSpecs(
            product_name="Night Cream",
            product_slug="night-cream",
            height_mm=100.0,
            width_mm=50.0,
            materials=["glass"],
            colors=["blue"],
        )
        specs.compute_ratios()
        block = specs.to_prompt_block(index=1)

        assert "Night Cream" in block
        assert "Height: 100mm" in block
        assert "Width: 50mm" in block
        assert "glass" in block
        assert "blue" in block
        assert "2.0:1" in block  # height:width ratio

    def test_to_prompt_block_with_description(self):
        """Test prompt block includes sanitized description."""
        specs = ProductSpecs(
            product_name="Night Cream",
            product_slug="night-cream",
            description="A luxurious night cream for deep hydration.",
        )
        block = specs.to_prompt_block()

        assert "Product notes" in block
        assert "luxurious night cream" in block
        assert "---BEGIN PRODUCT DESCRIPTION---" in block
        assert "---END PRODUCT DESCRIPTION---" in block

    def test_to_prompt_block_sanitizes_backticks(self):
        """Test that backticks in description are escaped."""
        specs = ProductSpecs(
            product_name="Test Product",
            product_slug="test",
            description="Use `code` and ```blocks``` for injection",
        )
        block = specs.to_prompt_block()

        # Backticks should be replaced
        assert "`" not in block
        assert "```" not in block
        assert "code" in block  # Content preserved


class TestBuildProductSpecs:
    """Tests for building specs from ProductFull."""

    def test_build_from_product_with_attributes(self):
        """Test building specs from product with attributes."""
        product = ProductFull(
            slug="night-cream",
            name="Night Cream",
            description="A luxurious night cream",
            attributes=[
                ProductAttribute(key="height", value="100mm", category="measurements"),
                ProductAttribute(key="width", value="50mm", category="measurements"),
                ProductAttribute(key="material", value="glass", category="physical"),
                ProductAttribute(key="color", value="frosted blue", category="visual"),
            ],
        )
        specs = build_product_specs(product)

        assert specs.product_name == "Night Cream"
        assert specs.product_slug == "night-cream"
        assert specs.height_mm == 100.0
        assert specs.width_mm == 50.0
        assert "glass" in specs.materials
        assert "frosted blue" in specs.colors
        assert specs.height_width_ratio == 2.0

    def test_build_extracts_from_description_fallback(self):
        """Test falling back to description for dimensions."""
        product = ProductFull(
            slug="cream",
            name="Cream",
            description="A jar with height: 80mm and width: 60mm",
            attributes=[],
        )
        specs = build_product_specs(product)

        assert specs.height_mm == 80.0
        assert specs.width_mm == 60.0

    def test_build_extracts_triplet_dimensions(self):
        """Test extracting triplet format dimensions (H x W x D)."""
        product = ProductFull(
            slug="box",
            name="Box",
            description="A product box measuring 100 x 50 x 30 mm",
            attributes=[],
        )
        specs = build_product_specs(product)

        assert specs.height_mm == 100.0
        assert specs.width_mm == 50.0
        assert specs.depth_mm == 30.0
        assert specs.height_width_ratio == 2.0

    def test_build_with_finish_attributes(self):
        """Test extracting finish attributes."""
        product = ProductFull(
            slug="bottle",
            name="Bottle",
            description="",
            attributes=[
                ProductAttribute(key="finish", value="matte", category="visual"),
                ProductAttribute(key="surface", value="smooth", category="physical"),
            ],
        )
        specs = build_product_specs(product)

        assert "matte" in specs.finishes
        assert "smooth" in specs.finishes

    def test_build_with_distinguishers(self):
        """Test extracting distinguishing features."""
        product = ProductFull(
            slug="bottle",
            name="Bottle",
            description="",
            attributes=[
                ProductAttribute(key="cap", value="gold pump", category="design"),
                ProductAttribute(key="label", value="center front", category="design"),
            ],
        )
        specs = build_product_specs(product)

        assert len(specs.distinguishers) == 2
        assert any("gold pump" in d for d in specs.distinguishers)


class TestPackagingTextSpecs:
    """Tests for packaging text in product specs."""

    def test_build_with_packaging_text(self):
        """Test building specs includes packaging text."""
        product = ProductFull(
            slug="bottle",
            name="Bottle",
            description="",
            packaging_text=PackagingTextDescription(
                elements=[
                    PackagingTextElement(
                        text="BRAND NAME",
                        typography="sans-serif",
                        emphasis="bold",
                        position="front-center",
                    ),
                    PackagingTextElement(text="50ml", typography="serif", position="bottom"),
                ]
            ),
        )
        specs = build_product_specs(product)
        assert '"BRAND NAME"' in specs.packaging_text
        assert "sans-serif" in specs.packaging_text
        assert "bold" in specs.packaging_text
        assert "front-center" in specs.packaging_text
        assert '"50ml"' in specs.packaging_text

    def test_packaging_text_with_disambiguation(self):
        """Test packaging text includes disambiguation notes."""
        product = ProductFull(
            slug="jar",
            name="Jar",
            description="",
            packaging_text=PackagingTextDescription(
                elements=[PackagingTextElement(text="OLAY", notes="letter O not zero")]
            ),
        )
        specs = build_product_specs(product)
        assert '"OLAY"' in specs.packaging_text
        assert "[letter O not zero]" in specs.packaging_text

    def test_packaging_text_filters_long_elements(self):
        """Test elements over 80 chars are filtered out."""
        long_text = "A" * 81
        product = ProductFull(
            slug="box",
            name="Box",
            description="",
            packaging_text=PackagingTextDescription(
                elements=[PackagingTextElement(text=long_text), PackagingTextElement(text="SHORT")]
            ),
        )
        specs = build_product_specs(product)
        assert "SHORT" in specs.packaging_text
        assert long_text not in specs.packaging_text

    def test_packaging_text_includes_all_elements(self):
        """Test all valid elements are included (text fidelity is critical)."""
        product = ProductFull(
            slug="box",
            name="Box",
            description="",
            packaging_text=PackagingTextDescription(
                elements=[PackagingTextElement(text=f"TEXT{i}") for i in range(7)]
            ),
        )
        specs = build_product_specs(product)
        assert '"TEXT0"' in specs.packaging_text
        assert '"TEXT4"' in specs.packaging_text
        assert '"TEXT5"' in specs.packaging_text
        assert '"TEXT6"' in specs.packaging_text

    def test_packaging_text_none_unchanged(self):
        """Test products without packaging_text don't have it in specs."""
        product = ProductFull(slug="plain", name="Plain", description="A product")
        specs = build_product_specs(product)
        assert specs.packaging_text == ""

    def test_packaging_text_in_prompt_block(self):
        """Test packaging text appears in prompt block."""
        specs = ProductSpecs(
            product_name="Test",
            product_slug="test",
            packaging_text='"BRAND" (sans-serif, bold) at front',
        )
        block = specs.to_prompt_block()
        assert "Packaging text:" in block
        assert '"BRAND"' in block
        assert "[REPRODUCE EXACTLY]" in block

    def test_has_structured_data_with_packaging_text(self):
        """Test has_structured_data returns True with packaging_text."""
        specs = ProductSpecs(product_name="Test", product_slug="test", packaging_text='"TEXT"')
        assert specs.has_structured_data() is True

    def test_packaging_text_escapes_special_chars(self):
        """Test special characters are properly escaped."""
        product = ProductFull(
            slug="item",
            name="Item",
            description="",
            packaging_text=PackagingTextDescription(
                elements=[PackagingTextElement(text='Say "Hello"')]
            ),
        )
        specs = build_product_specs(product)
        # json.dumps escapes quotes as \"
        assert r"\"Hello\"" in specs.packaging_text
