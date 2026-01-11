# Task Plan: Two-Phase Prompt Generation with Visual Directive

## Goal
Restructure image prompt generation into two distinct phases (Concept → Visual) with an evolving Visual Directive that translates brand identity into visual rules, enabling clearer context separation and learning from user feedback.

## Background (From Discussion)

### The Problem
Currently, the agent must juggle all contexts simultaneously:
- Brand identity (what not to violate)
- Product specs (pixel-perfect accuracy required)
- Project brief (campaign theme to express)
- Visual style (color grading, lighting)

This causes:
1. Important details get forgotten (e.g., target customer age)
2. Project instructions feel diluted ("10% tokens = 10% importance")
3. Hard to debug which context caused issues

### The Solution
Separate concerns into phases:

```
Phase 1 (Concept): Brand + Product + Project → Scene description
Phase 2 (Visual): Scene + Style + Visual Directive → Visual specifications
Phase 3 (Format): Agent applies skill guidelines → Final Gemini prompt
```

Plus: A new **Visual Directive** artifact that translates brand identity into visual-specific rules and evolves based on user feedback patterns.

## Phases

- [x] Phase 1: Design Visual Directive schema and storage
- [x] Phase 2: Implement Visual Directive generation (from brand identity)
- [x] Phase 3: Implement feedback pattern tracking
- [x] Phase 4: Implement Visual Directive evolution (learning mechanism)
- [x] Phase 5: Implement two-phase prompt pipeline (Concept → Visual)
- [x] Phase 6: Integrate with existing image generation flow
- [ ] Phase 7: Update skills and documentation
- [ ] Phase 8: Testing and validation

## Key Questions (Resolved)

1. **Visual Directive storage**: ✅ Separate file `visual_directive.json` alongside brand identity
2. **Feedback tracking**: ✅ JSON file `feedback_log.json` per brand
3. **Pattern threshold**: 3+ similar corrections (AI interprets semantic similarity)
4. **Scope detection**: AI decides brand-level vs project-level based on context
5. **Phase handoff**: Phased instructions within one agent turn (not separate LLM calls)
6. **Integration point**: Update `image-prompt-engineering` skill with two-phase thinking process

## Decisions Made
- [Trust agent for Phase 3]: Don't create separate formatter functions; strengthen skill instructions instead
- [Silent updates]: Visual Directive evolves without notifying user (for now)
- [AI interprets patterns]: Don't use exact phrase matching; let AI determine semantic similarity
- [Memory is not append-only]: Corrections can update/remove outdated rules
- [Separate file for Visual Directive]: Keeps it focused, loaded only for image generation, not diluted by brand identity
- [JSON for feedback tracking]: Simple, portable, per-brand storage
- [Phased instructions, not separate calls]: Maintains conversation continuity, memory, natural flow

## Architecture Sketch

### Visual Directive Schema (Draft)
```python
class VisualDirective:
    brand_slug: str
    version: int
    created_at: datetime
    updated_at: datetime

    # Core visual rules (from brand identity)
    target_representation: str  # "Women 35-45, confident, established"
    color_guidelines: list[str]  # "Warm tones", "Avoid clinical white"
    mood_guidelines: list[str]  # "Inviting", "Spa-like calm"
    avoid_list: list[str]  # "Overly young models", "Harsh lighting"

    # Learned preferences (from feedback patterns)
    learned_rules: list[LearnedRule]

class LearnedRule:
    rule: str
    scope: Literal["brand", "project"]
    project_slug: str | None  # If project-scoped
    confidence: float  # 0.0-1.0, increases with more confirmations
    created_from: list[FeedbackInstance]  # The corrections that led to this rule
```

### Two-Phase Pipeline (Draft)
```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: CONCEPT                                            │
│                                                             │
│ Inputs:                                                     │
│ - User request                                              │
│ - Brand identity (guardrails only)                          │
│ - Product specs + reference images                          │
│ - Project brief                                             │
│ - Visual Directive (do's and don'ts)                        │
│                                                             │
│ Output: Scene description (structured)                      │
│ - Subject: who/what is in the image                         │
│ - Setting: environment/location                             │
│ - Action: what's happening                                  │
│ - Product placement: where/how products appear              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: VISUAL                                             │
│                                                             │
│ Inputs:                                                     │
│ - Phase 1 scene description (locked concept)                │
│ - Visual style reference (color grading DNA)                │
│ - Style reference images                                    │
│ - Product reference images                                  │
│                                                             │
│ Output: Visual specifications                               │
│ - Lighting: direction, quality, color temperature           │
│ - Color grading: shadows, highlights, saturation            │
│ - Mood/atmosphere: emotional quality                        │
│ - Composition: framing, depth of field                      │
│                                                             │
│ Note: Can override Phase 1 lighting/color if conflicts      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: FORMAT (Existing Skill System)                     │
│                                                             │
│ Agent applies image-prompt-engineering skill:               │
│ - 5-Point Formula                                           │
│ - Narrative description (not keywords)                      │
│ - Texture/material details                                  │
│ - Product specs injection                                   │
│                                                             │
│ Output: Final Gemini-optimized prompt                       │
└─────────────────────────────────────────────────────────────┘
```

