"""Data models for brand identity and memory.

This module defines the hierarchical brand identity models:
- BrandSummary: L0 layer, always in agent context (~500 tokens)
- BrandIdentityFull: L1 layer, loaded on demand
- Supporting models for visual identity, voice, audience, positioning

Product models:
- ProductSummary: L0 layer for product list display
- ProductFull: L1 layer with full product details

Project models:
- ProjectSummary: L0 layer for project list display
- ProjectFull: L1 layer with project instructions
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator


class BrandSummary(BaseModel):
    """Compact brand summary - always present in agent context.

    This is the L0 layer of brand memory. Keep it under ~500 tokens.
    Includes pointers to deeper layers so agents know what else exists.
    """

    # Core Identity (required)
    slug: str = Field(description="URL-safe identifier, e.g., 'summit-coffee'")
    name: str = Field(description="Official brand name, e.g., 'Summit Coffee Co.'")
    tagline: str = Field(description="One-line positioning statement")
    category: str = Field(description="Product category, e.g., 'Coffee', 'Skincare'")
    tone: str = Field(description="2-3 adjectives describing brand personality")

    # Visual Essence (condensed)
    primary_colors: List[str] = Field(
        default_factory=list,
        description="Up to 3 hex color codes, e.g., ['#2C3E50', '#8B7355']",
    )
    visual_style: str = Field(
        default="",
        description="One sentence describing visual direction",
    )
    logo_path: str = Field(
        default="",
        description="Path to primary logo file (empty string if none)",
    )

    # Audience Essence
    audience_summary: str = Field(
        default="",
        description="One sentence describing target audience",
    )

    # Memory Pointers (tells agents what details exist)
    available_details: List[str] = Field(
        default_factory=lambda: [
            "visual_identity",
            "voice_guidelines",
            "audience_profile",
            "positioning",
        ],
        description="List of detail types available via fetch_brand_detail()",
    )
    asset_count: int = Field(
        default=0,
        description="Total number of generated assets",
    )
    last_generation: str = Field(
        default="",
        description="ISO timestamp of last asset generation (empty if never)",
    )

    # Instruction for agents
    exploration_hint: str = Field(
        default=(
            "Use fetch_brand_detail() to access full visual identity, "
            "voice guidelines, audience profile, or positioning before making "
            "creative decisions."
        ),
        description="Hint text included in agent context",
    )


# =============================================================================
# Supporting Models for BrandIdentityFull (L1 Layer)
# =============================================================================


class ColorDefinition(BaseModel):
    """Single color in the brand palette."""

    hex: str = Field(description="Hex color code, e.g., '#2C3E50'")
    name: str = Field(description="Human-readable name, e.g., 'Ocean Blue'")
    usage: str = Field(
        default="",
        description="When to use this color, e.g., 'Primary backgrounds'",
    )


class TypographyRule(BaseModel):
    """Typography specification for a specific use case."""

    role: str = Field(description="Where used: 'headings', 'body', 'accent'")
    family: str = Field(description="Font family name, e.g., 'Inter'")
    weight: str = Field(default="regular", description="Font weight")
    style_notes: str = Field(
        default="",
        description="Additional guidance, e.g., 'Use for emphasis only'",
    )


class VisualIdentity(BaseModel):
    """Complete visual design system for the brand."""

    # Colors
    primary_colors: List[ColorDefinition] = Field(
        default_factory=list,
        description="Main brand colors (1-3)",
    )
    secondary_colors: List[ColorDefinition] = Field(
        default_factory=list,
        description="Supporting colors",
    )
    accent_colors: List[ColorDefinition] = Field(
        default_factory=list,
        description="Highlight/accent colors",
    )

    # Typography
    typography: List[TypographyRule] = Field(
        default_factory=list,
        description="Typography rules by use case",
    )

    # Imagery
    imagery_style: str = Field(
        default="",
        description="Photography/illustration style description",
    )
    imagery_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords for image generation, e.g., ['warm', 'natural light']",
    )
    imagery_avoid: List[str] = Field(
        default_factory=list,
        description="What to avoid in imagery",
    )

    # Materials & Textures
    materials: List[str] = Field(
        default_factory=list,
        description="Materials to feature, e.g., ['matte paper', 'brushed metal']",
    )

    # Logo
    logo_description: str = Field(
        default="",
        description="Description of the logo design",
    )
    logo_usage_rules: str = Field(
        default="",
        description="Rules for logo usage, e.g., minimum size, clear space",
    )

    # Overall
    overall_aesthetic: str = Field(
        default="",
        description="One paragraph describing the unified visual language",
    )
    style_keywords: List[str] = Field(
        default_factory=list,
        description="Style anchors, e.g., ['minimalist', 'premium', 'organic']",
    )


class VoiceGuidelines(BaseModel):
    """Brand voice and messaging guidelines."""

    personality: str = Field(
        default="",
        description="How the brand 'speaks' - personality description",
    )
    tone_attributes: List[str] = Field(
        default_factory=list,
        description="3-5 adjectives defining voice, e.g., ['warm', 'professional']",
    )

    # Messaging
    key_messages: List[str] = Field(
        default_factory=list,
        description="Core talking points",
    )
    messaging_do: List[str] = Field(
        default_factory=list,
        description="Messaging guidelines - what TO do",
    )
    messaging_dont: List[str] = Field(
        default_factory=list,
        description="Messaging guidelines - what NOT to do",
    )

    # Examples
    example_headlines: List[str] = Field(
        default_factory=list,
        description="Sample headlines in brand voice",
    )
    example_taglines: List[str] = Field(
        default_factory=list,
        description="Sample taglines in brand voice",
    )


class AudienceProfile(BaseModel):
    """Target audience definition."""

    primary_summary: str = Field(
        default="",
        description="One sentence audience description",
    )

    # Demographics
    age_range: str = Field(default="", description="Target age range")
    gender: str = Field(default="", description="Target gender if relevant")
    income_level: str = Field(default="", description="Income bracket if relevant")
    location: str = Field(default="", description="Geographic focus if relevant")

    # Psychographics
    interests: List[str] = Field(
        default_factory=list,
        description="Hobbies and interests",
    )
    values: List[str] = Field(
        default_factory=list,
        description="What they value",
    )
    lifestyle: str = Field(default="", description="Lifestyle description")

    # Pain Points & Desires
    pain_points: List[str] = Field(
        default_factory=list,
        description="Problems they face",
    )
    desires: List[str] = Field(
        default_factory=list,
        description="What they want to achieve",
    )


class CompetitivePositioning(BaseModel):
    """Market positioning and differentiation."""

    market_category: str = Field(
        default="",
        description="Market category the brand operates in",
    )
    unique_value_proposition: str = Field(
        default="",
        description="What makes this brand uniquely valuable",
    )

    # Competitors
    primary_competitors: List[str] = Field(
        default_factory=list,
        description="Main competitor names",
    )
    differentiation: str = Field(
        default="",
        description="How we're different from competitors",
    )

    # Positioning Statement
    positioning_statement: str = Field(
        default="",
        description=(
            "Formal positioning: '[Brand] is the [category] for [audience] "
            "who [need] because [reason]'"
        ),
    )


# =============================================================================
# BrandIdentityFull (L1 Layer - On Demand)
# =============================================================================


class BrandCoreIdentity(BaseModel):
    """Fundamental brand identity elements.

    All fields have defaults to allow BrandIdentityFull to be instantiated
    with just a slug. The name/tagline will be populated during brand creation.
    """

    name: str = Field(
        default="",
        description="Official brand name (required for complete brands)",
    )
    tagline: str = Field(
        default="",
        description="One-line positioning statement",
    )
    mission: str = Field(
        default="",
        description="2-3 sentence mission/purpose statement",
    )
    brand_story: str = Field(
        default="",
        description="Origin story and brand narrative",
    )
    values: List[str] = Field(
        default_factory=list,
        description="3-5 core brand values",
    )


class BrandIdentityFull(BaseModel):
    """Complete brand identity - the L1 layer loaded on demand.

    This contains everything needed to make informed brand decisions.
    Agents fetch this via fetch_brand_detail() when they need specifics.
    """

    # Metadata
    slug: str = Field(description="URL-safe identifier")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the brand was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the brand was last updated",
    )

    # Identity sections
    core: BrandCoreIdentity = Field(
        default_factory=BrandCoreIdentity,
        description="Core identity: name, mission, story, values",
    )
    visual: VisualIdentity = Field(
        default_factory=VisualIdentity,
        description="Visual design system",
    )
    voice: VoiceGuidelines = Field(
        default_factory=VoiceGuidelines,
        description="Voice and messaging guidelines",
    )
    audience: AudienceProfile = Field(
        default_factory=AudienceProfile,
        description="Target audience profile",
    )
    positioning: CompetitivePositioning = Field(
        default_factory=CompetitivePositioning,
        description="Market positioning",
    )

    # Constraints
    constraints: List[str] = Field(
        default_factory=list,
        description="Must-haves and requirements",
    )
    avoid: List[str] = Field(
        default_factory=list,
        description="Things to explicitly avoid",
    )

    def to_summary(self) -> BrandSummary:
        """Extract a BrandSummary from this full identity.

        Used when saving a brand to generate the L0 layer.
        """
        return BrandSummary(
            slug=self.slug,
            name=self.core.name,
            tagline=self.core.tagline,
            category=self.positioning.market_category or "Uncategorized",
            tone=(", ".join(self.voice.tone_attributes[:3]) if self.voice.tone_attributes else ""),
            primary_colors=[c.hex for c in self.visual.primary_colors[:3]],
            visual_style=(
                self.visual.overall_aesthetic[:200] if self.visual.overall_aesthetic else ""
            ),
            audience_summary=self.audience.primary_summary,
        )


# =============================================================================
# BrandIndex - Registry of All Brands
# =============================================================================


class BrandIndexEntry(BaseModel):
    """Entry in the brand index for quick listing."""

    slug: str = Field(description="URL-safe identifier")
    name: str = Field(description="Display name")
    category: str = Field(default="", description="Product category")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the brand was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the brand was last updated",
    )
    last_accessed: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the brand was last accessed",
    )


class BrandIndex(BaseModel):
    """Registry of all brands - stored at ~/.sip-videogen/brands/index.json."""

    version: str = Field(default="1.0", description="Index format version")
    brands: List[BrandIndexEntry] = Field(
        default_factory=list,
        description="List of registered brands",
    )
    active_brand: str | None = Field(
        default=None,
        description="Slug of the currently active brand",
    )

    def get_brand(self, slug: str) -> BrandIndexEntry | None:
        """Find a brand by slug."""
        for brand in self.brands:
            if brand.slug == slug:
                return brand
        return None

    def add_brand(self, entry: BrandIndexEntry) -> None:
        """Add a new brand to the index."""
        # Remove if exists (for updates)
        self.brands = [b for b in self.brands if b.slug != entry.slug]
        self.brands.append(entry)

    def remove_brand(self, slug: str) -> bool:
        """Remove a brand from the index. Returns True if found and removed."""
        original_len = len(self.brands)
        self.brands = [b for b in self.brands if b.slug != slug]

        # Clear active if it was the removed brand
        if self.active_brand == slug:
            self.active_brand = None

        return len(self.brands) < original_len


# =============================================================================
# Product Models
# =============================================================================


class PackagingTextElement(BaseModel):
    """Single text element on product packaging."""

    text: str = Field(description="Exact text content - literal characters only")
    notes: str = Field(
        default="",
        description="Disambiguation notes, e.g. 'letter O not zero', 'lowercase L not one'",
    )
    role: str = Field(
        default="other",
        description="brand_name|product_name|tagline|instructions|legal|decorative|other",
    )
    typography: str = Field(
        default="", description="serif|sans-serif|script|decorative|handwritten|geometric|monospace"
    )
    size: str = Field(default="", description="large|medium|small|tiny")
    color: str = Field(default="", description="Text color")
    position: str = Field(default="", description="Position on package")
    emphasis: str = Field(
        default="", description="bold|italic|all-caps|embossed|engraved|foil|metallic|printed"
    )

    @field_validator("notes", "typography", "size", "color", "position", "emphasis", mode="before")
    @classmethod
    def _norm_str(cls, v):
        return "" if v is None else v

    @field_validator("role", mode="before")
    @classmethod
    def _norm_role(cls, v):
        return "other" if v is None else v


class PackagingTextDescription(BaseModel):
    """Structured description of text on product packaging."""

    summary: str = Field(default="", description="Brief overview of text layout")
    elements: List[PackagingTextElement] = Field(default_factory=list)
    layout_notes: str = Field(default="", description="Text arrangement notes")
    # Metadata for freshness tracking
    source_image: str = Field(default="", description="Image path used for analysis")
    generated_at: datetime | None = Field(
        default=None, description="When AI analysis was performed"
    )
    edited_at: datetime | None = Field(default=None, description="When human last edited")
    is_human_edited: bool = Field(default=False, description="True if manually modified")


class ProductAttribute(BaseModel):
    """Single attribute of a product.

    Attributes can describe physical properties, use cases, or any
    product-specific characteristic.
    """

    key: str = Field(description="Attribute name, e.g., 'dimensions', 'material'")
    value: str = Field(description="Attribute value")
    category: str = Field(
        default="general",
        description="Attribute category: 'measurements', 'texture', 'use_case', etc.",
    )


class ProductSummary(BaseModel):
    """Compact product summary - L0 layer for quick loading.
    Used for product list display and context building."""

    slug: str = Field(description="URL-safe identifier, e.g., 'night-cream'")
    name: str = Field(description="Product name, e.g., 'Restorative Night Cream'")
    description: str = Field(description="English product description (i18n deferred)")
    primary_image: str = Field(
        default="",
        description="Brand-relative path to primary image, e.g., 'products/night-cream/images/main.png'",
    )
    attribute_count: int = Field(default=0, description="Number of attributes for quick reference")
    has_packaging_text: bool = Field(default=False, description="Whether packaging text analyzed")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the product was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the product was last updated"
    )


class ProductFull(BaseModel):
    """Complete product details - L1 layer loaded on demand.
    Contains all product information including images and attributes.
    All image paths are brand-relative (e.g., 'products/slug/images/file.png')."""

    slug: str = Field(description="URL-safe identifier")
    name: str = Field(description="Product name")
    description: str = Field(description="English product description (i18n deferred)")
    images: List[str] = Field(
        default_factory=list, description="Brand-relative paths to all product images"
    )
    primary_image: str = Field(
        default="", description="Brand-relative path to primary image (must be in images list)"
    )
    attributes: List[ProductAttribute] = Field(
        default_factory=list, description="Product attributes (dimensions, materials, etc.)"
    )
    packaging_text: PackagingTextDescription | None = Field(
        default=None, description="Structured description of packaging text"
    )
    # DEFERRED: visual_keywords, avoid_keywords
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the product was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the product was last updated"
    )

    def to_summary(self) -> ProductSummary:
        """Extract a ProductSummary from this full product.
        Used when saving a product to generate the L0 layer."""
        return ProductSummary(
            slug=self.slug,
            name=self.name,
            description=self.description,
            primary_image=self.primary_image,
            attribute_count=len(self.attributes),
            has_packaging_text=self.packaging_text is not None,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class ProductIndex(BaseModel):
    """Registry of all products for a brand.

    Stored at ~/.sip-videogen/brands/{brand-slug}/products/index.json
    """

    version: str = Field(default="1.0", description="Index format version")
    products: List[ProductSummary] = Field(
        default_factory=list,
        description="List of product summaries",
    )

    def get_product(self, slug: str) -> ProductSummary | None:
        """Find a product by slug."""
        for product in self.products:
            if product.slug == slug:
                return product
        return None

    def add_product(self, entry: ProductSummary) -> None:
        """Add or update a product in the index."""
        self.products = [p for p in self.products if p.slug != entry.slug]
        self.products.append(entry)

    def remove_product(self, slug: str) -> bool:
        """Remove a product from the index. Returns True if found and removed."""
        original_len = len(self.products)
        self.products = [p for p in self.products if p.slug != slug]
        return len(self.products) < original_len


# =============================================================================
# Project/Campaign Models
# =============================================================================


class ProjectStatus(str, Enum):
    """Project lifecycle status."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectSummary(BaseModel):
    """Compact project summary - L0 layer for quick loading.

    Used for project list display.
    """

    slug: str = Field(description="URL-safe identifier, e.g., 'christmas-campaign'")
    name: str = Field(description="Project name, e.g., 'Christmas 2024 Campaign'")
    status: ProjectStatus = Field(
        default=ProjectStatus.ACTIVE,
        description="Project status: active or archived",
    )
    asset_count: int = Field(
        default=0,
        description="Number of generated assets (from prefix search)",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the project was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the project was last updated",
    )


