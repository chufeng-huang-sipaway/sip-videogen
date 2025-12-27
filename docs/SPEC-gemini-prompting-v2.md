# Specification: Gemini 3.0 Pro Prompting Enhancement (v2)

## Executive Summary
Upgrade our image generation prompting system to leverage **Nano-Banana Pro** (Gemini 3.0 Pro) advanced techniques, improving image quality, text rendering, layout control, and iterative refinement while maintaining strict product identity accuracy.

---

## 1. Background

### Current State
- **Image Prompt Engineering Skill** (`SKILL.md`) provides 5-point formula: Subject, Setting, Style, Lighting/Mood, Composition
- **`generate_image` tool** integrates with Gemini 3.0 Pro API
- **Identity validation** ensures product accuracy via `validate_identity=True`
- **Multi-product support** via `product_slugs` parameter
- **Template/Brand context** via `template_slug` and `load_brand()`

### Gap Analysis
| Current Capability | Missing Enhancement |
|---|---|
| Natural language prompts | Iterative refinement workflow |
| 5-point formula | Texture/material emphasis |
| Text description | Proper text quoting for rendering |
| Reference images | Sketch/wireframe layout control |
| Product validation | Image editing via language |
| Single-image output | 2D↔3D dimensional translation |

---

## 2. Goals

### Primary Goals
1. **Improve prompt quality** by integrating Nano-Banana Pro techniques
2. **Enable new use cases**: infographics, text-heavy images, sketch-to-final, 2D↔3D conversion
3. **Reduce iteration cycles** via "Edit, don't re-roll" approach
4. **Maintain strict product identity** (zero tolerance for visual deviation)

### Non-Goals
- New image generation tools (use existing `generate_image`)
- Separate skills for each scenario (keep unified skill)
- Training custom models
- Real-time web search integration

---

## 3. Technical Design

### 3.1 Enhanced Skill: `image-prompt-engineering/SKILL.md`

#### A. New Sections to Add

```markdown
## Advanced Prompting Techniques (Nano-Banana Pro)

### Texture & Material Details
When describing subjects, include:
- Surface finish: matte, glossy, frosted, brushed, textured
- Material properties: soft velvet, cold steel, warm wood grain
- Imperfections (for realism): fingerprint smudges, dust particles, micro-scratches

Example: "A frosted glass bottle with visible condensation droplets,
brushed copper cap showing subtle machining marks..."

### Text Rendering
For legible text in images:
1. Enclose exact text in **double quotes**
2. Specify typography: font style, size relative to scene, color
3. Describe placement precisely

Example: "A product label reading **"BLOOM ORGANIC"** in elegant
serif typography, gold foil embossed on matte black packaging..."

### Iterative Refinement ("Edit, Don't Re-roll")
When user requests modifications:
1. Retrieve previous prompt from generation metadata
2. Apply ONLY the requested change
3. Keep all other elements identical
4. Maintain same reference_image if used

Pattern: "Keep everything from previous generation, but [specific change]"

### Image Editing via Language
For modifying existing images (remove, replace, enhance):
- Use source image as `reference_image`
- Describe desired outcome, NOT pixel-level operations
- Trust model to handle low-level details

Examples:
- "Remove the cluttered background, place product on pure white"
- "Colorize this black-and-white photo with realistic colors"
- "Restore this damaged photo to HD quality"

### Layout Control via Sketch/Wireframe
When user provides a sketch or wireframe:
- Use sketch as `reference_image`
- Prompt: "Following this [sketch/wireframe/layout] exactly, create..."
- Describe what to fill in (colors, textures, content)

### Dimensional Translation (2D ↔ 3D)
For converting between dimensions:
- 2D to 3D: "Based on this [line drawing/blueprint/schematic],
  generate a photorealistic 3D render..."
- 3D to 2D: "Convert this 3D scene to a flat illustration
  maintaining composition..."
```

#### B. Updated "Critical Do's" Section

```markdown
## Critical Do's (Updated)
1. ✅ Full sentences, not tag soup
2. ✅ 5-point formula (Subject, Setting, Style, Lighting, Composition)
3. ✅ Material textures and surface details
4. ✅ Quote exact text for in-image rendering
5. ✅ Provide context (purpose, audience, platform)
6. ✅ Use reference_image for edits, not new generations
7. ✅ Iterative refinement over complete re-rolls
```

#### C. Expanded Trigger Keywords (Frontmatter)

