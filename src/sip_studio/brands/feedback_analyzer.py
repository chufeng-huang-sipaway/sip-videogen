"""Feedback Pattern Analyzer - detects patterns in user corrections."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

from agents import Agent, Runner
from pydantic import BaseModel, Field

from .models import FeedbackInstance, FeedbackLog, LearnedRule, RuleScope, VisualDirective
from .storage import (
    load_feedback_log,
    load_visual_directive,
    save_feedback_log,
    save_visual_directive,
)

logger = logging.getLogger(__name__)


class FeedbackAnalysis(BaseModel):
    """Analysis of a single feedback message."""

    is_correction: bool = Field(
        description="Whether this message is a correction/feedback about generated image"
    )
    category: str | None = Field(
        default=None,
        description="Category: subject_age, subject_gender, color_temperature, "
        "lighting, mood, composition, style, product_accuracy, other",
    )
    correction_intent: str = Field(
        default="", description="What the user wants changed, e.g., 'older model'"
    )


class PatternMatch(BaseModel):
    """A detected pattern from multiple feedback instances."""

    category: str = Field(description="The feedback category")
    rule_text: str = Field(description="The learned rule to add")
    scope: str = Field(default="brand", description="brand or project - where this rule applies")
    project_slug: str | None = Field(default=None, description="If project-scoped, which project")
    feedback_ids: list[str] = Field(
        default_factory=list, description="IDs of feedback that formed this pattern"
    )
    confidence: float = Field(default=0.6, description="Initial confidence score for this rule")


class PatternAnalysisResult(BaseModel):
    """Result of analyzing feedback patterns."""

    patterns_found: list[PatternMatch] = Field(default_factory=list)
    analysis_notes: str = Field(default="", description="Notes about the analysis")


# Agent for analyzing individual feedback messages
FEEDBACK_ANALYZER_INSTRUCTIONS = """\
You analyze user messages to determine if they are corrections/feedback about \
generated images.

## Your Task
Given a user message in the context of image generation, determine:
1. Is this a correction? (user wants something changed about the image)
2. What category does it fall into?
3. What is the user's intent?

## Categories
- subject_age: About age of people in image
- subject_gender: About gender of people in image
- subject_appearance: About clothing, style, look of people
- color_temperature: About warm/cool tones
- color_saturation: About vibrancy/muted colors
- lighting: About lighting quality/direction
- mood: About emotional atmosphere
- composition: About framing, layout, positioning
- style: About photography/artistic style
- product_accuracy: About product depiction accuracy
- environment: About setting/background
- other: Doesn't fit above categories

## Examples
- "Make her older" → is_correction=True, category=subject_age, intent="older model"
- "Too cold, warmer please" → is_correction=True, category=color_temperature, \
intent="warmer tones"
- "Can you add more products?" → is_correction=False (this is a new request)
- "The lighting feels harsh" → is_correction=True, category=lighting, \
intent="softer lighting"
"""

_feedback_analyzer = Agent(
    name="Feedback Analyzer",
    instructions=FEEDBACK_ANALYZER_INSTRUCTIONS,
    output_type=FeedbackAnalysis,
    model="gpt-4.1-mini",
)


# Agent for detecting patterns across multiple feedback instances
PATTERN_DETECTOR_INSTRUCTIONS = """\
You analyze multiple feedback instances to detect patterns and generate learned rules.

## Your Task
Given a list of feedback instances, determine:
1. Are there patterns (3+ similar corrections)?
2. What rules should be learned from these patterns?
3. Are the rules brand-level or project-specific?

## Guidelines
- Only suggest rules for clear, repeated patterns
- Be specific in rule text (actionable, not vague)
- Consider if pattern appears across all projects (brand-level) or one project
- A rule should prevent the same correction from being needed again

## Example Patterns
Feedback: ["Make her older", "She looks too young", "More mature model please"]
→ Rule: "Use models aged 35-45 for lifestyle images" (brand-level)

Feedback: ["Warmer", "Too cold", "More golden tones"] (all in Christmas project)
→ Rule: "Use warm, golden color temperature" (project: christmas-campaign)
"""

_pattern_detector = Agent(
    name="Pattern Detector",
    instructions=PATTERN_DETECTOR_INSTRUCTIONS,
    output_type=PatternAnalysisResult,
    model="gpt-4.1-mini",
)


async def analyze_feedback_message(
    message: str,
    context: str = "",
) -> FeedbackAnalysis:
    """Analyze a user message to detect if it's correction feedback.

    Args:
        message: The user's message.
        context: Optional context about current generation.

    Returns:
        FeedbackAnalysis with is_correction, category, and intent.
    """
    prompt = f"Analyze this user message:\n\n{message}"
    if context:
        prompt += f"\n\nContext: {context}"
    result = await Runner.run(_feedback_analyzer, prompt)
    return result.final_output


async def detect_patterns(
    feedback_instances: list[FeedbackInstance],
    min_occurrences: int = 3,
) -> PatternAnalysisResult:
    """Detect patterns in a list of feedback instances.

    Args:
        feedback_instances: List of feedback to analyze.
        min_occurrences: Minimum occurrences to consider a pattern.

    Returns:
        PatternAnalysisResult with detected patterns.
    """
    if len(feedback_instances) < min_occurrences:
        return PatternAnalysisResult(
            analysis_notes=f"Not enough feedback ({len(feedback_instances)} < {min_occurrences})"
        )
    # Build prompt with feedback data
    feedback_text = "\n".join(
        [
            f"- [{f.category or 'uncategorized'}] {f.user_message} "
            f"(project: {f.project_slug or 'none'})"
            for f in feedback_instances
        ]
    )
    prompt = f"""\
