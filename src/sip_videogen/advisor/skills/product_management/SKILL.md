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
  - create_product
  - update_product
  - delete_product
  - add_product_image
  - set_product_primary_image
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
3. **Call `create_product()`** with name, description, and attributes
4. **Call `add_product_image()`** with uploaded file from uploads/ folder
5. **Use returned brand-relative path** for `set_product_primary_image()` if needed

### Example Workflow
```python
# 1. User says: "Hey, this is our new product" with screenshot
# 2. Ask for name if not clear
propose_choices(
    question="What should we name this product?",
    choices=["Create new product", "Summer T-Shirt", "Premium Mug"],
    allow_custom=True
)

# 3. Create product
create_product(
    name="Summer T-Shirt",
    description="Comfortable cotton t-shirt for summer",
    attributes=[
        {"key": "color", "value": "blue", "category": "appearance"},
        {"key": "size", "value": "M", "category": "measurements"}
    ]
)

# 4. Add uploaded image
add_product_image(
    product_slug="summer-t-shirt",
    image_path="uploads/product-photo.jpg",
    set_as_primary=True
)
```

## Attribute Merge Behavior

### Default: Merge by (category, key) Case-Insensitive
- Existing attribute: `{"key": "color", "value": "red", "category": "appearance"}`
- New attribute: `{"key": "COLOR", "value": "blue", "category": "APPEARANCE"}`
- Result: `{"key": "color", "value": "blue", "category": "appearance"}` (updated)

### Replace All: Use `replace_attributes=True`
- Existing attributes: `[{color: red}, {size: M}]`
- New attributes: `[{material: cotton}]`
- Result: `[{material: cotton}]` (replaced)

## Quality Checklist

- ✅ **Name clear**: Product name is unambiguous
- ✅ **Slug URL-safe**: Generated slug follows pattern (lowercase, hyphens, no special chars)
- ✅ **Primary image set**: Product has a primary image for reference generation
- ✅ **Attributes meaningful**: Product attributes provide useful information for marketing

## Error Handling

- **Slug validation**: Always check generated slug is valid
- **Product existence**: Check product doesn't already exist before creating
- **Image validation**: Ensure images are valid raster files under 10MB
- **Path safety**: Always use uploads/ folder for product images
- **Confirmation required**: Never delete without explicit confirmation

## Integration with Other Skills

- **Image Generation**: Use product's primary image as reference for `generate_image(product_slug=...)`
- **Brand Identity**: Product attributes should align with brand positioning
- **Project Management**: Products can be tagged to projects for campaign organization

## Common Patterns

### Multi-Product Campaign
```python
# Create campaign products
create_product(name="Summer T-Shirt", ...)
create_product(name="Summer Shorts", ...)
create_product(name="Summer Hat", ...)

# Add images for all products
add_product_image(product_slug="summer-t-shirt", image_path="uploads/t-shirt.jpg")
add_product_image(product_slug="summer-shorts", image_path="uploads/shorts.jpg")
add_product_image(product_slug="summer-hat", image_path="uploads/hat.jpg")

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
update_product(
    product_slug="summer-t-shirt",
    description="New organic cotton summer t-shirt",
    attributes=[
        {"key": "material", "value": "organic cotton", "category": "materials"}
    ],
    replace_attributes=False  # Merge with existing
)

# Update primary image if needed
add_product_image(
    product_slug="summer-t-shirt",
    image_path="uploads/new-t-shirt.jpg",
    set_as_primary=True
)
```