### Feedback Tracking (Draft)
```python
class FeedbackInstance:
    timestamp: datetime
    session_id: str
    brand_slug: str
    project_slug: str | None

    # The correction
    user_message: str  # "Make her older", "Too cold, warmer please"
    category: str | None  # AI-determined: "subject_age", "color_temperature"

    # Context when correction was made
    original_prompt: str
    attached_products: list[str]
    attached_style: str | None

class FeedbackTracker:
    def record(self, feedback: FeedbackInstance) -> None: ...
    def find_patterns(self, brand_slug: str, min_occurrences: int = 3) -> list[Pattern]: ...
    def should_update_directive(self, pattern: Pattern) -> bool: ...
```

## Files to Create/Modify

### New Files
- `src/sip_studio/advisor/visual_directive.py` - VisualDirective model and service
- `src/sip_studio/advisor/feedback_tracker.py` - Feedback tracking and pattern detection
- `src/sip_studio/advisor/prompt_phases.py` - Two-phase pipeline implementation
- `src/sip_studio/brands/visual_directive_generator.py` - Generate directive from brand identity

### Modified Files
- `src/sip_studio/advisor/tools/image_tools.py` - Hook in two-phase pipeline
- `src/sip_studio/advisor/context.py` - Add VisualDirectiveContextBuilder
- `src/sip_studio/brands/storage.py` - Store/load Visual Directive
- `src/sip_studio/advisor/skills/image_prompt_engineering/SKILL.md` - Update for phase awareness

## Errors Encountered
(None yet)

## Status
**Currently in Phase 7** - Documentation and testing remaining.

## Completed Work

### Phase 1-2: Visual Directive Foundation

**New Files Created:**
- `src/sip_studio/brands/models/visual_directive.py` - Data models
  - `VisualDirective` - Main model with nested sections
  - `TargetRepresentation` - Who appears in images
  - `ColorGuidelines` - Color direction
  - `MoodGuidelines` - Emotional atmosphere
  - `PhotographyStyle` - Photography style
  - `LearnedRule` - Feedback-learned preferences
  - `FeedbackInstance` - Single correction
  - `FeedbackLog` - Collection of feedback

- `src/sip_studio/brands/storage/visual_directive_storage.py` - CRUD operations
  - `load_visual_directive()` / `save_visual_directive()`
  - `load_feedback_log()` / `save_feedback_log()`
  - `add_feedback()` - Convenience function

- `src/sip_studio/brands/visual_directive_generator.py` - LLM-based generation
  - `generate_visual_directive()` - Generate from brand identity
  - `regenerate_visual_directive()` - Regenerate with preserved learned rules

**Exports Updated:**
- `src/sip_studio/brands/models/__init__.py`
- `src/sip_studio/brands/storage/__init__.py`

### Phase 3-4: Feedback Pattern Tracking & Learning

**New Files Created:**
- `src/sip_studio/brands/feedback_analyzer.py` - Pattern detection and learning
  - `analyze_feedback_message()` - Detect if message is a correction
  - `detect_patterns()` - Find patterns in feedback history
  - `record_and_analyze_feedback()` - Main entry point for tracking
  - `force_pattern_analysis()` - Manual pattern analysis trigger

**How It Works:**
1. User gives correction ("Make her older")
2. `analyze_feedback_message()` categorizes it (subject_age)
3. Records to `feedback_log.json`
4. If 3+ unprocessed feedback, runs pattern detection
5. Detected patterns become LearnedRules in VisualDirective
6. Next image generation uses learned rules

## Storage Structure
```
~/.sip-studio/brands/{slug}/
├── identity.json           # Source: brand summary
├── identity_full.json      # Source: full brand identity
├── visual_directive.json   # Derived: visual rules for image generation (NEW)
├── feedback_log.json       # Learning: tracked corrections (NEW)
└── assets/
```

### Phase 5-6: Two-Phase Pipeline & Integration

**Modified Files:**
- `src/sip_studio/advisor/skills/image_prompt_engineering/SKILL.md`
  - Added "Two-Phase Thinking Process" section
  - Phase 1: CONCEPT (What's in the image) - Subject, Setting, Action, Product Placement
  - Phase 2: VISUAL (How it looks) - Lighting, Color Grading, Mood, Composition
  - Key rule: Visual styling can override Phase 1 for visual aspects
  - Included example two-phase process walkthrough
  - Added guidance for using Visual Directive in both phases

- `src/sip_studio/brands/context.py`
  - Added `VisualDirectiveContextBuilder` class
  - Formats Visual Directive as agent context (target representation, color guidelines, mood, photography style, learned rules)
  - Added `build_visual_directive_context()` convenience function
  - Integrated into `HierarchicalContextBuilder.build_turn_context()`
  - Visual Directive context injected after Project context, before Products

- `src/sip_studio/brands/__init__.py`
  - Exported `VisualDirectiveContextBuilder` and `build_visual_directive_context`

**Integration Points:**
- Visual Directive is now automatically included in per-turn context
- `HierarchicalContextBuilder` has new `include_visual_directive=True` parameter
- Learned rules are filtered by project scope when `project_slug` is provided

## Future Considerations
1. How to surface learned rules to user in UI (future feature)
2. Visual Directive versioning and rollback
3. Export/import of Visual Directives between brands