```yaml
triggers:
  keywords:
    # Existing
    - image
    - photo
    - render
    - picture
    - visual
    - shot
    - scene
    # New additions
    - infographic
    - diagram
    - chart
    - sketch
    - wireframe
    - layout
    - mockup
    - prototype
    - blueprint
    - schematic
    - illustration
    - 3D
    - render
    - colorize
    - restore
    - edit
    - remove background
    - enhance
```

---

### 3.2 Agent Behavior Updates (`advisor.md`)

#### A. Iterative Refinement Behavior

```markdown
## Iterative Image Refinement

When user requests changes to a generated image:

1. **Retrieve Context**
   - Get `original_prompt` from last generation metadata
   - Get `reference_image` if one was used

2. **Apply Minimal Edit**
   - Modify ONLY the part the user mentioned
   - Keep prompt structure intact
   - Preserve all other descriptors

3. **Call generate_image**
   - Same `product_slug` if applicable
   - Same `reference_image`
   - Updated prompt with targeted change

Example flow:
User: "Make the lighting warmer"
Agent: [Retrieves previous prompt, changes "soft morning light"
       to "warm golden hour light", calls generate_image]
```

#### B. Sketch/Layout Detection

```markdown
## Sketch & Layout Handling

When user attaches an image that appears to be:
- A hand-drawn sketch
- A wireframe
- A layout diagram
- A floor plan
- A schematic

Treat it as a **layout reference**, not a product reference:

1. Use as `reference_image`
2. Prompt pattern: "Following this [type] exactly, create [final output]..."
3. Do NOT apply identity validation (this isn't a product photo)
4. Describe what should fill in the sketch (colors, textures, content)
```

#### C. Edit Mode Detection

```markdown
## Image Edit Mode

When user wants to MODIFY an existing image (not generate new):

Trigger phrases:
- "remove the background"
- "change the [color/style/setting]"
- "enhance this"
- "colorize this"
- "restore this"
- "clean up"
- "crop and..."

Behavior:
1. Use the target image as `reference_image`
2. Describe the desired outcome naturally
3. Do NOT use validate_identity (editing doesn't require product matching)
```

---

### 3.3 Implementation Changes

#### A. Skill File Updates

| File | Change |
|---|---|
| `skills/image_prompt_engineering/SKILL.md` | Add new sections per 3.1 |
| `skills/image_prompt_engineering/triggers.yaml` | Expand keyword list |

#### B. Prompt File Updates

| File | Change |
|---|---|
| `prompts/advisor.md` | Add iterative refinement, sketch handling, edit mode sections |

#### C. Tool Updates (Optional Enhancement)

| File | Change |
|---|---|
| `tools.py` | Add `edit_mode: bool` parameter to distinguish edit vs generate |
| `tools.py` | Store `original_prompt` in generation metadata for retrieval |

---

## 4. New Use Cases Enabled

### 4.1 Infographic Generation
```
User: "Create an infographic showing our product's 3 key benefits"
Agent prompt: "An elegant infographic layout with the product centered,
three benefit icons surrounding it with labels "ORGANIC", "ECO-FRIENDLY",
"HANDCRAFTED" in modern sans-serif typography, connected by flowing
lines on a soft gradient background..."
```

### 4.2 Sketch-to-Final
```
User: [attaches hand-drawn ad layout] "Turn this into a final ad"
Agent prompt: "Following this sketch layout exactly, create a polished
advertisement for [product]. Replace rough shapes with the actual product,
fill background area with lifestyle environment, render text areas with
proper typography..."
```

### 4.3 Background Removal/Replacement
```
User: [attaches product on cluttered desk] "Put this on a marble surface"
Agent prompt: "Keep the product exactly as shown, remove the background
and place on an elegant white marble surface with soft natural lighting..."
```

### 4.4 2D to 3D Conversion
```
User: [attaches flat label design] "Show this as a 3D bottle"
Agent prompt: "Based on this label design, generate a photorealistic 3D
bottle render with the label wrapped around a frosted glass surface,
studio lighting, 45-degree angle..."
```

### 4.5 Iterative Refinement
```
Generation 1: "Warm kitchen scene..."
User: "Can you make the lighting cooler?"
Agent: [Uses same prompt, changes lighting descriptor only]
```

---

## 5. Testing Strategy

### Test Matrix

