"""Tests for V2 and V3 style reference analysis models and constraint builders."""

import pytest

from sip_videogen.advisor.style_reference_prompt import (
    build_style_reference_constraints_v2,
    build_style_reference_constraints_v3,
    format_v2_summary,
    format_v3_summary,
)
from sip_videogen.brands.models import (
    CanvasSpec,
    ColorGradingSpec,
    LayoutStructureSpec,
    StyleReferenceAnalysisV2,
    StyleReferenceAnalysisV3,
    StyleReferenceConstraintsSpec,
    StyleSpec,
    StyleSuggestionsSpec,
    VisualSceneSpec,
)


class TestV2Models:
    def test_visual_scene_spec(self):
        scene = VisualSceneSpec(
            scene_description="Woman holding product over blender",
            product_placement="Product jar in hands",
            visual_treatments=["rounded pill badges", "soft shadow"],
            photography_style="lifestyle",
        )
        assert "blender" in scene.scene_description
        assert len(scene.visual_treatments) == 2

    def test_layout_structure_spec(self):
        layout = LayoutStructureSpec(
            structure="Two-column: text left, lifestyle right",
            zones=["headline", "benefits", "hero"],
            hierarchy="Headline first, benefits second",
            alignment="left-aligned text",
        )
        assert "Two-column" in layout.structure
        assert len(layout.zones) == 3

    def test_style_reference_constraints_spec(self):
        constraints = StyleReferenceConstraintsSpec(
            non_negotiables=["layout structure", "visual treatments"],
            creative_freedom=["background can vary"],
            product_integration="Replace product in hero area",
        )
        assert len(constraints.non_negotiables) == 2
        assert "layout" in constraints.non_negotiables[0]

    def test_style_reference_analysis_v2_full(self):
        analysis = StyleReferenceAnalysisV2(
            canvas=CanvasSpec(aspect_ratio="1:1", background="Light gray"),
            style=StyleSpec(palette=["#F0F0F0", "#333333"], mood="Clean", lighting="Soft natural"),
            layout=LayoutStructureSpec(structure="Two-column split"),
            visual_scene=VisualSceneSpec(scene_description="Lifestyle product shot"),
            constraints=StyleReferenceConstraintsSpec(non_negotiables=["layout preserved"]),
        )
        assert analysis.version == "2.0"
        assert analysis.canvas.aspect_ratio == "1:1"
        assert analysis.style.mood == "Clean"


class TestV2ConstraintBuilder:
    @pytest.fixture
    def sample_v2_analysis(self):
        return StyleReferenceAnalysisV2(
            canvas=CanvasSpec(aspect_ratio="1:1", background="Light gray"),
            style=StyleSpec(
                palette=["#F0F0F0", "#333333"], mood="Clean and healthy", lighting="Soft natural"
            ),
            layout=LayoutStructureSpec(
                structure="Two-column: text stacked left, lifestyle image right",
                zones=["headline zone", "benefits area", "hero image"],
                hierarchy="Headline draws eye first",
                alignment="left-aligned text",
            ),
            visual_scene=VisualSceneSpec(
                scene_description="Woman holding product jar over blender",
                product_placement="Product in hands on right side",
                visual_treatments=["rounded pill badges for benefits", "soft drop shadow"],
                photography_style="lifestyle with human interaction",
            ),
            constraints=StyleReferenceConstraintsSpec(
                non_negotiables=["Layout structure preserved", "Visual treatments replicated"],
                creative_freedom=["Background setting can change"],
                product_integration="Replace product in hero area",
            ),
        )

    def test_strict_mode_includes_layout(self, sample_v2_analysis):
        result = build_style_reference_constraints_v2(sample_v2_analysis, strict=True)
        assert "Two-column" in result
        assert "Layout Structure" in result

    def test_strict_mode_includes_treatments(self, sample_v2_analysis):
        result = build_style_reference_constraints_v2(sample_v2_analysis, strict=True)
        assert "pill badges" in result

    def test_strict_mode_includes_scene(self, sample_v2_analysis):
        result = build_style_reference_constraints_v2(sample_v2_analysis, strict=True)
        assert "blender" in result
        assert "Visual Scene" in result

    def test_loose_mode_includes_creative_freedom(self, sample_v2_analysis):
        result = build_style_reference_constraints_v2(sample_v2_analysis, strict=False)
        assert "Background" in result or "CREATIVE FREEDOM" in result

    def test_loose_mode_preserves_mood(self, sample_v2_analysis):
        result = build_style_reference_constraints_v2(sample_v2_analysis, strict=False)
        assert "Clean" in result or "mood" in result.lower()

    def test_format_v2_summary(self, sample_v2_analysis):
        result = format_v2_summary(sample_v2_analysis)
        assert "V2:" in result
        assert "2 treatments" in result


