---
name: lifestyle-imagery
description: Create lifestyle photos showing products in authentic real-world contexts
triggers:
  - lifestyle
  - lifestyle photo
  - product in use
  - context shot
  - flatlay
  - environmental shot
  - usage photo
tools_required:
  - generate_image
  - load_brand
  - list_files
---

# Lifestyle Imagery Skill

Use this skill when the user wants to create lifestyle photography showing products
or the brand in authentic, aspirational contexts.

## What This Skill Covers

- In-use photography (product being enjoyed)
- Flatlay compositions
- Environmental/context shots
- Scene-setting imagery for marketing

## Prerequisites

Before generating lifestyle imagery:

1. **Load brand identity**: Call `load_brand()` to get brand context
2. **Check existing assets**: Use `list_files("assets/lifestyle/")` to see what exists
3. **Review visual direction**: Note imagery style, keywords, and avoidances
4. **Understand target audience**: Who should be represented in images

## Key Brand Elements for Lifestyle

From the brand identity, extract:

- **Color palette**: Colors to feature in compositions
- **Imagery style**: Photography style (candid, editorial, etc.)
- **Imagery keywords**: Specific visual terms (lighting, mood)
- **Imagery avoidances**: What NOT to include
- **Target audience**: Demographics for representation
- **Settings**: Environments where brand lives
- **Materials**: Physical textures associated with brand

## Types of Lifestyle Images

### 1. In-Use Photography
Product being actively used or enjoyed by target audience.
- Shows the experience, not just the product
- Features people matching target demographics
- Natural, candid moments

### 2. Flatlay Compositions
Top-down view of product with complementary items.
- Curated arrangement of items
- Consistent color palette
- Editorial, aspirational feel

### 3. Environmental/Context Shots
Product or brand presence in a setting.
- Signage, displays, or subtle placement
- Establishes brand atmosphere
- Storytelling through environment

## Prompt Templates

### In-Use Photography
```
Lifestyle photo of [Brand Name] [product] being enjoyed by
[audience description: age, style, context] in a [setting].
[Color palette]: [hex codes or color names].
Style: [imagery keywords from brand].
Lighting: [specific lighting direction].
Mood: [brand tone and feeling].
Avoid: [imagery avoidances].
Natural, candid composition, premium yet approachable.
Photorealistic, editorial quality.
```

Example:
```
Lifestyle photo of Summit Coffee being enjoyed by a professional
in their 30s, casually dressed, in a modern airy kitchen with
natural wood elements. Warm earth tones: browns, creams, navy accents.
Style: warm golden hour, authentic moments, natural textures.
Lighting: soft natural morning light from window.
Mood: calm confidence, daily ritual.
Avoid: stock photo poses, harsh lighting, sterile backgrounds.
Natural, candid composition, premium yet approachable.
Photorealistic, editorial quality.
```

### Flatlay Composition
```
High-angle flatlay of [product] with complementary items
that match the palette ([color list]).
Include: [relevant props matching brand/category].
Style: [imagery keywords].
Balanced spacing, soft shadows, editorial minimalism.
Background: [surface that matches brand aesthetic].
Avoid: [imagery avoidances].
```

Example:
```
High-angle flatlay of premium coffee bag with complementary items:
ceramic pour-over, linen napkin, artisanal pastry, succulent plant.
Palette: warm browns #8B7355, cream #F5F5DC, navy accent #2C3E50.
Style: organic, artisanal, carefully curated.
Balanced spacing, soft morning shadows, editorial minimalism.
Background: natural wood surface with subtle grain.
Avoid: clutter, harsh shadows, synthetic materials.
```

### Environmental Shot
```
[Brand Name] presence within [environment type]:
[specific placement: signage, countertop, display].
Setting: [detailed environment description].
[Color palette and style keywords].
Subtle depth of field, photorealistic, ambient mood.
No crowded text, clean composition.
Avoid: [imagery avoidances].
```

## Generation Workflow

### Step 1: Understand the Goal
- What story should this image tell?
- Where will this image be used?
- What emotion should it evoke?

### Step 2: Craft Prompt
1. Start with image type and main subject
2. Add audience/model description if people are included
3. Include setting and environment details
4. Apply brand visual direction
5. Specify lighting and mood
6. Add avoidances

### Step 3: Generate and Present
- Use appropriate aspect ratio:
  - In-use: 4:5 (portrait, social media)
  - Flatlay: 4:5 or 1:1 (square)
  - Environmental: 16:9 (wide, hero images)
- Present with context about intended use

### Step 4: Iterate
- Adjust setting, lighting, or composition based on feedback
- Try different angles or arrangements

## Aspect Ratio Guide

| Image Type | Ratio | Use Case |
|------------|-------|----------|
| In-Use Portrait | 4:5 | Instagram, social |
| In-Use Square | 1:1 | Social posts |
| Flatlay | 4:5 or 1:1 | Social, product pages |
| Environmental | 16:9 | Hero images, banners |
| Environmental | 3:4 | Pinterest, tall displays |

## Quality Checks

Before presenting lifestyle imagery:

- [ ] Colors align with brand palette
- [ ] Style matches imagery keywords
- [ ] Avoidances are respected
- [ ] People (if any) match target audience
- [ ] Lighting is appropriate and flattering
- [ ] Composition is balanced and professional
- [ ] No distracting elements
- [ ] Mood aligns with brand personality

## Common Issues and Fixes

### Generic/Stock Photo Feel
- Add more specific, authentic details
- Use "candid", "natural moment", "authentic"
- Include specific environmental elements

### Wrong Lighting
- Be explicit: "soft natural light", "golden hour"
- Specify direction: "from large window on left"

### Wrong Demographics
- Be specific about age, style, setting
- Include lifestyle context clues

### Cluttered Composition
- Add "minimal", "clean composition"
- Reduce number of props
- Emphasize "negative space"

## Saving Lifestyle Assets

`generate_image` saves images under `assets/generated/` and returns the path.
Share those paths with the user instead of calling `write_file` on binary data.

## Series Considerations

When creating multiple lifestyle images:
- Maintain consistent lighting across set
- Use the same color temperature
- Keep styling elements cohesive
- Vary compositions while maintaining style
