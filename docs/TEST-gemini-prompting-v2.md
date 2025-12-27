# Test Cases: Gemini 3.0 Pro Prompting Enhancement

**Version**: 1.0
**Created**: 2025-12-26
**Related**: IMPLEMENTATION_PLAN-gemini-prompting-v2.md, SPEC-gemini-prompting-v2.md

---

## Overview

This document defines test cases for validating the Gemini 3.0 Pro ("Nano-Banana Pro") prompting enhancements. All tests verify prompt structure and tool parameter usage—no actual image generation required for validation.

---

## Test Categories

### 1. Basic Product Shot (Regression)

Ensures existing functionality remains intact after enhancements.

| ID | Test Case | Input | Expected Prompt Pattern | Expected Parameters |
|----|-----------|-------|------------------------|---------------------|
| REG-01 | Single product hero | "Create a hero image for our coffee bag" with product_slug | 5-point formula (subject, setting, style, lighting, composition) + texture/material | `product_slug`, `validate_identity=True` |
| REG-02 | Multi-product group | "Show all three products together" with product_slugs | Explicit differentiation per product, material details for each | `product_slugs`, `validate_identity=True` |
| REG-03 | Lifestyle context | "Product in kitchen setting" | Natural environment description + product placement | `product_slug`, `validate_identity=True` |

**Acceptance Criteria**:
- Prompt uses complete sentences, NOT keyword soup
- 5-point formula elements present (subject, setting, style, lighting, composition)
- Material/texture details included per Task 1 guidance
- Product identity validated when product_slug used

---

### 2. Texture & Material Details (Task 1)

Validates material and surface property inclusion.

| ID | Test Case | Input | Expected Prompt Pattern |
|----|-----------|-------|------------------------|
| TEX-01 | Surface finish | "Glossy ceramic vase product shot" | Includes finish descriptors: glossy, smooth, reflective |
| TEX-02 | Material properties | "Leather handbag hero" | Includes material feel: supple leather, stitching detail |
| TEX-03 | Imperfections | "Rustic wooden table setting" | Includes realistic details: grain patterns, minor scratches, patina |
| TEX-04 | Condensation | "Cold beverage bottle" | Includes: condensation droplets, visible moisture |

**Acceptance Criteria**:
- Surface finish (matte/glossy/frosted/etc.) present in prompt
- Material properties described (soft velvet, cold steel, warm wood, etc.)
- Imperfections added for photorealism when appropriate

---

### 3. Text Rendering (Task 2)

Validates proper text quoting and typography specification.

| ID | Test Case | Input | Expected Prompt Pattern | Validation |
|----|-----------|-------|------------------------|------------|
| TXT-01 | Label text | "Product label with ORGANIC text" | `**"ORGANIC"**` in double quotes | Text quoted correctly |
| TXT-02 | Typography style | "Bold headline SUMMER SALE" | Font style specified: serif/sans-serif, bold/italic | Typography detailed |
| TXT-03 | Text placement | "Brand name at top of package" | Placement described: centered, top third, corner | Location precise |
| TXT-04 | Multiple text | "50% OFF and FREE SHIPPING labels" | Both texts quoted: `**"50% OFF"**`, `**"FREE SHIPPING"**` | All text quoted |

**Acceptance Criteria**:
- Exact text enclosed in double quotes with bold markers
- Typography style specified (font family, weight, color)
- Placement precisely described

---

### 4. Iterative Refinement (Task 3)

Validates "Edit, Don't Re-roll" workflow.

| ID | Test Case | Input | Expected Behavior | Expected Parameters |
|----|-----------|-------|-------------------|---------------------|
| REF-01 | Lighting change | Previous output + "make lighting warmer" | Only lighting descriptor changes | `reference_image` (previous output, relative path), `validate_identity=False` |
| REF-02 | Angle change | Previous output + "try different angle" | Fresh generation for major composition change | `product_slug`, no `reference_image`, `validate_identity=True` |
| REF-03 | Color adjustment | Previous output + "make background darker" | Keep subject, change background | `reference_image`, `validate_identity=False` |
| REF-04 | Multi-product refinement | Previous multi-product + "warmer colors" | Fresh generation (reference_image ignored for product_slugs) | `product_slugs`, no `reference_image` |
| REF-05 | Path conversion | Absolute path returned from generate_image | Converted to brand-relative path for reference_image | Path starts with `assets/` not `/Users/` |

