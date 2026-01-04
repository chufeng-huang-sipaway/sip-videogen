"""Tests for V2 style reference analysis models and constraint builder."""

import pytest

from sip_videogen.advisor.style_reference_prompt import (
    build_style_reference_constraints_v2,
    format_v2_summary,
)
from sip_videogen.brands.models import (
    CanvasSpec,
    CopywritingSpec,
    LayoutStructureSpec,
    StyleReferenceAnalysisV2,
    StyleReferenceConstraintsSpec,
    StyleSpec,
    VisualSceneSpec,
)


class TestV2Models:
    def test_copywriting_spec_basic(self):
        copy = CopywritingSpec(
            headline="One Scoop Per Day",
            benefits=["Support Metabolism*†", "Support Digestion*†"],
            disclaimer="*Results vary",
        )
        assert copy.headline == "One Scoop Per Day"
        assert len(copy.benefits) == 2
        assert copy.benefits[0] == "Support Metabolism*†"

    def test_copywriting_spec_defaults(self):
        copy = CopywritingSpec()
        assert copy.headline == ""
        assert copy.benefits == []
        assert copy.disclaimer == ""

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
            non_negotiables=["verbatim copy", "two-column layout"],
            creative_freedom=["background can vary"],
            product_integration="Replace product in hero area",
        )
        assert len(constraints.non_negotiables) == 2
        assert "verbatim" in constraints.non_negotiables[0]

    def test_style_reference_analysis_v2_full(self):
        analysis = StyleReferenceAnalysisV2(
            canvas=CanvasSpec(aspect_ratio="1:1", background="Light gray"),
            style=StyleSpec(palette=["#F0F0F0", "#333333"], mood="Clean", lighting="Soft natural"),
            layout=LayoutStructureSpec(structure="Two-column split"),
            copywriting=CopywritingSpec(
                headline="One Scoop Per Day Can Help:", benefits=["Support Metabolism*†"]
            ),
            visual_scene=VisualSceneSpec(scene_description="Lifestyle product shot"),
            constraints=StyleReferenceConstraintsSpec(non_negotiables=["verbatim copy"]),
        )
        assert analysis.version == "2.0"
        assert analysis.canvas.aspect_ratio == "1:1"
        assert analysis.copywriting.headline == "One Scoop Per Day Can Help:"


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
            copywriting=CopywritingSpec(
                headline="One Scoop Per Day Can Help:",
                benefits=[
                    "Support Healthy Metabolism*†",
                    "Support Smooth Digestion*†",
                    "Support Sustained Energy*†",
                ],
                disclaimer="*Results may vary.",
            ),
            visual_scene=VisualSceneSpec(
                scene_description="Woman holding product jar over blender",
                product_placement="Product in hands on right side",
                visual_treatments=["rounded pill badges for benefits", "soft drop shadow"],
                photography_style="lifestyle with human interaction",
            ),
            constraints=StyleReferenceConstraintsSpec(
                non_negotiables=["All copywriting verbatim", "Two-column layout"],
                creative_freedom=["Background setting can change"],
                product_integration="Replace product in hero area",
            ),
        )

    def test_strict_mode_includes_verbatim_copy(self, sample_v2_analysis):
        result = build_style_reference_constraints_v2(sample_v2_analysis, strict=True)
        assert "One Scoop Per Day Can Help:" in result
        assert "Support Healthy Metabolism*†" in result
        assert "VERBATIM" in result

    def test_strict_mode_includes_layout(self, sample_v2_analysis):
        result = build_style_reference_constraints_v2(sample_v2_analysis, strict=True)
        assert "Two-column" in result
        assert "Layout Structure" in result

    def test_strict_mode_includes_treatments(self, sample_v2_analysis):
        result = build_style_reference_constraints_v2(sample_v2_analysis, strict=True)
        assert "pill badges" in result

    def test_loose_mode_still_includes_verbatim(self, sample_v2_analysis):
        result = build_style_reference_constraints_v2(sample_v2_analysis, strict=False)
        assert "One Scoop Per Day Can Help:" in result
        assert "VERBATIM" in result or "verbatim" in result.lower()

    def test_loose_mode_includes_creative_freedom(self, sample_v2_analysis):
        result = build_style_reference_constraints_v2(sample_v2_analysis, strict=False)
        assert "Background" in result or "CREATIVE FREEDOM" in result

    def test_format_v2_summary(self, sample_v2_analysis):
        result = format_v2_summary(sample_v2_analysis)
        assert "V2:" in result
        assert "3 benefits" in result
        assert "2 treatments" in result
