---
name: image-prompt-engineering
description: Craft effective prompts for Gemini image generation - MUST READ before any generate_image call
triggers:
  - image
  - generate_image
  - generate image
  - generate an image
  - create image
  - create an image
  - make image
  - make an image
  - make me an image
  - image generation
  - lifestyle image
  - product image
  - hero image
  - picture
  - photo
  - photograph
  - visual
  - artwork
  - graphic
  - illustration
  - render
tools_required:
  - generate_image
priority: high
---

# Image Prompt Engineering

**CRITICAL**: Read and apply these guidelines BEFORE every `generate_image` call.

## Core Principle

**Describe scenes narratively, not as keyword lists.**

| Bad (keyword soup) | Good (narrative) |
|---|---|
| "coffee shop, cozy, warm lighting, minimalist" | "A minimalist coffee shop interior with warm pendant lighting casting soft shadows on blonde wood tables. Morning sunlight streams through floor-to-ceiling windows." |
| "dog, park, happy" | "A golden retriever puppy with floppy ears bounding through a sun-dappled meadow, tongue out, pure joy in motion." |

## Advanced Prompting Techniques

### Texture & Material Details
When describing subjects, include surface and material properties for photorealism:
- **Surface finish**: matte, glossy, frosted, brushed, satin, textured, polished
- **Material properties**: soft velvet, cold steel, warm wood grain, cool ceramic, supple leather
- **Imperfections for realism**: condensation droplets, dust particles, fingerprint smudges, micro-scratches, patina

**Examples**:
```
"A frosted glass bottle with visible condensation droplets running down its surface,
brushed copper cap showing subtle machining marks and a soft patina..."

"Matte black packaging with a soft-touch finish, catching light at the edges
to reveal a subtle texture, slight dust particles visible in the studio lighting..."

"Warm oak wood table with visible grain patterns and natural knots,
a few minor scratches from use adding authentic character..."
```

**Why this matters**: Nano-Banana Pro excels at rendering fine details. Including texture and material information produces more realistic, believable images with depth and tactile quality.

### Text Rendering
For legible, well-rendered text in images:
1. **Quote exact text** with double quotes in your prompt
2. **Specify typography**: font style (serif, sans-serif, script), relative size, color/treatment
3. **Describe placement** precisely (centered, above product, along edge, etc.)

**Examples**:
```
"A product label with **"BLOOM ORGANIC"** in elegant serif typography,
gold foil embossed on matte black packaging, centered on the front panel..."

"A coffee bag featuring **"DARK ROAST"** in bold condensed sans-serif,
white text on a dark brown kraft paper surface, positioned at the top third..."

"An advertisement banner with **"50% OFF TODAY"** in vibrant red italic lettering,
large relative to the frame, positioned in the upper right corner with a subtle drop shadow..."
```

**Why this matters**: Nano-Banana Pro can render legible, styled text when instructed properly. The key is quoting exact text and being specific about typography treatment. Without quotes, the model may omit text or render it illegibly.

### Iterative Refinement ("Edit, Don't Re-roll")
When an image is 80% correct and user requests small changes, don't regenerate from scratch. Use iterative refinement to preserve what's working.

**Critical Requirement**: Refinement requires BOTH:
1. **Previous OUTPUT image as `reference_image`** (not just edited prompt)
2. **Modified prompt** with targeted change

**Path Conversion**: `generate_image` returns absolute paths (e.g., `/Users/.../output/image.png`). Before using as `reference_image`, convert to brand-relative path (e.g., `assets/generated/image.png`).

**Scope Limitation (Single-Reference Only)**: Iterative refinement works for:
- ✅ Single product image refinement (no `product_slug`)
- ✅ Non-product image refinement (lifestyle shots, backgrounds)
- ❌ Multi-product flows (`product_slugs` ignores `reference_image`)
- ❌ Combined output + product_slug refs (not supported)

For multi-product refinement, regenerate fresh with same `product_slugs` and adjusted prompt.