Analyze these feedback instances for patterns:

{feedback_text}

Minimum occurrences for a pattern: {min_occurrences}
"""
    result = await Runner.run(_pattern_detector, prompt)
    return result.final_output


async def record_and_analyze_feedback(
    brand_slug: str,
    user_message: str,
    original_prompt: str = "",
    project_slug: str | None = None,
    attached_products: list[str] | None = None,
    attached_style: str | None = None,
    session_id: str = "",
    auto_update_directive: bool = True,
    progress_callback: Callable[[str], None] | None = None,
) -> FeedbackInstance | None:
    """Record user feedback and optionally trigger pattern analysis.

    This is the main entry point for tracking feedback. It:
    1. Analyzes the message to see if it's a correction
    2. If yes, records it to the feedback log
    3. Checks for patterns and updates Visual Directive if needed

    Args:
        brand_slug: The brand slug.
        user_message: The user's message.
        original_prompt: The prompt that generated the rejected image.
        project_slug: Current project context.
        attached_products: Products attached during generation.
        attached_style: Style reference attached.
        session_id: Current session ID.
        auto_update_directive: Whether to auto-update directive on patterns.
        progress_callback: Optional callback for progress updates.

    Returns:
        FeedbackInstance if recorded, None if message wasn't a correction.
    """
    # Step 1: Analyze the message
    if progress_callback:
        progress_callback("Analyzing feedback...")
    analysis = await analyze_feedback_message(user_message)
    if not analysis.is_correction:
        logger.debug("Message is not a correction: %s", user_message[:50])
        return None
    # Step 2: Record to feedback log
    import uuid

    log = load_feedback_log(brand_slug)
    feedback = FeedbackInstance(
        id=str(uuid.uuid4()),
        brand_slug=brand_slug,
        project_slug=project_slug,
        user_message=user_message,
        category=analysis.category,
        original_prompt=original_prompt,
        attached_products=attached_products or [],
        attached_style=attached_style,
        session_id=session_id,
    )
    log.add_feedback(feedback)
    save_feedback_log(brand_slug, log)
    logger.info(
        "Recorded feedback for %s: [%s] %s",
        brand_slug,
        analysis.category,
        user_message[:50],
    )
    # Step 3: Check for patterns (if enough unprocessed feedback)
    if auto_update_directive:
        unprocessed = log.get_unprocessed()
        if len(unprocessed) >= 3:
            if progress_callback:
                progress_callback("Checking for patterns...")
            await _check_and_apply_patterns(brand_slug, log, progress_callback)
    return feedback


async def _check_and_apply_patterns(
    brand_slug: str,
    log: FeedbackLog,
    progress_callback: Callable[[str], None] | None = None,
) -> int:
    """Check for patterns and apply them to Visual Directive.

    Returns:
        Number of new rules added.
    """
    unprocessed = log.get_unprocessed()
    if len(unprocessed) < 3:
        return 0
    # Detect patterns
    result = await detect_patterns(unprocessed)
    if not result.patterns_found:
        return 0
    # Load or create directive
    directive = load_visual_directive(brand_slug)
    if not directive:
        directive = VisualDirective()
    rules_added = 0
    for pattern in result.patterns_found:
        # Create learned rule
        scope = RuleScope.PROJECT if pattern.scope == "project" else RuleScope.BRAND
        rule = LearnedRule(
            rule=pattern.rule_text,
            scope=scope,
            project_slug=pattern.project_slug,
            confidence=pattern.confidence,
            occurrences=len(pattern.feedback_ids),
            source_category=pattern.category,
        )
        directive.add_learned_rule(rule)
        rules_added += 1
        # Mark feedback as processed
        log.mark_processed(pattern.feedback_ids, pattern.rule_text)
        logger.info(
            "Added learned rule for %s: [%s] %s",
            brand_slug,
            pattern.category,
            pattern.rule_text,
        )
    # Save updates
    log.last_pattern_analysis = datetime.utcnow()
    save_feedback_log(brand_slug, log)
    directive.version += 1
    save_visual_directive(brand_slug, directive)
    if progress_callback and rules_added > 0:
        progress_callback(f"Learned {rules_added} new rule(s) from your feedback")
    return rules_added


async def force_pattern_analysis(
    brand_slug: str,
    progress_callback: Callable[[str], None] | None = None,
) -> int:
    """Force pattern analysis on all unprocessed feedback.

    Args:
        brand_slug: The brand slug.
        progress_callback: Optional callback.

    Returns:
        Number of rules added.
    """
    log = load_feedback_log(brand_slug)
    return await _check_and_apply_patterns(brand_slug, log, progress_callback)
