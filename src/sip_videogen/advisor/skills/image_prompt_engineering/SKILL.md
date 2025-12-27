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