**Decision Tree**:
```
User requests change on recent generation:

1. Was it a multi-product generation (product_slugs)?
   YES → Cannot use output as reference. Regenerate fresh with
         same product_slugs + adjusted prompt. Warn user that
         composition may vary.
   NO  → Continue to step 2

2. What kind of change?
   "change X" (lighting, angle, color) → Use output as reference + edit prompt
   "try something different"          → Fresh generation, no reference
```

**Examples**:
```python
# First generation
result = generate_image(prompt="Product bottle on marble counter, soft morning light...", ...)
# Returns: /Users/project/output/brands/acme/assets/generated/hero_001.png

# User: "Make the lighting warmer"
# Convert to relative path and use as reference:
generate_image(
    prompt="Product bottle on marble counter, warm golden hour light...",  # Only lighting changed
    reference_image="assets/generated/hero_001.png",  # Previous output as reference
    validate_identity=False  # Not a product identity check
)
```

```python
# User: "Try a completely different angle"
# Fresh generation - no reference, new composition:
generate_image(
    prompt="Product bottle on marble counter, dramatic low angle, soft morning light...",
    product_slug="acme-bottle",  # Use product_slug for identity
    validate_identity=True
)
```

**Why this matters**: Iterative refinement reduces iteration cycles by preserving what's already working. Re-rolling from scratch often loses good composition, lighting, or placement that was hard to achieve.

### Image Editing via Language
Nano-Banana Pro can perform image edits through natural language—no masks or pixel operations needed. Use the source image as `reference_image` and describe the desired outcome.

**Key Principle**: Describe WHAT you want, not HOW to do it. Trust the model to handle low-level operations.

**Path Conversion**: When editing a recently generated image, convert absolute path to brand-relative path before using as `reference_image`.

**validate_identity Decision Table**:
| Edit Type | validate_identity | Reason |
|-----------|-------------------|--------|
| Remove background from product | `True` | Product must stay identical |
| Relight/cleanup product photo | `True` | Product must stay identical |
| Color correction on product | `True` | Product must stay identical |
| Colorize old photo | `False` | Not a product identity task |
| Style transfer | `False` | Intentionally changing appearance |
| Follow sketch/layout reference | `False` | Reference is layout, not product |
| Restore damaged photo | `False` | Not validating against reference |
| Generic background replacement | `False` | Only background changes |

**Examples**:
```python
# Remove background - product identity matters
generate_image(
    prompt="Keep the product exactly as shown. Remove the cluttered background and place on pure white seamless backdrop with soft studio lighting.",
    reference_image="assets/uploads/product_desk.png",
    validate_identity=True  # Product must remain identical
)
```

```python
# Relight product photo - product identity matters
generate_image(
    prompt="Same product, same position. Change from harsh flash lighting to soft, diffused natural window light from the left. Add subtle shadows for depth.",
    reference_image="assets/generated/product_001.png",
    validate_identity=True  # Product must remain identical
)
```

```python
# Colorize vintage photo - NOT a product identity task
generate_image(
    prompt="Colorize this black-and-white photograph with realistic, period-appropriate colors. Skin tones should be natural, fabrics should match 1950s era fashion colors.",
    reference_image="assets/uploads/vintage_photo.jpg",
    validate_identity=False  # Not validating product identity
)
```

```python
# Style transfer - intentionally changing appearance
generate_image(
    prompt="Transform this photograph into a watercolor painting style. Maintain composition and subject but apply loose, flowing brushstrokes and soft color blending.",
    reference_image="assets/uploads/original.png",
    validate_identity=False  # Intentionally altering appearance
)
```

**Why this matters**: Nano-Banana Pro understands editing intent from natural language. By describing the outcome ("remove background", "add warmth") rather than pixel operations, you get better results with less effort.

---

## The 5-Point Prompt Formula

Build every prompt with these elements:

### 1. Subject (WHAT)
Be hyper-specific. Replace generic terms with precise descriptions.

- "a bottle" → "a frosted glass bottle with a copper cap and embossed leaf pattern"
- "a person" → "a woman in her 30s with curly auburn hair, wearing a cream linen blazer"

