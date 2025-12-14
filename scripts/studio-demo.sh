#!/bin/bash
# Brand Studio Demo Setup
# Creates a sample brand and launches the app for testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BRANDS_DIR="$HOME/.sip-videogen/brands"
SAMPLE_BRAND="summit-coffee"

echo "=== Brand Studio Demo Setup ==="
echo ""

# Create brands directory if needed
mkdir -p "$BRANDS_DIR"

# Check if sample brand exists
if [ ! -d "$BRANDS_DIR/$SAMPLE_BRAND" ]; then
    echo "Creating sample brand: $SAMPLE_BRAND"

    # Create brand directory structure
    mkdir -p "$BRANDS_DIR/$SAMPLE_BRAND/assets/logo"
    mkdir -p "$BRANDS_DIR/$SAMPLE_BRAND/assets/packaging"
    mkdir -p "$BRANDS_DIR/$SAMPLE_BRAND/assets/lifestyle"
    mkdir -p "$BRANDS_DIR/$SAMPLE_BRAND/assets/mascot"
    mkdir -p "$BRANDS_DIR/$SAMPLE_BRAND/assets/marketing"
    mkdir -p "$BRANDS_DIR/$SAMPLE_BRAND/assets/generated"
    mkdir -p "$BRANDS_DIR/$SAMPLE_BRAND/history"
    mkdir -p "$BRANDS_DIR/$SAMPLE_BRAND/docs"

    # Create identity summary (L0)
    cat > "$BRANDS_DIR/$SAMPLE_BRAND/identity.json" << 'EOF'
{
  "slug": "summit-coffee",
  "name": "Summit Coffee Co.",
  "tagline": "Reach your peak, one cup at a time",
  "category": "Premium Coffee",
  "personality_keywords": ["adventurous", "premium", "sustainable", "energizing"],
  "primary_colors": ["#2D5A27", "#8B4513", "#F5F5DC"],
  "asset_count": 0,
  "last_generation": null
}
EOF

    # Create full identity (L1)
    cat > "$BRANDS_DIR/$SAMPLE_BRAND/identity_full.json" << 'EOF'
{
  "slug": "summit-coffee",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z",
  "core": {
    "name": "Summit Coffee Co.",
    "tagline": "Reach your peak, one cup at a time",
    "mission": "To fuel life's adventures with exceptional, sustainably-sourced coffee",
    "values": ["Quality", "Sustainability", "Adventure", "Community"]
  },
  "visual": {
    "primary_colors": [
      {"name": "Forest Green", "hex": "#2D5A27", "usage": "Primary brand color, backgrounds"},
      {"name": "Coffee Brown", "hex": "#8B4513", "usage": "Accents, text"},
      {"name": "Cream", "hex": "#F5F5DC", "usage": "Backgrounds, contrast"}
    ],
    "secondary_colors": [
      {"name": "Mountain Blue", "hex": "#4A90A4", "usage": "Highlights"},
      {"name": "Sunrise Orange", "hex": "#E67E22", "usage": "CTAs, energy"}
    ],
    "typography": {
      "heading": "Montserrat Bold",
      "body": "Open Sans",
      "accent": "Playfair Display"
    },
    "imagery_style": "Outdoor adventure photography, mountain landscapes, cozy coffee moments",
    "logo_description": "Stylized mountain peak with coffee cup silhouette, minimalist line art"
  },
  "voice": {
    "tone": ["Warm", "Encouraging", "Adventurous", "Authentic"],
    "personality": "Like a trusted hiking buddy who always brings the best coffee",
    "dos": ["Use active, energizing language", "Reference outdoor adventures", "Speak authentically about sustainability"],
    "donts": ["Sound corporate or stiff", "Use generic coffee cliches", "Overpromise on caffeine effects"]
  },
  "audience": {
    "primary_demographic": "Active professionals aged 28-45 who value quality and sustainability",
    "psychographics": ["Outdoor enthusiasts", "Health-conscious", "Environmentally aware", "Quality over quantity"],
    "pain_points": ["Generic mass-market coffee", "Unsustainable practices", "Lack of adventure in daily routine"]
  },
  "positioning": {
    "market_category": "Premium Coffee",
    "unique_value": "The only coffee brand that combines peak-quality beans with a genuine outdoor adventure ethos",
    "competitors": ["Blue Bottle", "Stumptown", "Counter Culture"],
    "differentiation": "Not just about the coffee, but about the lifestyle and adventures it fuels"
  }
}
EOF

    # Create brand index
    cat > "$BRANDS_DIR/index.json" << 'EOF'
{
  "brands": [
    {
      "slug": "summit-coffee",
      "name": "Summit Coffee Co.",
      "category": "Premium Coffee",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z",
      "last_accessed": "2024-01-15T10:00:00Z"
    }
  ],
  "active_brand": "summit-coffee"
}
EOF

    # Create a sample document
    cat > "$BRANDS_DIR/$SAMPLE_BRAND/docs/brand-guidelines.md" << 'EOF'
# Summit Coffee Co. Brand Guidelines

## Our Story
Summit Coffee was founded by two avid mountain climbers who wanted to bring
the same dedication to quality they applied to their expeditions to their coffee.

## Visual Identity
- **Primary Color**: Forest Green (#2D5A27) - Represents our connection to nature
- **Secondary Color**: Coffee Brown (#8B4513) - The warmth of a perfect cup
- **Accent**: Sunrise Orange (#E67E22) - The energy to start your day

## Tone of Voice
We speak like your favorite hiking buddy - warm, encouraging, and always ready
for the next adventure. We're authentic about our sustainability efforts and
never use corporate jargon.

## Key Messages
1. Every cup fuels an adventure
2. Sustainably sourced from peak to cup
3. Quality you can taste, practices you can trust
EOF

    echo "Sample brand created at: $BRANDS_DIR/$SAMPLE_BRAND"
else
    echo "Sample brand already exists: $BRANDS_DIR/$SAMPLE_BRAND"
fi

echo ""
echo "=== Launching Brand Studio ==="
echo ""

# Check if running from venv
cd "$PROJECT_DIR"
if [ -f ".venv/bin/python" ]; then
    echo "Using project venv..."
    .venv/bin/python -m sip_videogen.studio
else
    echo "Using system Python..."
    python -m sip_videogen.studio
fi