class ProjectFull(BaseModel):
    """Complete project details - L1 layer loaded on demand.

    Contains project instructions and metadata.
    Generated assets are tracked via filename prefix in assets/generated/.
    """

    slug: str = Field(description="URL-safe identifier")
    name: str = Field(description="Project name")
    status: ProjectStatus = Field(
        default=ProjectStatus.ACTIVE,
        description="Project status: active or archived",
    )
    instructions: str = Field(
        default="",
        description="Markdown instructions - campaign rules, guidelines, etc.",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the project was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the project was last updated",
    )

    def to_summary(self, asset_count: int = 0) -> ProjectSummary:
        """Extract a ProjectSummary from this full project.

        Used when saving a project to generate the L0 layer.
        asset_count must be provided as it requires filesystem access.
        """
        return ProjectSummary(
            slug=self.slug,
            name=self.name,
            status=self.status,
            asset_count=asset_count,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class ProjectIndex(BaseModel):
    """Registry of all projects for a brand.

    Stored at ~/.sip-videogen/brands/{brand-slug}/projects/index.json
    """

    version: str = Field(default="1.0", description="Index format version")
    projects: List[ProjectSummary] = Field(
        default_factory=list,
        description="List of project summaries",
    )
    active_project: str | None = Field(
        default=None,
        description="Slug of the currently active project",
    )

    def get_project(self, slug: str) -> ProjectSummary | None:
        """Find a project by slug."""
        for project in self.projects:
            if project.slug == slug:
                return project
        return None

    def add_project(self, entry: ProjectSummary) -> None:
        """Add or update a project in the index."""
        self.projects = [p for p in self.projects if p.slug != entry.slug]
        self.projects.append(entry)

    def remove_project(self, slug: str) -> bool:
        """Remove a project from the index. Returns True if found and removed."""
        original_len = len(self.projects)
        self.projects = [p for p in self.projects if p.slug != slug]

        # Clear active if it was the removed project
        if self.active_project == slug:
            self.active_project = None

        return len(self.projects) < original_len


# =============================================================================
# Style Reference Models - Style References for Visual Consistency
# =============================================================================


class CanvasSpec(BaseModel):
    """Canvas specification for template layout."""

    aspect_ratio: str = Field(description="Aspect ratio, e.g., '1:1', '16:9', '9:16'")
    background: str = Field(default="", description="Background description or color")
    width: int | None = Field(default=None, description="Optional width in pixels")
    height: int | None = Field(default=None, description="Optional height in pixels")

    @field_validator("background", mode="before")
    @classmethod
    def _normalize_background(cls, value):
        return "" if value is None else value


class MessageSpec(BaseModel):
    """Message intent and audience for template."""

    intent: str = Field(default="", description="Primary message intent, e.g., 'product launch'")
    audience: str = Field(default="", description="Target audience for this layout")
    key_claims: List[str] = Field(default_factory=list, description="Key claims or messages")

    @field_validator("intent", "audience", mode="before")
    @classmethod
    def _normalize_text(cls, value):
        return "" if value is None else value

    @field_validator("key_claims", mode="before")
    @classmethod
    def _normalize_claims(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value


class StyleSpec(BaseModel):
    """Visual style specification for template."""

    palette: List[str] = Field(default_factory=list, description="Color palette hex codes")
    lighting: str = Field(default="", description="Lighting style, e.g., 'soft natural'")
    mood: str = Field(default="", description="Overall mood, e.g., 'premium minimalist'")
    materials: List[str] = Field(default_factory=list, description="Featured materials/textures")

    @field_validator("lighting", "mood", mode="before")
    @classmethod
    def _normalize_text(cls, value):
        return "" if value is None else value

    @field_validator("palette", "materials", mode="before")
    @classmethod
    def _normalize_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value


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
    def _normalize_text(cls, value):
        return "" if value is None else value

    @field_validator("opacity", "blur", mode="before")
    @classmethod
    def _normalize_floats(cls, value, info):
        if value is None:
            return 1.0 if info.field_name == "opacity" else 0.0
        return value


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
    def _normalize_text(cls, value):
        return "" if value is None else value


class ConstraintSpec(BaseModel):
    """Constraints for layout elements during generation."""

    locked_position: bool = Field(default=False, description="Position cannot change")
    locked_size: bool = Field(default=False, description="Size cannot change")
    locked_aspect: bool = Field(default=False, description="Aspect ratio must be preserved")
    min_margin: float = Field(default=0.0, description="Minimum margin from edges (0-1)")
    semantic_role: str = Field(default="", description="Semantic role for strict mode")

    @field_validator("locked_position", "locked_size", "locked_aspect", mode="before")
    @classmethod
    def _normalize_bools(cls, value):
        return False if value is None else value

    @field_validator("min_margin", mode="before")
    @classmethod
    def _normalize_margin(cls, value):
        return 0.0 if value is None else value

    @field_validator("semantic_role", mode="before")
    @classmethod
    def _normalize_role(cls, value):
        return "" if value is None else value


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
    def _normalize_role(cls, value):
        return "" if value is None else value


class InteractionSpec(BaseModel):
    """Interaction specification for product slot."""

    replacement_mode: str = Field(default="replace", description="replace or overlay")
    preserve_shadow: bool = Field(default=True, description="Preserve original shadow")
    preserve_reflection: bool = Field(default=False, description="Preserve reflection")
    scale_mode: str = Field(default="fit", description="fit, fill, or stretch")

    @field_validator("replacement_mode", "scale_mode", mode="before")
    @classmethod
    def _normalize_text(cls, value, info):
        if value is None:
            return "replace" if info.field_name == "replacement_mode" else "fit"
        return value

    @field_validator("preserve_shadow", "preserve_reflection", mode="before")
    @classmethod
    def _normalize_bools(cls, value, info):
        if value is None:
            return True if info.field_name == "preserve_shadow" else False
        return value


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
    DEPRECATED: Use StyleReferenceAnalysisV2 for new style references.
    """

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

    Used for style reference list display and sidebar.
    """

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

    Stored at ~/.sip-videogen/brands/{brand-slug}/style_references/index.json
    """

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