### 2. Setting (WHERE)
Describe the environment and what surrounds the subject.

- "outdoors" → "in a sun-dappled forest clearing with ferns and moss-covered rocks"
- "kitchen" → "on a marble countertop in a bright Scandinavian kitchen with copper fixtures"

### 3. Style (HOW IT LOOKS)
Specify the visual medium and aesthetic.

**Photography**: "shot on 35mm film, shallow depth of field, natural lighting"
**Illustration**: "flat vector illustration with bold outlines, limited color palette"
**3D**: "isometric 3D render with soft shadows, clay material"
**Editorial**: "high-fashion editorial photography, dramatic lighting, Vogue aesthetic"

### 4. Lighting/Mood (ATMOSPHERE)
Define the emotional quality through light.

- "golden hour backlighting with lens flare"
- "soft diffused overcast, moody and contemplative"
- "dramatic chiaroscuro with deep shadows"
- "bright, airy, high-key studio lighting"

### 5. Composition (CAMERA)
Direct the framing and perspective.

- "wide-angle shot from low angle, subject towering"
- "tight close-up on hands, shallow focus"
- "bird's eye view, flat lay arrangement"
- "three-quarter portrait, looking off-camera"

## Quick Reference: Prompt Template

```
[Subject with specific details],
[setting/environment],
[style/medium],
[lighting/mood],
[composition/camera angle].
[Purpose: what this image is for]
```

**Example**:
```
A frosted glass bottle of artisanal olive oil with a hand-drawn label,
placed on a rustic wooden cutting board surrounded by fresh rosemary and garlic cloves,
editorial food photography style with natural window light,
warm afternoon glow creating soft shadows,
45-degree overhead angle, shallow depth of field.
Hero image for premium food brand website.
```

## Critical Do's and Don'ts

### DO:
- **Be specific over generic**: "ornate Victorian brass keyhole" not "old keyhole"
- **Include material textures**: surface finishes, material properties, realistic imperfections
- **Quote exact text for rendering**: Use **"EXACT TEXT"** in double quotes with typography details
- **State purpose**: "A hero image for a luxury skincare homepage" gives context
- **Use positive framing**: "an empty street at dawn" not "a street with no cars"
- **Layer details**: Start broad, then add specific elements

### DON'T:
- **List disconnected keywords**: "modern, sleek, professional, blue" (no context)
- **Use negatives**: "no people", "without text", "not busy" (Gemini ignores these)
- **Be vague about style**: "make it look good" or "professional quality"
- **Assume context**: The model doesn't know your brand unless you describe it
- **Over-specify**: Too many constraints can conflict; focus on what matters most

## Reference Images

When using `reference_image` parameter:

### To Preserve Subject Identity
Use with `validate_identity=True` when the exact product/item must appear:

```python
generate_image(
    prompt="The product bottle on a marble bathroom counter, morning light through frosted window, spa aesthetic",
    reference_image="path/to/product.png",
    validate_identity=True
)
```

Describe what to KEEP (the product) and what to CHANGE (the setting).

### For Style/Mood Reference
Use without validation when the reference is for inspiration only:

```python
generate_image(
    prompt="A coffee cup in this same warm, golden lighting style and color palette",
    reference_image="path/to/mood_reference.jpg"
)
```

## Before Calling generate_image

Mental checklist:
- [ ] Is my subject specific (not generic)?
- [ ] Did I describe the setting/background?
- [ ] Is the style/medium clear?
- [ ] Did I set the mood through lighting?
- [ ] Is the composition directed?
- [ ] If using reference: did I specify what to keep vs. change?

## Common Fixes

| Problem | Solution |
|---------|----------|
| Image too generic | Add 2-3 more specific details about the subject |
| Wrong style | Explicitly name the medium: "digital illustration", "35mm photograph" |
| Composition off | Add camera language: "close-up", "wide shot", "overhead view" |
| Mood doesn't match | Describe lighting specifically: "soft diffused", "dramatic shadows" |
| Text rendering issues | Describe font style: "bold sans-serif", "elegant script" |