**Acceptance Criteria**:
- Single-reference refinement uses previous OUTPUT as reference_image
- Path converted from absolute to brand-relative
- Multi-product flows regenerate fresh (warn user composition may vary)
- "Try something different" triggers fresh generation, not refinement

---

### 5. Image Editing via Language (Task 4)

Validates natural language editing workflow.

| ID | Test Case | Input | Expected Prompt Pattern | Expected Parameters |
|----|-----------|-------|------------------------|---------------------|
| EDT-01 | Remove background (product) | "Remove background from this product photo" | "Keep product exactly as shown, remove background..." | `reference_image`, `validate_identity=True` |
| EDT-02 | Relight product | "Make the lighting softer" on product | "Same product, change lighting to..." | `reference_image`, `validate_identity=True` |
| EDT-03 | Colorize photo | "Colorize this black-and-white photo" | "Colorize with realistic, period-appropriate colors..." | `reference_image`, `validate_identity=False` |
| EDT-04 | Style transfer | "Make this look like watercolor" | "Transform into watercolor painting style..." | `reference_image`, `validate_identity=False` |
| EDT-05 | Background replacement | "Put this on marble" | "Keep subject, replace background with marble..." | `reference_image`, context-dependent validate_identity |

**Acceptance Criteria**:
- Correct validate_identity per decision table:
  - Product edits (remove bg, relight, cleanup) → `True`
  - Non-product edits (colorize, style transfer) → `False`
- Source image used as reference_image
- Prompt describes outcome, NOT pixel operations

---

### 6. Sketch/Layout Control (Task 5)

Validates layout-following workflow.

| ID | Test Case | Input | Expected Prompt Pattern | Expected Parameters |
|----|-----------|-------|------------------------|---------------------|
| SKT-01 | Ad wireframe | "Turn this wireframe into a final ad" | "Following this wireframe exactly, create..." | `reference_image`, `validate_identity=False` |
| SKT-02 | UI mockup | "Based on this sketch, create polished UI" | "Following this sketch layout exactly..." | `reference_image`, `validate_identity=False` |
| SKT-03 | Floor plan to 3D | "Make this floor plan into a 3D interior" | "Following this floor plan layout exactly..." | `reference_image`, `validate_identity=False` |
| SKT-04 | Ambiguous image | Image attached, no explicit intent | Ask user via propose_choices: "Is this a product reference or layout guide?" | No generation until clarified |
| SKT-05 | Sketch + product_slug | Sketch attached + product_slug present | Treat as product identity reference, NOT layout | `product_slug`, `validate_identity=True` |

**Acceptance Criteria**:
- Explicit layout keywords trigger Layout Flow
- product_slug presence triggers Identity Flow (overrides layout)
- Ambiguous cases prompt for clarification
- Layout references use validate_identity=False

---

### 7. Dimensional Translation (Task 6)

Validates 2D↔3D conversion prompting.

| ID | Test Case | Input | Expected Prompt Pattern | Expected Parameters |
|----|-----------|-------|------------------------|---------------------|
| DIM-01 | Label to bottle | Flat label + "show as 3D bottle" | "Based on this label design, generate photorealistic 3D bottle..." | `reference_image`, `validate_identity=False` |
| DIM-02 | Blueprint to 3D | Blueprint + "create 3D render" | "Based on this blueprint, generate photorealistic 3D render..." | `reference_image`, `validate_identity=False` |
| DIM-03 | 3D to illustration | 3D render + "make flat illustration" | "Convert this 3D scene to flat vector illustration..." | `reference_image`, `validate_identity=False` |
| DIM-04 | Merge brand attributes | Label + brand colors | Prompt includes brand palette colors, typography style | Brand attributes merged into prompt |

**Acceptance Criteria**:
- Correct conversion pattern (2D→3D or 3D→2D)
- Material and form descriptions for 3D output
- Brand attributes merged when available
- validate_identity=False (reference is source design, not product identity)

---

### 8. Trigger Keywords (Task 7)

Validates skill activation on correct triggers.

