"""Style Reference models for visual consistency."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator


class CanvasSpec(BaseModel):
    """Canvas specification for template layout."""

    aspect_ratio: str = Field(description="Aspect ratio, e.g., '1:1', '16:9', '9:16'")
    background: str = Field(default="", description="Background description or color")
    width: int | None = Field(default=None, description="Optional width in pixels")
    height: int | None = Field(default=None, description="Optional height in pixels")

    @field_validator("background", mode="before")
    @classmethod
    def _normalize_background(cls, v):
        return "" if v is None else v


class MessageSpec(BaseModel):
    """Message intent and audience for template."""

    intent: str = Field(default="", description="Primary message intent, e.g., 'product launch'")
    audience: str = Field(default="", description="Target audience for this layout")
    key_claims: List[str] = Field(default_factory=list, description="Key claims or messages")

    @field_validator("intent", "audience", mode="before")
    @classmethod
    def _normalize_text(cls, v):
        return "" if v is None else v

    @field_validator("key_claims", mode="before")
    @classmethod
    def _normalize_claims(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class StyleSpec(BaseModel):
    """Visual style specification for template."""

    palette: List[str] = Field(default_factory=list, description="Color palette hex codes")
    lighting: str = Field(default="", description="Lighting style, e.g., 'soft natural'")
    mood: str = Field(default="", description="Overall mood, e.g., 'premium minimalist'")
    materials: List[str] = Field(default_factory=list, description="Featured materials/textures")

    @field_validator("lighting", "mood", mode="before")
    @classmethod
    def _normalize_text(cls, v):
        return "" if v is None else v

    @field_validator("palette", "materials", mode="before")
    @classmethod
    def _normalize_lists(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class GeometrySpec(BaseModel):
    """Position and size specification for layout elements."""

    x: float = Field(description="X position as fraction of canvas width (0-1)")
    y: float = Field(description="Y position as fraction of canvas height (0-1)")
    width: float = Field(description="Width as fraction of canvas width (0-1)")
    height: float = Field(description="Height as fraction of canvas height (0-1)")
    rotation: float = Field(default=0.0, description="Rotation in degrees")
    z_index: int = Field(default=0, description="Layer order (higher = front)")


class AppearanceSpec(BaseModel):
    """Visual appearance specification for layout elements."""

    fill: str = Field(default="", description="Fill color or gradient")
    stroke: str = Field(default="", description="Stroke/border color")
    opacity: float = Field(default=1.0, description="Opacity 0-1")
    blur: float = Field(default=0.0, description="Blur amount")
    shadow: str = Field(default="", description="Shadow specification")

    @field_validator("fill", "stroke", "shadow", mode="before")
    @classmethod
    def _normalize_text(cls, v):
        return "" if v is None else v

    @field_validator("opacity", "blur", mode="before")
    @classmethod
    def _normalize_floats(cls, v, info):
        if v is None:
            return 1.0 if info.field_name == "opacity" else 0.0
        return v


class ContentSpec(BaseModel):
    """Content specification for layout elements."""

    text: str = Field(default="", description="Text content if applicable")
    font_family: str = Field(default="", description="Font family")
    font_size: str = Field(default="", description="Font size relative to canvas")
    font_weight: str = Field(default="", description="Font weight")
    alignment: str = Field(default="", description="Text alignment")
    image_description: str = Field(default="", description="Image content description")

    @field_validator(
        "text",
        "font_family",
        "font_size",
        "font_weight",
        "alignment",
        "image_description",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, v):
        return "" if v is None else v


class ConstraintSpec(BaseModel):
    """Constraints for layout elements during generation."""

    locked_position: bool = Field(default=False, description="Position cannot change")
    locked_size: bool = Field(default=False, description="Size cannot change")
    locked_aspect: bool = Field(default=False, description="Aspect ratio must be preserved")
    min_margin: float = Field(default=0.0, description="Minimum margin from edges (0-1)")
    semantic_role: str = Field(default="", description="Semantic role for strict mode")

    @field_validator("locked_position", "locked_size", "locked_aspect", mode="before")
    @classmethod
    def _normalize_bools(cls, v):
        return False if v is None else v

    @field_validator("min_margin", mode="before")
    @classmethod
    def _normalize_margin(cls, v):
        return 0.0 if v is None else v

    @field_validator("semantic_role", mode="before")
    @classmethod
    def _normalize_role(cls, v):
        return "" if v is None else v


class LayoutElement(BaseModel):
    """Single element in the template layout."""

    id: str = Field(description="Unique element identifier")
    type: str = Field(description="Element type: 'image', 'text', 'shape', 'product'")
    role: str = Field(default="", description="Semantic role, e.g., 'headline'")
    geometry: GeometrySpec = Field(
        default_factory=lambda: GeometrySpec(x=0.0, y=0.0, width=1.0, height=1.0),
        description="Position/size",
    )
    appearance: AppearanceSpec = Field(default_factory=AppearanceSpec, description="Visual style")
    content: ContentSpec = Field(default_factory=ContentSpec, description="Content spec")
    constraints: ConstraintSpec = Field(default_factory=ConstraintSpec, description="Constraints")

    @field_validator("role", mode="before")
    @classmethod
    def _normalize_role(cls, v):
        return "" if v is None else v


class InteractionSpec(BaseModel):
    """Interaction specification for product slot."""

    replacement_mode: str = Field(default="replace", description="replace or overlay")
    preserve_shadow: bool = Field(default=True, description="Preserve original shadow")
    preserve_reflection: bool = Field(default=False, description="Preserve reflection")
    scale_mode: str = Field(default="fit", description="fit, fill, or stretch")

    @field_validator("replacement_mode", "scale_mode", mode="before")
    @classmethod
    def _normalize_text(cls, v, info):
        if v is None:
            return "replace" if info.field_name == "replacement_mode" else "fit"
        return v

    @field_validator("preserve_shadow", "preserve_reflection", mode="before")
    @classmethod
    def _normalize_bools(cls, v, info):
        if v is None:
            return True if info.field_name == "preserve_shadow" else False
        return v


class ProductSlot(BaseModel):
    """Product slot specification in template."""

    id: str = Field(description="Slot identifier")
    geometry: GeometrySpec = Field(description="Position and size for product")
    appearance: AppearanceSpec = Field(default_factory=AppearanceSpec, description="Visual style")
    interaction: InteractionSpec = Field(default_factory=InteractionSpec, description="Behavior")


class StyleReferenceAnalysis(BaseModel):
    """Style reference analysis from Gemini Vision (V1 - geometry-focused).
    This is the structured JSON representation of a style reference image,
    containing geometry, semantics, and style information.
    DEPRECATED: Use StyleReferenceAnalysisV2 for new style references."""

    version: str = Field(default="1.0", description="Analysis schema version")
    canvas: CanvasSpec = Field(description="Canvas specification")
    message: MessageSpec = Field(default_factory=MessageSpec, description="Message intent")
    style: StyleSpec = Field(default_factory=StyleSpec, description="Visual style")
    elements: List[LayoutElement] = Field(default_factory=list, description="Layout elements")
    product_slot: ProductSlot | None = Field(default=None, description="Product slot")


# V2 Style Reference Analysis Models - Semantic-focused
class VisualSceneSpec(BaseModel):
    """Description of non-text visual elements in the style reference."""

    scene_description: str = Field(default="", description="Overall visual scene in prose")
    product_placement: str = Field(default="", description="How/where product appears")
    lifestyle_elements: List[str] = Field(
        default_factory=list, description="Context elements (hands, props, surfaces)"
    )
    visual_treatments: List[str] = Field(
        default_factory=list, description="Design treatments (pill badges, drop shadow, gradient)"
    )
    photography_style: str = Field(
        default="", description="Photography style (lifestyle, studio, flat lay)"
    )

    @field_validator("scene_description", "product_placement", "photography_style", mode="before")
    @classmethod
    def _norm_str(cls, v):
        return "" if v is None else v

    @field_validator("lifestyle_elements", "visual_treatments", mode="before")
    @classmethod
    def _norm_list(cls, v):
        return [] if v is None else ([v] if isinstance(v, str) else v)


class LayoutStructureSpec(BaseModel):
    """Prose description of layout structure - no pixel coordinates."""

    structure: str = Field(
        description="Layout in prose, e.g., 'Two-column: text left, lifestyle right'"
    )
    zones: List[str] = Field(
        default_factory=list, description="Named zones (header, hero, benefits, footer)"
    )
    hierarchy: str = Field(default="", description="Visual hierarchy description")
    alignment: str = Field(default="", description="Alignment pattern (left-aligned, centered)")

    @field_validator("structure", "hierarchy", "alignment", mode="before")
    @classmethod
    def _norm_str(cls, v):
        return "" if v is None else v

    @field_validator("zones", mode="before")
    @classmethod
    def _norm_list(cls, v):
        return [] if v is None else ([v] if isinstance(v, str) else v)


class StyleReferenceConstraintsSpec(BaseModel):
    """What must vs. can change during generation."""

    non_negotiables: List[str] = Field(default_factory=list, description="MUST preserve exactly")
    creative_freedom: List[str] = Field(default_factory=list, description="CAN vary")
    product_integration: str = Field(
        default="", description="How to integrate product into style reference"
    )

    @field_validator("product_integration", mode="before")
    @classmethod
    def _norm_str(cls, v):
        return "" if v is None else v

    @field_validator("non_negotiables", "creative_freedom", mode="before")
    @classmethod
    def _norm_list(cls, v):
        return [] if v is None else ([v] if isinstance(v, str) else v)


class StyleReferenceAnalysisV2(BaseModel):
    """Semantic style reference analysis (V2) - focuses on meaning, not geometry.
    Captures prose layout descriptions, visual treatments, and scene elements
    instead of pixel coordinates."""

    version: str = Field(default="2.0", description="Analysis schema version")
    canvas: CanvasSpec = Field(description="Canvas spec (aspect_ratio, background)")
    style: StyleSpec = Field(
        default_factory=StyleSpec, description="Visual style (palette, mood, lighting)"
    )
    layout: LayoutStructureSpec = Field(description="Prose layout structure")
    visual_scene: VisualSceneSpec = Field(
        default_factory=VisualSceneSpec, description="Non-text visual elements"
    )
    constraints: StyleReferenceConstraintsSpec = Field(
        default_factory=StyleReferenceConstraintsSpec, description="What can/cannot change"
    )


class StyleReferenceSummary(BaseModel):
    """Compact style reference summary - L0 layer for quick loading.
    Used for style reference list display and sidebar."""

    slug: str = Field(description="URL-safe identifier, e.g., 'hero-centered'")
    name: str = Field(description="Style reference name, e.g., 'Hero Centered Layout'")
    description: str = Field(default="", description="Style reference description")
    primary_image: str = Field(default="", description="Brand-relative path to primary image")
    default_strict: bool = Field(default=True, description="Default strict toggle state")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Created at")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Updated at")


class StyleReferenceFull(BaseModel):
    """Complete style reference details - L1 layer loaded on demand.
    Contains style reference images and analysis results."""

    slug: str = Field(description="URL-safe identifier")
    name: str = Field(description="Style reference name")
    description: str = Field(default="", description="Style reference description")
    images: List[str] = Field(default_factory=list, description="Style reference image paths")
    primary_image: str = Field(default="", description="Primary image path")
    default_strict: bool = Field(default=True, description="Default strict toggle state")
    analysis: StyleReferenceAnalysis | StyleReferenceAnalysisV2 | None = Field(
        default=None, description="Gemini analysis (V1 or V2)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Created at")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Updated at")

    def to_summary(self) -> StyleReferenceSummary:
        """Extract a StyleReferenceSummary from this full style reference."""
        return StyleReferenceSummary(
            slug=self.slug,
            name=self.name,
            description=self.description,
            primary_image=self.primary_image,
            default_strict=self.default_strict,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class StyleReferenceIndex(BaseModel):
    """Registry of all style references for a brand.
    Stored at ~/.sip-videogen/brands/{brand-slug}/style_references/index.json"""

    version: str = Field(default="1.0", description="Index format version")
    style_references: List[StyleReferenceSummary] = Field(
        default_factory=list, description="Style references"
    )

    def get_style_reference(self, slug: str) -> StyleReferenceSummary | None:
        """Find a style reference by slug."""
        for t in self.style_references:
            if t.slug == slug:
                return t
        return None

    def add_style_reference(self, entry: StyleReferenceSummary) -> None:
        """Add or update a style reference in the index."""
        self.style_references = [t for t in self.style_references if t.slug != entry.slug]
        self.style_references.append(entry)

    def remove_style_reference(self, slug: str) -> bool:
        """Remove a style reference from the index. Returns True if found and removed."""
        n = len(self.style_references)
        self.style_references = [t for t in self.style_references if t.slug != slug]
        return len(self.style_references) < n
