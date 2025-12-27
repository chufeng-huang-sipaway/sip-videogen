# Implementation Plan: Gemini 3.0 Pro Prompting Enhancement

## Background

### Why Are We Doing This?

Google's Gemini 3.0 Pro (internally codenamed "Nano-Banana Pro") represents a significant leap in image generation capabilities. Unlike previous models that treated prompts as keyword lists, Gemini 3.0 Pro is a **"thinking" model** that understands intent, physics, context, and can perform complex reasoning.

Our current implementation works, but it doesn't fully leverage these advanced capabilities. We're leaving performance on the table by not utilizing:
- **Iterative refinement** (the model excels at targeted edits)
- **Text rendering** (it can produce legible, styled text in images)
- **Layout control** (it can follow sketches and wireframes)
- **Dimensional translation** (2D↔3D conversion)
- **Intelligent editing** (background removal, colorization via natural language)

### The Goal

Transform our image generation agent from a "good prompt writer" into a **state-of-the-art creative director** that:

1. Produces higher-quality images with fewer iterations
2. Enables new use cases (infographics, sketch-to-final, image editing)
3. Maintains our strict product identity requirements (zero visual deviation)
4. Reduces user effort through smarter iterative refinement

### Key Insight: "Stop Using Tag Soup, Start Acting Like a Creative Director"

The Nano-Banana Pro guide emphasizes that prompts should read like you're briefing a human artist—complete sentences with context, not comma-separated keywords. Our skill already follows this principle, but we'll reinforce it and add advanced techniques.

### Architecture Decision: Keep It Simple

We will **NOT** create multiple specialized skills (infographic skill, editing skill, etc.). Instead, we enhance our single `image-prompt-engineering` skill with new sections. This keeps the system maintainable and ensures the agent always has the complete picture when working on image tasks.

---

## ⚠️ Critical Implementation Concerns (Review Feedback)

The following concerns were raised during review and **MUST** be addressed in the relevant tasks:

### Concern 1: Iterative Refinement Requires Previous OUTPUT as Reference
**Problem**: Prompt-only edits still re-roll composition. If user says "keep this but change X", you need the previous OUTPUT image as `reference_image`, not just edited prompt text.

**Solution**: Task 3 must specify that iterative refinement requires:
1. Retrieve previous generation's output path
2. Use that output as `reference_image` for the next generation
3. Apply prompt modifications on top

### Concern 2: validate_identity Guidance Is Too Broad
**Problem**: Original plan said "don't use validate_identity for edits"—but this is wrong for product photo edits like "remove background from this product shot".

**Correct Logic**:
| Scenario | validate_identity |
|----------|-------------------|
| Edit product photo (remove bg, relight, cleanup) | `True` — product must stay identical |
| Style/layout reference (sketch, mood board) | `False` — reference is not the product |
| Colorize old photo / restore damage | `False` — not a product identity task |
| Change the product itself | `False` — intentionally changing it |

### Concern 3: Path Ergonomics for Follow-up Edits
**Problem**: `generate_image` returns absolute path (`/Users/.../output/image.png`), but `reference_image` expects brand-relative path (`assets/generated/...`).

**Solution**: Document path conversion in Task 3 and Task 4. Agent must convert absolute paths to relative before passing to next `generate_image` call.

### Concern 4: Trigger Expansion Risk
**Problem**: Substring matching on generic words like "edit" or "enhance" will fire on non-image tasks (e.g., "edit the code", "enhance the API").

**Solution**: Task 7 must use specific phrases instead:
- ❌ `edit` → ✅ `edit image`, `edit photo`
- ❌ `enhance` → ✅ `enhance image`, `photo enhancement`
- ❌ `remove` → ✅ `remove background`
- Alternative: Gate on attachment presence (requires code change)

### Concern 5: Sketch/Layout Detection Ambiguity
**Problem**: "Looks like a sketch" is subjective and error-prone.

**Solution**: Use deterministic rules in Task 5:
1. If `product_slug` present → **Identity flow** (product reference)
2. If user explicitly says "sketch", "wireframe", "layout" → **Layout flow**
3. Otherwise → **Ask for clarification** via `propose_choices`

