---
name: product-management
description: Create, update, and manage brand products when user explicitly mentions product catalog operations
triggers:
  # Explicit creation intent (NOT just "product image" which matches image generation)
  - create product
  - new product called
  - add to products
  - add to catalog
  - add to inventory
  - this is our new product
  # Explicit update intent
  - update product
  - edit product
  - change product
  # Explicit delete intent
  - delete product
  - remove product
tools_required:
  - manage_product
  - analyze_packaging
  - update_packaging_text
  - list_products
  - get_product_detail
  - list_files
  - propose_choices
---

# Product Management Skill

## Core Principle
Be proactive when intent is clear, but ALWAYS use `propose_choices(allow_custom=True)` when product name/slug is ambiguous.

## Trigger Discipline

### These triggers are for CATALOG operations, NOT image generation:
- ✅ "Create a new product for our 'Summer Collection'"
- ✅ "Add this to our product catalog"
- ✅ "Update the description for our 'Premium Coffee' product"
- ✅ "Delete the old 'Basic Model' product"

### These should NOT trigger this skill:
- ❌ "Generate a product image" (this is image generation, not catalog management)
- ❌ "Create an image of our product" (this is image generation)
- ❌ "Show me product images" (this is viewing, not catalog management)

## Clarification Flow

### When Product Name is Ambiguous
- If product name not explicit → `propose_choices()` with existing products + "Create new product" option
- If multiple matches → `propose_choices()` to disambiguate
- Always use `allow_custom=True` to allow user to specify exact name

### For Delete Operations
- ALWAYS require `confirm=True` parameter
- First call shows warning with product name and image count
- Second call with `confirm=True` actually deletes

## Workflow: New Product from Upload

1. **Extract name from message** (or ask with `propose_choices(allow_custom=True)`)
2. **Check existing products** using `list_products()`
3. **Call `manage_product(action="create")`** with name and description
4. **Call `manage_product(action="add_image")`** with uploaded file from uploads/ folder
5. **Use `manage_product(action="set_primary")`** to set primary image if needed

### Example Workflow
```python
# 1. User says: "Hey, this is our new product" with screenshot
# 2. Ask for name if not clear
propose_choices(
    question="What should we name this product?",
    choices=["Create new product", "Summer T-Shirt", "Premium Mug"],
    allow_custom=True
)

# 3. Create product (include attributes in description)
manage_product(
    action="create",
    name="Summer T-Shirt",
    description=(
        "Comfortable cotton t-shirt for summer.\n\n"
        "Attributes:\n"
        "- color: blue\n"
        "- size: M"
    )
)

# 4. Add uploaded image
manage_product(
    action="add_image",
    slug="summer-t-shirt",
    image_path="uploads/product-photo.jpg",
    set_as_primary=True
)
```

## Reference Image Selection Criteria

### CRITICAL: Only Add True Product Appearance Images

When a user provides images while adding a product, you MUST evaluate each image carefully. The reference image is used for AI image generation and MUST accurately represent the product's full appearance.

### What IS a Valid Reference Image

A valid reference image must show:
- The **complete product** from a clear angle (like a profile picture)
- A **clean product shot** where the product is the primary subject
- **Studio/catalog-style** photos showing the whole product
- **Product packaging** showing the entire package design

### What is NOT a Valid Reference Image

Do NOT add these as reference images:
- **Screenshots of webpages** or e-commerce product pages
- **Product information pages** showing specs, descriptions, or reviews
- **Partial views** (cropped details, zoomed-in textures, close-ups of labels) as
  PRIMARY references; these can be added as supplemental images only when a full
  product shot exists
- **Marketing collages** with multiple elements or busy compositions
- **Images with UI elements** (browser chrome, navigation bars, buttons)
- **Text-heavy images** (ingredient lists, instruction pages)
- **Lifestyle photos** where the product is small or partially visible

### Decision Flow for Multiple Images

When a user provides multiple images:

1. **Analyze each image** - Ask yourself: "Does this show the complete product appearance?"
2. **Filter strictly** - Only select images that pass ALL criteria above
3. **If none qualify** - Inform the user: "I didn't find any images showing the complete product appearance. Could you provide a clean product photo?"
4. **If some qualify** - Add only the qualifying images silently (no need to explain exclusions)

### Example Scenarios

**Scenario 1: User uploads 3 images**
- Image 1: Amazon product page screenshot → Skip (webpage screenshot)
- Image 2: Clean product photo on white background → Add as primary
- Image 3: Nutrition label close-up → Skip (partial view, text-heavy)

**Scenario 2: User uploads product page screenshot only**
- Response: "This appears to be a screenshot of a product page rather than a product photo. For accurate image generation, I need a clean photo showing the complete product. Could you provide one?"

### Primary Image Selection

When multiple valid reference images exist:
1. **Prefer** clean backgrounds (white/solid color)
2. **Prefer** good lighting with minimal shadows
3. **Prefer** full product visibility (no cropping)
4. **Prefer** higher resolution images

