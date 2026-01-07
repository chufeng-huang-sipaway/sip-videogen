"""Product models."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator


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
    product-specific characteristic."""

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
    Stored at ~/.sip-studio/brands/{brand-slug}/products/index.json"""

    version: str = Field(default="1.0", description="Index format version")
    products: List[ProductSummary] = Field(
        default_factory=list, description="List of product summaries"
    )

    def get_product(self, slug: str) -> ProductSummary | None:
        """Find a product by slug."""
        for p in self.products:
            if p.slug == slug:
                return p
        return None

    def add_product(self, entry: ProductSummary) -> None:
        """Add or update a product in the index."""
        self.products = [p for p in self.products if p.slug != entry.slug]
        self.products.append(entry)

    def remove_product(self, slug: str) -> bool:
        """Remove a product from the index. Returns True if found and removed."""
        n = len(self.products)
        self.products = [p for p in self.products if p.slug != slug]
        return len(self.products) < n
