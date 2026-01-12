"""Visual Directive models - translated brand identity for image generation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class RuleScope(str, Enum):
    """Scope of a learned rule."""

    BRAND = "brand"
    PROJECT = "project"


class TargetRepresentation(BaseModel):
    """Who should appear in lifestyle/marketing images."""

    description: str = Field(
        default="",
        description="Primary subject description, e.g., 'Women 35-45, confident, established'",
    )
    age_range: str = Field(default="", description="Target age range for human subjects")
    gender: str = Field(default="", description="Gender if relevant")
    style_descriptors: List[str] = Field(
        default_factory=list,
        description="Style/appearance keywords, e.g., ['professional', 'approachable']",
    )
    avoid: List[str] = Field(
        default_factory=list, description="What to avoid in subject representation"
    )


class ColorGuidelines(BaseModel):
    """Color direction for image generation."""

    primary_palette: List[str] = Field(
        default_factory=list, description="Primary colors to emphasize (hex codes)"
    )
    mood_colors: List[str] = Field(
        default_factory=list, description="Colors that evoke the brand mood"
    )
    temperature: str = Field(
        default="", description="Overall color temperature: warm, cool, neutral"
    )
    saturation: str = Field(
        default="", description="Saturation preference: vibrant, muted, natural"
    )
    avoid_colors: List[str] = Field(default_factory=list, description="Colors to avoid")


class MoodGuidelines(BaseModel):
    """Emotional atmosphere for images."""

    primary_mood: str = Field(
        default="", description="Primary emotional quality, e.g., 'inviting', 'energetic'"
    )
    mood_keywords: List[str] = Field(
        default_factory=list, description="Keywords describing desired atmosphere"
    )
    lighting_preference: str = Field(
        default="", description="Lighting direction, e.g., 'soft natural', 'dramatic studio'"
    )
    environment_feel: str = Field(
        default="", description="Environmental atmosphere, e.g., 'cozy indoor', 'bright outdoor'"
    )


class PhotographyStyle(BaseModel):
    """Photography/visual style guidelines."""

    style_description: str = Field(default="", description="Overall photography style description")
    composition_notes: List[str] = Field(
        default_factory=list, description="Composition preferences"
    )
    texture_materials: List[str] = Field(
        default_factory=list, description="Materials/textures to feature"
    )
    depth_of_field: str = Field(
        default="", description="DoF preference: shallow, deep, varies by context"
    )


class LearnedRule(BaseModel):
    """A rule learned from user feedback patterns."""

    rule: str = Field(description="The learned rule/preference")
    scope: RuleScope = Field(default=RuleScope.BRAND, description="brand or project level")
    project_slug: str | None = Field(
        default=None, description="If project-scoped, the project slug"
    )
    confidence: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Confidence score 0-1, increases with confirmations",
    )
    occurrences: int = Field(default=3, description="Number of times this pattern was observed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_confirmed: datetime = Field(default_factory=datetime.utcnow)
    source_category: str = Field(
        default="", description="Category of feedback: subject_age, color_temperature, etc."
    )


class VisualDirective(BaseModel):
    """Visual rules for image generation - derived from brand identity.
    This is a single file per brand (not indexed like products/styles).
    Stored at: ~/.sip-studio/brands/{slug}/visual_directive.json"""

    # Metadata
    version: int = Field(default=1, description="Directive version, increments on updates")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_from_identity_at: datetime | None = Field(
        default=None, description="When this was generated from brand identity"
    )
    # Core visual rules (derived from brand identity)
    target_representation: TargetRepresentation = Field(
        default_factory=TargetRepresentation, description="Who should appear in images"
    )
    color_guidelines: ColorGuidelines = Field(
        default_factory=ColorGuidelines, description="Color direction"
    )
    mood_guidelines: MoodGuidelines = Field(
        default_factory=MoodGuidelines, description="Emotional atmosphere"
    )
    photography_style: PhotographyStyle = Field(
        default_factory=PhotographyStyle, description="Visual style guidelines"
    )
    # Do's and Don'ts
    always_include: List[str] = Field(
        default_factory=list, description="Elements to always include or emphasize"
    )
    never_include: List[str] = Field(
        default_factory=list, description="Elements to never include - hard constraints"
    )
    # Learned preferences (from feedback patterns)
    learned_rules: List[LearnedRule] = Field(
        default_factory=list, description="Rules learned from user feedback"
    )

    def add_learned_rule(self, rule: LearnedRule) -> None:
        """Add or update a learned rule."""
        # Check for existing rule with same content (include project_slug for PROJECT scope)
        for i, r in enumerate(self.learned_rules):
            if (
                r.rule.lower() == rule.rule.lower()
                and r.scope == rule.scope
                and r.project_slug == rule.project_slug
            ):
                # Update existing
                self.learned_rules[i].confidence = min(1.0, r.confidence + 0.1)
                self.learned_rules[i].occurrences += 1
                self.learned_rules[i].last_confirmed = datetime.utcnow()
                return
        self.learned_rules.append(rule)

    def remove_learned_rule(self, rule_text: str) -> bool:
        """Remove a learned rule by its text. Returns True if removed."""
        n = len(self.learned_rules)
        self.learned_rules = [r for r in self.learned_rules if r.rule.lower() != rule_text.lower()]
        return len(self.learned_rules) < n

    def get_rules_for_project(self, project_slug: str | None) -> List[LearnedRule]:
        """Get learned rules applicable to a project (brand-level + project-specific)."""
        return [
            r
            for r in self.learned_rules
            if r.scope == RuleScope.BRAND
            or (r.scope == RuleScope.PROJECT and r.project_slug == project_slug)
        ]


# Feedback tracking models
class FeedbackInstance(BaseModel):
    """A single user correction/feedback instance."""

    id: str = Field(description="Unique feedback ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str = Field(default="", description="Session identifier")
    brand_slug: str = Field(description="Brand this feedback applies to")
    project_slug: str | None = Field(default=None, description="Project context if any")
    # The correction
    user_message: str = Field(description="User's correction, e.g., 'Make her older'")
    category: str | None = Field(
        default=None, description="AI-determined category: subject_age, color_temperature, etc."
    )
    # Context when correction was made
    original_prompt: str = Field(
        default="", description="The prompt that generated the rejected image"
    )
    attached_products: List[str] = Field(
        default_factory=list, description="Products attached during generation"
    )
    attached_style: str | None = Field(
        default=None, description="Style reference attached during generation"
    )
    # Processing status
    processed: bool = Field(
        default=False, description="Whether this feedback has been analyzed for patterns"
    )
    contributed_to_rule: str | None = Field(
        default=None, description="If processed, the rule it contributed to"
    )


class FeedbackLog(BaseModel):
    """Collection of feedback instances for a brand.
    Stored at: ~/.sip-studio/brands/{slug}/feedback_log.json"""

    version: str = Field(default="1.0")
    brand_slug: str = Field(description="Brand this log belongs to")
    instances: List[FeedbackInstance] = Field(default_factory=list)
    last_pattern_analysis: datetime | None = Field(
        default=None, description="When patterns were last analyzed"
    )

    def add_feedback(self, feedback: FeedbackInstance) -> None:
        """Add a feedback instance."""
        self.instances.append(feedback)

    def get_unprocessed(self) -> List[FeedbackInstance]:
        """Get feedback instances not yet processed for patterns."""
        return [f for f in self.instances if not f.processed]

    def get_by_category(self, category: str) -> List[FeedbackInstance]:
        """Get feedback instances by category."""
        return [f for f in self.instances if f.category == category]

    def mark_processed(self, feedback_ids: List[str], rule_text: str) -> None:
        """Mark feedback instances as processed."""
        for f in self.instances:
            if f.id in feedback_ids:
                f.processed = True
                f.contributed_to_rule = rule_text