---

## Implementation Tasks

### ☐ Task 1: Update Image Prompt Engineering Skill with Texture & Material Guidance

**Background**: Nano-Banana Pro excels at rendering fine details—surface textures, material properties, even imperfections like fingerprint smudges or dust particles. Our current 5-point formula covers Subject, Setting, Style, Lighting, and Composition, but doesn't emphasize texture depth.

**Goal**: Ensure the agent consistently includes material and texture details in prompts, resulting in more photorealistic and accurate product representations.

**File**: `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md`

**Changes**:
- Add new section "### Texture & Material Details" under Advanced Prompting
- Include guidance on surface finishes: matte, glossy, frosted, brushed, textured
- Include material properties: soft velvet, cold steel, warm wood grain
- Include imperfections for realism: condensation, dust, micro-scratches
- Add 2-3 example prompts demonstrating texture-rich descriptions
- Update "Critical Do's" to include texture emphasis

---

### ☐ Task 2: Add Text Rendering Guidance to Skill

**Background**: Legible text in generated images has historically been a weak point for AI models. Nano-Banana Pro specifically addresses this—it can render readable, styled text when properly instructed. The key technique is **quoting exact text** and specifying typography.

**Goal**: Enable the agent to produce images with clear, correctly rendered text for use cases like product labels, infographics, and advertisements.

**File**: `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md`

**Changes**:
- Add new section "### Text Rendering" under Advanced Prompting
- Instruct: enclose exact text in **double quotes**
- Instruct: specify typography (font style, relative size, color)
- Instruct: describe placement precisely
- Add example: `"BLOOM ORGANIC" in elegant serif typography, gold foil embossed...`
- Reference existing text guidance in skill and strengthen it

---

### ☐ Task 3: Add Iterative Refinement Workflow ("Edit, Don't Re-roll")

**Background**: When an image is 80% correct, users typically ask for small changes ("warmer lighting", "different angle"). The naive approach generates a completely new image, often losing what was already good. Nano-Banana Pro is designed for **iterative refinement**—you tell it what to change, and it adjusts while preserving the rest.

**Goal**: Reduce iteration cycles by teaching the agent to use previous output as reference while applying targeted prompt modifications.

**⚠️ Addresses**: Concern 1 (output as reference), Concern 3 (path ergonomics)

**⚠️ Scope Limitation (Phase 1)**: Iterative refinement is **only supported for single-reference flows**:
- ✅ Single product image refinement (no `product_slug`)
- ✅ Non-product image refinement (lifestyle shots, backgrounds)
- ❌ Multi-product flows (`product_slugs` ignores `reference_image` in current tool)
- ❌ Combined output + product_slug refs (not supported in current tool)

For multi-product refinement, agent should regenerate fresh with same `product_slugs` and adjusted prompt. See **Phase 2 (Future)** below for planned enhancement.

**Files**:
- `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md`
- `src/sip_videogen/advisor/prompts/advisor.md`

**Changes**:
- Add new section "### Iterative Refinement" to SKILL.md
- **Critical**: Document that refinement requires BOTH:
  1. Previous OUTPUT image as `reference_image` (not just prompt edits)
  2. Modified prompt with targeted change
- **Document scope limitation**: single-reference flows only (Phase 1)
- Document path conversion: absolute path → brand-relative path before next call
- Add guidance to advisor.md for detecting refinement requests
- Add decision tree:
  ```
  User requests change on recent generation:

  1. Was it a multi-product generation?
     YES → Cannot use output as reference. Regenerate fresh with
           same product_slugs + adjusted prompt. Warn user that
           composition may vary.
     NO  → Continue to step 2

  2. What kind of change?
     "change X" (lighting, angle, color) → use output as reference + edit prompt
     "try something different" → fresh generation, no reference
  ```
- Add examples showing correct `reference_image` usage

---

### ☐ Task 4: Add Image Editing via Natural Language

**Background**: Traditional image editing requires masks, layers, and pixel-level operations. Nano-Banana Pro can perform edits through **natural language instructions alone**—"remove the background", "colorize this black-and-white photo", "restore this damaged image". The model intelligently infers what needs to change.