# V3 Color Grading DNA Tests
class TestV3Models:
    def test_color_grading_spec(self):
        cg = ColorGradingSpec(
            color_temperature="warm golden (+500K)",
            shadow_tint="warm brown",
            black_point="lifted/milky",
            highlight_rolloff="soft film-like",
            highlight_tint="warm cream",
            saturation_level="desaturated/muted",
            contrast_character="low/flat",
            film_stock_reference="Kodak Portra 400",
            signature_elements=["lifted blacks", "warm skin tones", "neon accent pop"],
        )
        assert "warm" in cg.color_temperature
        assert "Portra" in cg.film_stock_reference
        assert len(cg.signature_elements) == 3

    def test_color_grading_spec_defaults(self):
        cg = ColorGradingSpec()
        assert cg.color_temperature == ""
        assert cg.shadow_tint == ""
        assert cg.signature_elements == []

    def test_style_suggestions_spec(self):
        suggestions = StyleSuggestionsSpec(
            environment_tendency="urban/industrial",
            mood="energetic, authentic",
            lighting_setup="natural diffused daylight",
        )
        assert "urban" in suggestions.environment_tendency
        assert "energetic" in suggestions.mood

    def test_style_reference_analysis_v3_full(self):
        analysis = StyleReferenceAnalysisV3(
            canvas=CanvasSpec(aspect_ratio="4:5"),
            color_grading=ColorGradingSpec(
                color_temperature="warm golden",
                film_stock_reference="Kodak Portra 400",
                signature_elements=["lifted blacks", "warm skin tones"],
            ),
            style_suggestions=StyleSuggestionsSpec(mood="energetic"),
        )
        assert analysis.version == "3.0"
        assert analysis.canvas.aspect_ratio == "4:5"
        assert "Portra" in analysis.color_grading.film_stock_reference

    def test_v3_backward_compat_with_none_fields(self):
        """V3 should handle None values gracefully."""
        cg = ColorGradingSpec(color_temperature=None, signature_elements=None)  # type: ignore
        assert cg.color_temperature == ""
        assert cg.signature_elements == []


class TestV3ConstraintBuilder:
    @pytest.fixture
    def sample_v3_analysis(self):
        return StyleReferenceAnalysisV3(
            canvas=CanvasSpec(aspect_ratio="4:5"),
            color_grading=ColorGradingSpec(
                color_temperature="warm golden (+500K)",
                shadow_tint="warm brown shadows",
                black_point="lifted/milky",
                highlight_rolloff="soft film-like",
                highlight_tint="warm cream",
                saturation_level="desaturated/muted with selective accent saturation",
                contrast_character="low/flat",
                film_stock_reference="Kodak Portra 400",
                signature_elements=[
                    "lifted blacks with brown tint",
                    "warm skin tones",
                    "neon accent pop",
                ],
            ),
            style_suggestions=StyleSuggestionsSpec(
                environment_tendency="urban/industrial outdoor",
                mood="energetic, authentic",
                lighting_setup="natural diffused daylight",
            ),
        )

    def test_strict_mode_includes_color_grading(self, sample_v3_analysis):
        result = build_style_reference_constraints_v3(sample_v3_analysis, strict=True)
        assert "COLOR GRADING DNA" in result
        assert "HIGHEST PRIORITY" in result

    def test_strict_mode_includes_film_reference(self, sample_v3_analysis):
        result = build_style_reference_constraints_v3(sample_v3_analysis, strict=True)
        assert "Portra 400" in result
        assert "Film Look" in result

    def test_strict_mode_includes_temperature(self, sample_v3_analysis):
        result = build_style_reference_constraints_v3(sample_v3_analysis, strict=True)
        assert "warm golden" in result
        assert "Temperature" in result

    def test_strict_mode_includes_shadow_treatment(self, sample_v3_analysis):
        result = build_style_reference_constraints_v3(sample_v3_analysis, strict=True)
        assert "lifted" in result
        assert "Shadows" in result

    def test_strict_mode_includes_signature(self, sample_v3_analysis):
        result = build_style_reference_constraints_v3(sample_v3_analysis, strict=True)
        assert "Signature" in result
        assert "lifted blacks" in result

    def test_loose_mode_allows_variation(self, sample_v3_analysis):
        result = build_style_reference_constraints_v3(sample_v3_analysis, strict=False)
        assert "LOOSE MODE" in result
        assert "COLOR FAMILY MATCHING" in result

    def test_loose_mode_preserves_direction(self, sample_v3_analysis):
        result = build_style_reference_constraints_v3(sample_v3_analysis, strict=False)
        assert "warm stays warm" in result

    def test_style_suggestions_included(self, sample_v3_analysis):
        result = build_style_reference_constraints_v3(sample_v3_analysis, strict=True)
        assert "urban" in result or "Environment" in result
        assert "SUGGESTIONS" in result

    def test_format_v3_summary(self, sample_v3_analysis):
        result = format_v3_summary(sample_v3_analysis)
        assert "V3:" in result
        assert "Portra" in result
        assert "3 signatures" in result
