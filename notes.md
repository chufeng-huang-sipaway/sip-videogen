# Notes: Two-Phase Prompt Generation Design

## Source: User Discussion (This Session)

### Context Hierarchy (User's Mental Model)

The user described four context layers with different purposes:

| Layer | Role | Constraint Type | Priority |
|-------|------|-----------------|----------|
| **Brand Identity** | Guardrails - "do not violate" | Negative constraint | Top (cannot violate) |
| **Product** | Accuracy - "must match exactly" | Hard positive constraint | Top (cannot violate) |
| **Project** | Creative brief - "what to express" | Soft positive direction | Middle (express strongly) |
| **Visual Style** | Consistency - "how it should look" | Soft positive direction | Middle (express strongly) |

Key insight: **Two tiers exist**
1. Hard constraints (Brand + Product) → violation = failure
2. Creative direction (Project + Style) → guidance for expression

### Problem Statements

**Problem 1: Brand Identity is too raw**
- Dumping whole brand identity and hoping agent figures it out is unstable
- Example: Skincare brand targeting 40-year-old women, but model generates 20-year-old girls
- Information IS in brand identity but buried among 50 other facts
- A human brand manager would NEVER forget target customer age

**Problem 2: Project gets diluted**
- "10% of tokens = 10% importance" - project competes with color grading specs
- Example: "January cold sunny vibe" campaign → only surface changes (sweater, gray lighting)
- Model doesn't fundamentally shift the scene based on project

### Visual Directive Concept

A new artifact that translates brand identity into visual-specific rules:

**Example for skincare brand:**
- "Primary subject in lifestyle shots: women 35-45, confident, established"
- "Never: overly young models that don't match target customer"
- "Color temperature: warm, inviting, spa-like"
- "Avoid: clinical/medical aesthetics, harsh lighting"

**When created:**
- Initially when brand is created
- Updated when brand identity is re-analyzed
- Evolves based on user feedback patterns

### Learning Mechanism Principles

User defined these principles for memory/learning:

1. **Not append-only** - Memory is corrected, updated, and pruned
2. **AI interprets patterns** - Don't match exact phrases; understand semantic similarity
3. **AI decides scope** - Brand-level vs project-level is contextual
4. **Best judgment is sufficient** - Make a call even with incomplete info; can correct later
5. **Goal: first-try accuracy** - Reduce trial-and-error, understand user immediately
6. **Memory stays critical** - Remove outdated info; don't accumulate noise

**Pattern threshold:** 3+ similar corrections = update rule
- One-off corrections = noise (ignore)
- Repeated corrections = pattern (learn)

**Scope detection:**
- If "warmer" mentioned only in Christmas project → project-level
- If "warmer" mentioned across all projects → brand-level
- AI makes best judgment given context

### Two-Phase Approach

User proposed separating "what is in the image" from "how the image looks":

**Phase 1: Concept**
- Focus: What's happening? Who's there? What environment?
- Inputs: Brand, Product, Project, Visual Directive
- Output: Scene description / script

**Phase 2: Visual**
- Focus: How does it look? Color, light, mood?
- Inputs: Phase 1 output, Visual Style, Style reference
- Output: Visual specifications

**Key rule:** Phase 2 can override Phase 1 for lighting/color if style conflicts.
Example: If Phase 1 says "bright bathroom" but style is moody/dark → adjust to match style.

### Phase 3: Trust the Agent

User decided against separate formatter functions:

**Reasoning:**
1. Agent sees everything - concept, visual specs, product constraints, formatting guidelines
2. Separate formatter might drop important details (product characteristics)
3. Creating formatter per skill breaks elegant skill architecture
4. If agent isn't applying guidelines well, strengthen the instructions instead

**Skill system philosophy:**
```
Skill = Knowledge that agent lazy-loads when relevant
      ≠ A function that transforms output
```

## Source: Codebase Exploration

### Current Prompt Engineering Technique

Located in `skills/image_prompt_engineering/SKILL.md` (617 lines):

**5-Point Formula:**
1. Subject (WHAT) - Hyper-specific with materials
2. Setting (WHERE) - Environment
3. Style (HOW IT LOOKS) - Medium specification
4. Lighting/Mood (ATMOSPHERE) - Emotional quality
5. Composition (CAMERA) - Framing/perspective

**Key techniques:**
- Narrative descriptions over keywords
- Texture/material details (surface finishes, imperfections)
- Text rendering with exact quotes and typography specs
- Multi-image reference handling with explicit scoping

### Current Context Building

Located in `context.py`:

- `BrandContextBuilder` - Brand identity context
- `ProductContextBuilder` - Product specs + images
- `ProjectContextBuilder` - Project brief + instructions
- `StyleReferenceContextBuilder` - V1/V2/V3 style constraints
- `HierarchicalContextBuilder` - Merges all contexts per-turn

### Skills System

- Skills are markdown files with YAML frontmatter
- Loaded per-turn when triggers match user message
- Max 2 skills per request
- Pure prompt injection - agent reads and follows

### Product Specs Injection

Located in `product_specs.py`:
- Deterministic block appended to prompt
- `[PRESERVE EXACTLY]` markers for materials/colors
- Cannot be overridden by agent

## Synthesized Findings

### Architecture Pattern Emerging

```
Brand Created → Generate Visual Directive (v1)
                         ↓
User generates images ← Visual Directive informs Phase 1
                         ↓
User gives feedback → Track corrections
                         ↓
3+ similar patterns? → Update Visual Directive (v2, v3...)
                         ↓
Visual Directive evolves to match user's mental model
```

### Key Design Decisions

1. **Visual Directive is separate from brand identity** - It's a derived artifact, not source data
2. **Two-phase is within agent** - Not separate LLM calls, but structured prompting
3. **Phase 3 uses existing skill system** - No new code, just skill instructions
4. **Learning is silent** - No user notification (for now)
5. **AI has full autonomy on scope** - Brand vs project level

### Integration Points

1. **Brand creation/update** → Trigger Visual Directive generation
2. **Image generation** → Load Visual Directive into Phase 1 context
3. **User correction** → Record feedback instance
4. **Post-session analysis** → Check for patterns, update directive
5. **Context building** → Add VisualDirectiveContextBuilder