**Goal**: Enable the agent to handle image modification requests without new tools, using the existing `generate_image` with source image as reference.

**⚠️ Addresses**: Concern 2 (validate_identity nuance), Concern 3 (path ergonomics)

**Files**:
- `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md`
- `src/sip_videogen/advisor/prompts/advisor.md`

**Changes**:
- Add new section "### Image Editing via Language" to SKILL.md
- Instruct: use source image as `reference_image`
- Instruct: describe desired outcome, NOT pixel-level operations
- Document path conversion for follow-up edits
- **Critical**: Add nuanced `validate_identity` decision table:
  | Edit Type | validate_identity | Reason |
  |-----------|-------------------|--------|
  | Remove background from product | `True` | Product must stay identical |
  | Relight/cleanup product photo | `True` | Product must stay identical |
  | Colorize old photo | `False` | Not a product identity task |
  | Style transfer | `False` | Intentionally changing appearance |
  | Follow sketch/layout | `False` | Reference is layout, not product |
- **Add to advisor.md** - Edit mode detection rules:
  ```
  ## Edit Mode Detection

  Trigger phrases (use ONLY these specific phrases):
  - "remove background", "remove the background"
  - "edit image", "edit photo", "edit this image"
  - "enhance image", "enhance photo", "photo enhancement"
  - "restore photo", "restore image"
  - "colorize", "colorize this"
  - "clean up", "cleanup"
  - "relight", "change lighting on"

  When detected:
  1. Use attached/referenced image as reference_image
  2. Apply validate_identity per decision table above
  3. Describe desired outcome in prompt (not pixel operations)
  4. Do NOT treat as new generation—preserve source image
  ```
- Add 3-4 example prompts for common edit scenarios with correct flag usage

---

### ☐ Task 5: Add Sketch/Layout Control Guidance

**Background**: Designers often start with rough sketches or wireframes. Nano-Banana Pro can use these as **layout references**—it follows the spatial arrangement while filling in polished details. This is different from our template system (which uses JSON constraints); this approach uses visual input directly.

**Goal**: Enable users to upload a sketch and get a polished final image that follows the exact layout.

**⚠️ Addresses**: Concern 5 (deterministic detection, not subjective)

**Files**:
- `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md`
- `src/sip_videogen/advisor/prompts/advisor.md`

**Changes**:
- Add new section "### Layout Control via Sketch/Wireframe" to SKILL.md
- Instruct: use sketch as `reference_image`
- Instruct: prompt pattern "Following this [sketch/wireframe] exactly, create..."
- **Critical**: Add deterministic detection rules to advisor.md (NO subjective "looks like sketch"):
  ```
  Decision Tree for Attached Images:
  1. If product_slug is present → IDENTITY FLOW (product reference)
  2. If user says "sketch", "wireframe", "layout", "mockup", "blueprint" → LAYOUT FLOW
  3. If ambiguous → ASK via propose_choices:
     "Is this image a product reference or a layout guide?"
  ```
- Specify that `validate_identity=False` for layout references
- Add examples for ad layouts, UI mockups, floor plans

---

### ☐ Task 6: Add Dimensional Translation Guidance (2D ↔ 3D)

**Background**: Nano-Banana Pro can convert between dimensions—turning a flat blueprint into a 3D render, or a 3D scene into a stylized 2D illustration. This is valuable for product visualization (e.g., turning a label design into a bottle mockup).

**Goal**: Enable the agent to handle dimensional conversion requests with proper prompting.

**File**: `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md`

**Changes**:
- Add new section "### Dimensional Translation (2D ↔ 3D)" to SKILL.md
- Add pattern for 2D→3D: "Based on this [drawing/blueprint], generate a photorealistic 3D render..."
- Add pattern for 3D→2D: "Convert this 3D scene to a flat illustration maintaining composition..."
- Add guidance on merging product attributes with reference (colors, labels from product data)
- Add 2 example prompts

---

### ☐ Task 7: Expand Trigger Keywords in Skill Frontmatter