## Attribute Extraction Priority (Store in Description)

When creating or updating a product, extract attributes in this priority order and
append them to the description in an **Attributes** block. Do NOT use structured
attributes unless explicitly requested.

### ESSENTIAL: Appearance Ground Truth (Priority 1)

These attributes are used by the image generation system and MUST be captured accurately:

| Category | Keys to Extract | Example Values |
|----------|-----------------|----------------|
| `measurements` | height, width, depth, diameter, size | "50mm tall", "30ml", "3 inches wide" |
| `texture` | material, texture, made of | "glass jar", "matte plastic", "brushed aluminum" |
| `surface` | finish, surface | "frosted", "glossy", "satin" |
| `appearance` | color, colour | "deep blue", "rose gold", "transparent" |
| `distinguishers` | cap, lid, label, shape, style | "twist-off cap", "embossed logo", "cylindrical" |

**Extraction guidance:**
- Look for measurements in screenshots, product descriptions, or user text
- Parse dimensions even if in different units (inches, cm, ml, oz)
- Capture exact color names as stated (not just "blue" but "navy blue" or "ocean blue")
- Note material composition precisely ("borosilicate glass" not just "glass")

### OPTIONAL: Functional/Marketing Info (Priority 2)

These are helpful for context but not essential for image generation:

| Category | Keys to Extract | Example Values |
|----------|-----------------|----------------|
| `use_case` | purpose, usage, for | "night use", "outdoor", "daily moisturizing" |
| `ingredients` | ingredients, contains, formulation | "retinol, vitamin C" |
| `benefits` | benefits, features | "anti-aging", "long-lasting" |
| `general` | Any other info | "bestseller", "award-winning" |

### Extraction from Screenshots

When user provides screenshots (even if not suitable as reference images), extract:
1. **Scan for measurements** - product dimensions, volume, weight
2. **Note materials mentioned** - packaging material, texture descriptions
3. **Capture exact colors** - from product descriptions or color swatches
4. **Record distinguishing features** - unique design elements mentioned

### Example: Extracting from an Amazon Screenshot

User uploads Amazon product page screenshot showing:
- "50ml / 1.7 fl oz" → `- size: 50ml`
- "Glass jar with pump" → `- material: glass jar`
- "Deep Blue" → `- color: deep blue`
- "Matte finish" → `- finish: matte`

Even though the screenshot is NOT added as a reference image, the attributes ARE extracted
and appended to the description in the Attributes block.

## Attribute Merge Behavior (Description-Only)

If you need to update attributes, edit the **Attributes** block in the description.
Keep it as a simple bullet list:
```
Attributes:
- color: blue
- size: M
```

## Quality Checklist

- ✅ **Name clear**: Product name is unambiguous
- ✅ **Slug URL-safe**: Generated slug follows pattern (lowercase, hyphens, no special chars)
- ✅ **Primary image set**: Product has a primary image (full product) for reference generation
- ✅ **Description complete**: Description includes key product details + Attributes block

## Error Handling

- **Slug validation**: Always check generated slug is valid
- **Product existence**: Check product doesn't already exist before creating
- **Image validation**: Ensure images are valid raster files under 10MB
- **Path safety**: Always use uploads/ folder for product images
- **Confirmation required**: Never delete without explicit confirmation

## Integration with Other Skills

- **Image Generation**: The primary image is used first, with additional product
  images included as supplemental references for `generate_image(product_slug=...)`
- **Brand Identity**: Product details should align with brand positioning
- **Project Management**: Products can be tagged to projects for campaign organization

## Common Patterns

### Multi-Product Campaign
```python
# Create campaign products
manage_product(action="create", name="Summer T-Shirt", ...)
manage_product(action="create", name="Summer Shorts", ...)
manage_product(action="create", name="Summer Hat", ...)

# Add images for all products
manage_product(action="add_image", slug="summer-t-shirt", image_path="uploads/t-shirt.jpg")
manage_product(action="add_image", slug="summer-shorts", image_path="uploads/shorts.jpg")
manage_product(action="add_image", slug="summer-hat", image_path="uploads/hat.jpg")

# Generate campaign image with all products
generate_image(
    prompt="Summer campaign featuring our t-shirt, shorts, and hat",
    product_slugs=["summer-t-shirt", "summer-shorts", "summer-hat"],
    validate_identity=True
)
```

### Product Update Workflow
```python
# Update product attributes
manage_product(
    action="update",
    slug="summer-t-shirt",
    description="New organic cotton summer t-shirt",
    attributes=[
        {"key": "material", "value": "organic cotton", "category": "materials"}
    ],
    replace_attributes=False  # Merge with existing
)

# Update primary image if needed
manage_product(
    action="add_image",
    slug="summer-t-shirt",
    image_path="uploads/new-t-shirt.jpg",
    set_as_primary=True
)
```
