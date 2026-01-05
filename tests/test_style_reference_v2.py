"""Tests for V2 style reference analysis models and constraint builder."""

import pytest

from sip_videogen.advisor.style_reference_prompt import (
    build_style_reference_constraints_v2,
    format_v2_summary,
)
from sip_videogen.brands.models import (
    CanvasSpec,
    LayoutStructureSpec,
    StyleReferenceAnalysisV2,
    StyleReferenceConstraintsSpec,
    StyleSpec,
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
