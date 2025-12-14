---
name: marketing-materials
description: Create marketing assets like landing pages, social content, merch, and promotional materials
triggers:
  - marketing
  - social media
  - landing page
  - merch
  - merchandise
  - promotional
  - ad
  - advertisement
  - campaign
  - pop-up
  - booth
  - stand
tools_required:
  - generate_image
  - load_brand
  - list_files
---

# Marketing Materials Skill

Use this skill when the user wants to create marketing-focused visual assets
for their brand.

## What This Skill Covers

- Landing page hero images
- Social media content
- Merchandise mockups (totes, apparel, accessories)
- Usage/recipe cards
- Pop-up/booth designs
- Promotional materials

## Prerequisites

Before generating marketing materials:

1. **Load brand identity**: Call `load_brand()` to get brand context
2. **Check for logo**: Use `list_files("assets/logo/")` - logo should be referenced
3. **Review existing assets**: Check other categories for consistency
4. **Understand use case**: Where will this be used?

## Important: Logo Reference

Marketing materials should prominently feature the brand logo.
Include this instruction in prompts:

```
IMPORTANT: Incorporate the brand logo prominently and naturally
in the design. The logo should be readable and properly placed.
```

If logo hasn't been generated yet, create it first using the logo-design skill.

## Types of Marketing Materials

### 1. Landing Page Hero
Wide-format hero image for website landing pages.
- Strong visual hierarchy
- Space for headline/CTA overlay
- Product featured prominently
- Brand colors and style

### 2. Social Media Content
Square or portrait images for social platforms.
- Eye-catching and scroll-stopping
- Brand-consistent styling
- Clear focal point
- Suitable for Instagram, Facebook, etc.

### 3. Usage/Recipe Cards
Educational content showing product use.
- Step-by-step or ingredient visuals
- Clean, readable layout
- Social media friendly format

### 4. Merchandise
Product mockups showing branded merchandise.
- Apparel: t-shirts, hoodies, hats
- Accessories: totes, mugs, notebooks
- Studio quality presentation

### 5. Pop-up/Booth Designs
Physical retail presence concepts.
- Counter and display setup
- Backdrop graphics
- Signage and branding elements

## Prompt Templates

### Landing Page Hero
```
Landing page hero layout for [Brand Name].
Feature: [product hero shot description].
Include: brand logo prominently placed, clean grid layout,
space for headline text, strong CTA area.
Style: [style keywords], [tone].
Palette: [colors with hex codes].
Modern web aesthetic, generous whitespace.
Aspect ratio 16:9, photorealistic quality.
```

### Social Media Post
```
Social media image for [Brand Name] [campaign/content type].
Feature: [main visual element].
Include: logo placement (corner or integrated).
Style: [style keywords], scroll-stopping visual.
Palette: [colors].
Bold composition, clear focal point.
Aspect ratio 1:1, high impact.
```

### Usage/Recipe Card
```
Usage/recipe card for [product] styled for social media.
Show: [specific usage or recipe elements].
Layout: [step indicators OR ingredient arrangement].
Include: logo placement, minimal readable text placeholders.
Style: [style keywords].
Neat clean layout on [background].
Aspect ratio 4:5.
```

### Merchandise Mockup
```
Merchandise assortment for [Brand Name]:
[list items: tote bag, t-shirt, hoodie, mug, etc.].
Feature logo prominently on each item.
Palette: [colors for merchandise].
Style: [style keywords].
Studio lighting, professional product photography.
Arranged attractively, cohesive presentation.
Aspect ratio 4:5.
```

### Pop-up/Booth Design
```
Pop-up stand/booth design for [Brand Name].
Include: counter surface, backdrop graphics with logo,
product display area, [specific elements].
Style: [style keywords].
Palette: [colors].
Small footprint retail presence.
Bright inviting lighting, professional setup.
Aspect ratio 16:9.
```

## Generation Workflow

### Step 1: Clarify Purpose
- What platform/context is this for?
- What's the marketing goal?
- What should be the focal point?

### Step 2: Gather Brand Elements
- Load brand identity
- Get logo path for reference
- Note colors, style, tone

### Step 3: Generate
- Use appropriate aspect ratio
- Include logo reference instruction
- Apply brand visual direction

### Step 4: Present with Context
- Explain how the asset would be used
- Note any text/CTA overlay areas
- Suggest complementary assets

## Aspect Ratio Guide

| Asset Type | Ratio | Platform/Use |
|------------|-------|--------------|
| Landing Page Hero | 16:9 | Website |
| Social Square | 1:1 | Instagram, Facebook |
| Social Portrait | 4:5 | Instagram feed |
| Story/Reel | 9:16 | Stories, TikTok |
| Pinterest | 2:3 | Pinterest |
| Merch Mockup | 4:5 | Product display |
| Pop-up Design | 16:9 | Presentation |

## Quality Checks

Before presenting marketing materials:

- [ ] Logo is visible and properly placed
- [ ] Brand colors are correctly applied
- [ ] Style matches brand identity
- [ ] Purpose is clear (what's being marketed)
- [ ] Composition allows for text overlay (if needed)
- [ ] Professional quality suitable for use
- [ ] Aspect ratio matches intended platform

## Common Issues and Fixes

### Logo Missing or Wrong
- Explicitly state "incorporate brand logo"
- Describe logo placement location

### Too Busy/Cluttered
- Add "generous whitespace"
- "Clean minimal layout"
- Reduce elements

### Generic Stock Feel
- Add brand-specific details
- Include product/brand elements
- Reference brand personality

### Wrong Aspect Ratio
- Specify exact ratio in prompt
- State intended platform

## Saving Marketing Assets

`generate_image` saves images under `assets/generated/` and returns the file path.
Share those returned paths with the user; do not attempt to write binary data
with `write_file`.

## Campaign Considerations

When creating multiple marketing assets:
- Maintain visual consistency across set
- Use same color treatment and filters
- Keep logo placement consistent
- Create cohesive visual campaign language