**Background**: Our skill system uses keyword triggers to determine when to load a skill. Currently, `image-prompt-engineering` triggers on words like "image", "photo", "render". But with new capabilities, we need to trigger on "infographic", "diagram", "sketch", "mockup", "colorize", etc.

**Goal**: Ensure the skill activates for all relevant use cases, including new ones.

**⚠️ Addresses**: Concern 4 (avoid generic triggers that false-positive)

**File**: `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md` (frontmatter/triggers section)

**Changes**:
- Add new keywords to trigger list using **specific phrases** (not generic words):
  - Infographics: `infographic`, `diagram`, `chart`
  - Layout: `sketch layout`, `wireframe`, `layout mockup`, `blueprint`, `schematic`
  - Editing (SPECIFIC, not generic):
    - ✅ `remove background` (not just "remove")
    - ✅ `colorize image`, `colorize photo` (not just "colorize")
    - ✅ `enhance image`, `photo enhancement` (not just "enhance")
    - ✅ `edit image`, `edit photo` (not just "edit")
    - ✅ `restore photo`, `restore image`
  - Dimensional: `3D render`, `3D mockup`, `illustration`
- **Do NOT add**: `edit`, `enhance`, `remove`, `change` (too generic, will fire on code/API tasks)
- Verify no conflicts with other skills' triggers
- Consider: attachment-based gating as future code enhancement

---

### ☐ Task 8: Update Critical Do's and Don'ts Section

**Background**: The "Critical Do's" section is a quick-reference checklist for the agent. With new capabilities, we need to add new items and reinforce existing ones.

**Goal**: Provide the agent with an updated, comprehensive checklist that covers all prompting best practices.

**File**: `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md`

**Changes**:
- Update "Critical Do's" to include:
  - ✅ Material textures and surface details
  - ✅ Quote exact text for in-image rendering
  - ✅ Use reference_image for edits, not new generations
  - ✅ Iterative refinement over complete re-rolls
  - ✅ "Following this sketch exactly" for layout references
- Review "Critical Don'ts" for any needed updates
- Ensure consistency with new sections

---

### ☐ Task 9: Add Example Prompt Templates to Skill

**Background**: Templates help the agent consistently produce high-quality prompts. Rather than figuring out structure each time, it can follow proven patterns.

**Goal**: Provide reusable prompt templates for common scenarios.

**File**: `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md`

**Changes**:
- Add new section "### Prompt Templates" or append to existing examples section
- Include templates for:
  - Product Hero Shot (existing, enhance with texture)
  - Infographic Layout
  - Image Edit
  - Sketch to Final
  - 2D to 3D Conversion
- Each template shows structure with placeholders
- Add 1-2 filled-in examples per template

---

### ☐ Task 10: Write Test Cases and Validation Checklist

**Background**: These changes affect how the agent prompts the image model. We need to verify that all scenarios work correctly and that existing functionality isn't broken.

**Goal**: Create a test matrix that developers and QA can use to validate the implementation.

**File**: `docs/TEST-gemini-prompting-v2.md` (new file)

**Changes**:
- Document test cases for each new capability:
  - Basic product shot (regression test)
  - Infographic with text rendering
  - Image editing (background removal)
  - Sketch layout following
  - Multi-product group shot
  - 2D to 3D conversion
  - Iterative refinement
- Define acceptance criteria for each
- Include example inputs and expected prompt patterns
- Document how to verify output quality

---

## Summary Checklist

### Phase 1: Prompt-Only Changes (No Code)

| # | Task | File(s) | Status |
|---|------|---------|--------|
| 1 | Texture & Material Guidance | SKILL.md | ✅ Complete |
| 2 | Text Rendering Guidance | SKILL.md | ✅ Complete |
| 3 | Iterative Refinement Workflow ⚠️ | SKILL.md, advisor.md | ✅ Complete |
| 4 | Image Editing via Language ⚠️ | SKILL.md, advisor.md | ✅ Complete |
| 5 | Sketch/Layout Control ⚠️ | SKILL.md, advisor.md | ☐ Not Started |
| 6 | Dimensional Translation | SKILL.md | ☐ Not Started |
| 7 | Expand Trigger Keywords ⚠️ | SKILL.md | ☐ Not Started |
| 8 | Update Critical Do's/Don'ts | SKILL.md | ☐ Not Started |
| 9 | Add Prompt Templates | SKILL.md | ☐ Not Started |
| 10 | Write Test Cases | TEST-gemini-prompting-v2.md | ☐ Not Started |

