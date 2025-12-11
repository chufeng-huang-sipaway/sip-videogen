"""Models for Brand Kit generation workflow.

These models capture the structured brief, creative directions,
prompt scaffolding, and generated assets used in the brand
design library flow.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class BrandAssetCategory(str, Enum):
    """Supported asset categories for the brand kit."""

    LOGO = "logo"
    PACKAGING = "packaging"
    LIFESTYLE = "lifestyle"
    MASCOT = "mascot"
    MARKETING = "marketing"


class BrandKitBrief(BaseModel):
    """Normalized brand brief distilled from freeform user input."""

    brand_name: str = Field(description="Name of the brand")
    product_category: str = Field(description="Category (e.g., beverage, bike, spread)")
    core_product: str = Field(description="Specific product or SKU to spotlight")
    target_audience: str = Field(description="Primary audience or customer persona")
    tone: str = Field(description="Overall tone (e.g., playful, luxurious, futuristic)")
    style_keywords: List[str] = Field(
        default_factory=list,
        description="Style anchors to keep consistent across assets",
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Must-haves (colors, motifs, materials, settings)",
    )
    avoid: List[str] = Field(
        default_factory=list,
        description="Avoidances (colors, motifs, materials, settings)",
    )
    reference_notes: str | None = Field(
        default=None,
        description="Notes about reference images or prior assets (optional)",
    )


class BrandDirection(BaseModel):
    """A creative direction to explore."""

    id: str = Field(description="Stable identifier for this direction")
    label: str = Field(description="Short name/title for the direction")
    summary: str = Field(description="One-paragraph overview of the look/feel")
    tone: str | None = Field(
        default=None,
        description="Tone or personality emphasis for this direction",
    )
    style_keywords: List[str] = Field(
        default_factory=list,
        description="Key aesthetic anchors",
    )
    color_palette: List[str] = Field(
        default_factory=list,
        description="Primary and secondary colors to reuse",
    )
    typography: str | None = Field(
        default=None,
        description="Type direction (families, weights, qualities)",
    )
    materials: List[str] = Field(
        default_factory=list,
        description="Materials/textures to emphasize (if applicable)",
    )
    settings: List[str] = Field(
        default_factory=list,
        description="Environment or context examples",
    )
    differentiator: str | None = Field(
        default=None,
        description="What makes this direction distinct from others",
    )


class BrandKitPlan(BaseModel):
    """Structured plan returned by the Brand Kit planning agent."""

    brief: BrandKitBrief = Field(description="Normalized brief for the brand kit")
    directions: List[BrandDirection] = Field(
        description="Three distinct directions for the user to pick from"
    )
    notes: str | None = Field(
        default=None,
        description="Any notable considerations or trade-offs",
    )


class BrandAssetPrompt(BaseModel):
    """Prompt prepared for a specific asset generation task."""

    id: str = Field(description="Identifier for this prompt within the run")
    category: BrandAssetCategory = Field(description="Which asset family this prompt belongs to")
    label: str = Field(description="Human-friendly label (e.g., 'Logo v1')")
    prompt: str = Field(description="Full text prompt to send to the image model")
    aspect_ratio: str = Field(
        default="1:1",
        description="Requested aspect ratio string (e.g., 1:1, 16:9)",
    )
    variants: int = Field(
        default=1,
        description="How many images to request for this prompt",
    )


class BrandAssetResult(BaseModel):
    """Record of generated outputs for a single prompt."""

    prompt_id: str = Field(description="ID of the BrandAssetPrompt used")
    category: BrandAssetCategory = Field(description="Asset category")
    label: str = Field(description="Human-friendly label (same as prompt label)")
    prompt_used: str = Field(description="Exact prompt used for generation")
    image_paths: List[str] = Field(
        default_factory=list,
        description="Local filesystem paths for generated images",
    )


class BrandKitPackage(BaseModel):
    """Complete set of outputs for a brand kit run."""

    brief: BrandKitBrief = Field(description="Normalized brief")
    selected_direction: BrandDirection = Field(description="Chosen creative direction")
    asset_results: List[BrandAssetResult] = Field(
        default_factory=list,
        description="Generated assets grouped by prompt",
    )
    output_dir: str = Field(description="Base directory where assets are stored")
    selected_logo_path: str | None = Field(
        default=None,
        description="Chosen logo image path for downstream use",
    )