| ID | Test Case | Trigger Phrase | Should Activate | Notes |
|----|-----------|---------------|-----------------|-------|
| TRG-01 | Core: image | "create an image" | ✅ Yes | |
| TRG-02 | Core: photo | "take a photo" | ✅ Yes | |
| TRG-03 | Infographic | "create an infographic" | ✅ Yes | |
| TRG-04 | Diagram | "make a diagram" | ✅ Yes | |
| TRG-05 | Layout: wireframe | "turn this wireframe into" | ✅ Yes | |
| TRG-06 | Layout: sketch layout | "based on this sketch layout" | ✅ Yes | |
| TRG-07 | Edit: remove background | "remove background" | ✅ Yes | Specific phrase |
| TRG-08 | Edit: edit image | "edit image" | ✅ Yes | Specific phrase |
| TRG-09 | Edit: colorize photo | "colorize photo" | ✅ Yes | Specific phrase |
| TRG-10 | Dimensional: 3D render | "3D render" | ✅ Yes | |
| TRG-11 | False positive: edit code | "edit the code" | ❌ No | Should NOT trigger |
| TRG-12 | False positive: remove file | "remove this file" | ❌ No | Should NOT trigger |
| TRG-13 | False positive: enhance API | "enhance the API" | ❌ No | Should NOT trigger |

**Acceptance Criteria**:
- All specific trigger phrases activate skill
- Generic words ("edit", "remove", "enhance") alone do NOT trigger
- No false positives on code/API/file tasks

---

### 9. Infographic with Text (Composite)

Validates combined text rendering + layout.

| ID | Test Case | Input | Expected Prompt Pattern | Validation |
|----|-----------|-------|------------------------|------------|
| INF-01 | Three benefits | "Infographic showing 3 product benefits" | Layout + quoted text for each: `**"BENEFIT 1"**`, etc. | All text quoted, layout described |
| INF-02 | Comparison chart | "Comparison chart: us vs competitors" | Chart layout + quoted labels + visual differentiation | Structure + typography detailed |
| INF-03 | Process flow | "Show our 4-step process" | Flow layout + numbered/labeled steps with quoted text | Sequential layout + text |

**Acceptance Criteria**:
- Layout pattern (radial, grid, flow) specified
- All text properly quoted with typography
- Color palette from brand if available

---

### 10. End-to-End Workflow (Integration)

Full workflow tests combining multiple capabilities.

| ID | Test Case | Workflow | Validation Points |
|----|-----------|----------|-------------------|
| E2E-01 | Generate → Refine → Final | 1) Generate hero 2) "warmer lighting" 3) "add brand text" | Each step uses correct pattern; refinement uses reference |
| E2E-02 | Sketch → 3D → Edit | 1) Wireframe to ad 2) "add 3D product mockup" 3) "remove background" | Layout flow → dimensional → edit flow correctly |
| E2E-03 | Multi-product → Individual | 1) Group shot 2) "zoom in on the blue bottle" | Multi-product → single product with fresh generation |

**Acceptance Criteria**:
- Workflow transitions detected correctly
- Correct parameters at each step
- Path conversion applied when needed

---

## Validation Checklist

### Before PR Merge

- [ ] All REG-* (regression) tests pass
- [ ] All TEX-* (texture) tests demonstrate material descriptions
- [ ] All TXT-* (text) tests show proper quoting
- [ ] All REF-* (refinement) tests use correct reference_image handling
- [ ] All EDT-* (editing) tests apply correct validate_identity
- [ ] All SKT-* (sketch) tests follow deterministic detection rules
- [ ] All DIM-* (dimensional) tests use correct conversion patterns
- [ ] All TRG-* (trigger) tests confirm correct skill activation
- [ ] No false positives on code/API/file edit triggers

### Manual Verification (Post-Merge)

- [ ] Generate actual images with new prompting techniques
- [ ] Verify text legibility in infographics
- [ ] Verify layout following from sketch inputs
- [ ] Verify iterative refinement preserves composition
- [ ] Verify product identity maintained with validate_identity=True

---

## How to Run Tests

### Prompt Structure Verification
1. Set up test conversation with advisor
2. Issue test input from tables above
3. Intercept `generate_image` call parameters
4. Verify prompt matches expected pattern
5. Verify parameters match expected values

### Trigger Verification
1. Check skill activation logs
2. Verify `image-prompt-engineering` skill loaded for TRG-01 through TRG-10
3. Verify skill NOT loaded for TRG-11 through TRG-13

### Integration Testing
1. Run full E2E workflow scenarios
2. Log all generate_image calls with parameters
3. Verify reference_image paths correctly converted
4. Verify validate_identity correctly set at each step

---

*Document Version: 1.0*
*Last Updated: 2025-12-26*