⚠️ = Has critical concerns addressed in task description

### Phase 2: Code Enhancements (Future)

| # | Task | File(s) | Status |
|---|------|---------|--------|
| 11 | Combined Output + Product Refs | tools.py | ☐ Not Started |
| 12 | Attachment-Based Skill Gating | registry.py | ☐ Not Started |

---

## Dependencies & Notes

**No Code Changes Required for Phase 1**: All tasks in this plan involve updating markdown files (skills and prompts). The existing `generate_image` tool already supports all the parameters we need (`reference_image`, `validate_identity`, etc.).

**Order of Implementation**: Tasks 1-6 can be done in any order. Task 7 (triggers) and Task 8 (Critical Do's) should be done after the main sections are added. Task 9 (templates) should come last. Task 10 can be done in parallel.

**Files to Modify**:
- `src/sip_videogen/advisor/skills/image_prompt_engineering/SKILL.md` (primary)
- `src/sip_videogen/advisor/prompts/advisor.md` (secondary)
- `docs/TEST-gemini-prompting-v2.md` (new)

**Reference Document**: See `docs/SPEC-gemini-prompting-v2.md` for detailed technical specifications and example content.

---

## Phase 2 (Future): Code Enhancements

These require changes to `tools.py` and are out of scope for Phase 1 (prompt-only changes):

### ☐ Task 11: Enable Combined Output + Product Refs in generate_image

**Background**: Currently `generate_image` cannot combine:
- Previous output as `reference_image` (for composition continuity)
- `product_slug(s)` for identity validation

Multi-product flows ignore `reference_image` entirely.

**Goal**: Enable iterative refinement for product and multi-product flows.

**File**: `src/sip_videogen/advisor/tools.py`

**Changes**:
- Modify `_impl_generate_image` to accept both `reference_image` (composition) and `product_slug(s)` (identity)
- Update API call structure to include output image + product refs in same request
- For multi-product: include output as "composition reference" alongside product images
- Update validation logic to check identity against product refs (not output ref)

**Acceptance Criteria**:
- `generate_image(reference_image="prev_output.png", product_slug="bottle")` works
- `generate_image(reference_image="prev_output.png", product_slugs=["a","b"])` works
- Identity validation still enforces product accuracy

### ☐ Task 12: Attachment-Based Skill Gating

**Background**: Substring trigger matching on "edit"/"enhance" causes false positives on non-image tasks. A more robust solution is to gate skill activation on attachment presence.

**Goal**: Only trigger image-prompt-engineering skill when image attachment is present AND edit-related keywords detected.

**File**: `src/sip_videogen/advisor/skills/registry.py` (or similar)

**Changes**:
- Add `requires_attachment: image` option to skill frontmatter
- Modify `find_relevant_skills` to check for image attachments
- For edit triggers: require BOTH keyword match AND image attachment
- For non-edit triggers (infographic, diagram): keyword alone is sufficient

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-26 | Initial draft |
| 1.1 | 2025-12-26 | Incorporated review feedback: added Critical Concerns section, updated Tasks 3/4/5/7 with fixes for iterative refinement, validate_identity nuance, path ergonomics, trigger specificity, and deterministic sketch detection |
| 1.2 | 2025-12-26 | Added explicit advisor.md edit mode detection rules to Task 4; scoped Task 3 to single-reference flows with multi-product decision tree; added Phase 2 (Future) with Tasks 11-12 for code enhancements (combined refs, attachment gating) |

---

*Document Version: 1.2*
*Created: 2025-12-26*
*Related: SPEC-gemini-prompting-v2.md, Plan for State-of-the-Art Gemini 3 Prompting.md*