| Scenario | Input | Expected Behavior | Validation |
|---|---|---|---|
| Basic product shot | Product slug + "hero image" | 5-point formula prompt, identity validation | Product matches reference |
| Infographic | "infographic with features" | Quoted text, layout description | Text legible, layout coherent |
| Image editing | Attached image + "remove background" | Edit mode, reference_image used | Background removed, product intact |
| Sketch layout | Attached sketch + "make final ad" | Layout reference, no identity validation | Follows sketch structure |
| Multi-product | 2-3 product slugs | Explicit differentiation, material details | All products accurate |
| 2D to 3D | Blueprint + "3D render" | Dimensional translation prompt | Realistic 3D from 2D input |
| Iterative edit | "warmer lighting" | Minimal prompt change | Only lighting differs |

### Acceptance Criteria
1. **Product Identity**: Zero deviation from reference (materials, colors, proportions)
2. **Text Rendering**: Quoted text appears legible and correctly styled
3. **Layout Following**: Sketch layouts translate to final with correct placement
4. **Iterative Efficiency**: Refinement uses previous prompt, not fresh generation
5. **Trigger Coverage**: All new keywords activate the skill

---

## 6. Success Metrics

| Metric | Baseline | Target |
|---|---|---|
| Identity validation pass rate | TBD | >95% first attempt |
| Text legibility in infographics | N/A | >90% readable |
| User refinement iterations | TBD | -30% reduction |
| Sketch-to-final accuracy | N/A | Layout matches >85% |

---

## 7. Rollout Phases

### Phase 1: Skill Enhancement
- Update `SKILL.md` with new sections
- Expand trigger keywords
- Test basic scenarios

### Phase 2: Agent Behavior
- Add iterative refinement logic to `advisor.md`
- Add sketch/edit mode detection
- Test all use cases

### Phase 3: Tool Improvements (Optional)
- Add `edit_mode` parameter
- Implement prompt metadata storage
- Enable multi-reference support for mood boards

### Phase 4: Validation & Monitoring
- Deploy to staging
- Run full test matrix
- Collect user feedback
- Iterate on prompt phrasing

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Text rendering still poor | Medium | Iterate on quoting patterns, add font descriptors |
| Sketch layout ignored | Medium | Add explicit "follow exactly" phrasing |
| Iterative edits drift | Low | Store and compare prompts, warn on major changes |
| Trigger keyword conflicts | Low | Review existing skills for overlap |
| Skill file too large | Low | Consider splitting if >500 lines |

---

## 9. Dependencies

- Gemini 3.0 Pro API (existing)
- OpenAI Agents SDK (existing)
- No new external dependencies required

---

## 10. Open Questions

1. **Multi-reference support**: Should we allow multiple generic reference images (e.g., style + layout) in single generation?
2. **Edit mode flag**: Is explicit `edit_mode` parameter worth the added complexity, or can agent infer from prompt?
3. **Prompt history**: How to efficiently store/retrieve previous generation prompts for iterative refinement?

---

## Appendix A: Nano-Banana Pro Golden Rules

1. **Edit, Don't Re-roll** - Iterative refinement over fresh generations
2. **Natural Language** - Full sentences, not keyword tags
3. **Be Specific** - Materials, textures, precise details
4. **Provide Context** - Purpose, audience, platform
5. **Quote Text** - Exact text in double quotes
6. **Trust the Model** - It understands physics, layout, intent

---

## Appendix B: Example Prompt Templates

### Product Hero Shot
```
A [material] [product type] with [distinctive features],
placed [position] on [surface] in [environment].
Shot as [photography style] with [lighting description],
[camera angle] capturing [focal point].
For [purpose/platform].
```

### Infographic
```
An [style] infographic featuring [product] centered,
with [N] [elements] arranged [layout pattern].
Text elements: "[text1]", "[text2]", "[text3]"
in [typography style].
Background: [description].
For [audience/platform].
```

### Image Edit
```
Keep the [subject] exactly as shown.
[Action]: [specific change description].
Maintain [preserved elements].
Result should appear [quality descriptors].
```

### Sketch to Final
```
Following this [sketch type] exactly, create [output type].
Replace [sketch elements] with [final elements].
Apply [style/colors/textures] from [brand/product].
Render in [quality level] with [lighting].
```

---

*Document Version: 1.0*
*Based on: Plan for State-of-the-Art Gemini 3 Prompting.md*
*Last Updated: 2025-12-26*
