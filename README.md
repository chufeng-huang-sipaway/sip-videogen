# Brand Studio

A macOS desktop app for creating and managing brand identities with AI assistance.

## What It Does

Brand Studio helps you develop complete brand identities through conversation with an AI Brand Advisor. Upload reference materials, describe your vision, and the AI creates:

- **Brand Strategy** - Mission, values, positioning, target audience
- **Visual Identity** - Color palette, typography, imagery guidelines
- **Brand Voice** - Tone, messaging, communication style
- **Asset Library** - Organized storage for logos, marketing materials, documents

## Installation

### Option 1: Download DMG (Recommended)

1. Go to [GitHub Releases](https://github.com/chufeng-huang-sipaway/sip-videogen/releases)
2. Download `Brand-Studio-X.Y.Z.dmg`
3. Open the DMG and drag Brand Studio to Applications

### Option 2: Terminal Install

```bash
curl -sSL https://raw.githubusercontent.com/chufeng-huang-sipaway/sip-videogen/main/scripts/install-brand-studio.sh | bash
```

## First-Time Setup

1. Launch Brand Studio from Applications
2. Enter your API keys when prompted:
   - **OpenAI API Key** - [Get one here](https://platform.openai.com/api-keys)
   - **Gemini API Key** - [Get one here](https://aistudio.google.com/apikey)
3. Create your first brand

## Usage

### Creating a Brand

1. Click **New Brand** in the sidebar
2. Optionally upload reference materials:
   - Images (logos, packaging, mood boards)
   - Documents (brand guidelines, briefs)
3. Describe your brand concept
4. The AI Brand Director team develops your complete identity

### Managing Brands

- **Switch brands** - Use the dropdown in the sidebar
- **View brand info** - See name, tagline, and category
- **Delete brands** - Click the trash icon (with confirmation)

### AI Brand Advisor

Chat with an AI that understands your brand's voice, values, and visual identity:

- Ask for copy suggestions in your brand voice
- Request asset generation (uses Gemini)
- Get feedback on brand consistency
- Refine your brand identity over time

**Attachments**: Drag and drop files into the chat, or click the attachment button to reference assets or documents.

### Asset Library

Organize your brand materials by category:
- `logo/` - Brand logos and variations
- `packaging/` - Product packaging designs
- `lifestyle/` - Lifestyle and mood imagery
- `mascot/` - Brand mascot variations
- `marketing/` - Marketing materials
- `generated/` - AI-generated assets

Upload, rename, or delete assets directly in the sidebar.

### Documents

Store brand-related documents:
- Brand guidelines (`.md`, `.txt`)
- Strategy briefs (`.json`, `.yaml`)
- Reference materials

## Auto-Updates

Brand Studio checks for updates on launch. When a new version is available, click **Update Now** to download and install automatically.

## Data Storage

All brand data is stored locally at `~/.sip-videogen/brands/`:

```
~/.sip-videogen/brands/
├── index.json           # Brand registry
├── my-brand/
│   ├── identity.json    # Brand summary
│   ├── identity_full.json
│   ├── assets/
│   └── docs/
```

---

## Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm

### Running from Source

```bash
# Clone and setup
git clone https://github.com/chufeng-huang-sipaway/sip-videogen.git
cd sip-videogen
pip install -e ".[dev]"

# Build frontend
cd src/sip_videogen/studio/frontend
npm install
npm run build
cd ../../../..

# Run
python -m sip_videogen.studio
```

### Development Mode

Use Vite dev server for hot reloading:

```bash
# Terminal 1: Frontend dev server
cd src/sip_videogen/studio/frontend
npm run dev

# Terminal 2: App with dev mode
STUDIO_DEV=1 python -m sip_videogen.studio
```

Or use the launcher script:

```bash
./scripts/studio-demo.sh
```

### Testing & Linting

```bash
python -m pytest           # Run tests
ruff check .               # Lint
ruff format .              # Format
mypy src/                  # Type check
```

### Building a Release

```bash
# Build DMG
./scripts/build-release.sh 0.3.0

# Publish to GitHub
gh release create v0.3.0 dist/Brand-Studio-0.3.0.dmg \
  --title "Brand Studio v0.3.0" \
  --notes "Release notes here"
```

---

## Legacy: Video Generation CLI

The repository also includes a CLI tool for AI-powered video generation. This feature is maintained but not actively developed.

### Quick Start

```bash
# Install
pipx install sip-videogen

# Run
sipvid
```

### Features

- AI script writing with visual consistency
- Video generation via VEO 3.1, Kling, or Sora
- Reference image generation for character/prop consistency
- FFmpeg assembly with background music

### Configuration

Required API keys for video generation:

| Key | Purpose |
|-----|---------|
| `OPENAI_API_KEY` | Script generation |
| `GEMINI_API_KEY` | Image & video generation |
| `GOOGLE_CLOUD_PROJECT` | GCS storage (optional) |
| `SIP_GCS_BUCKET_NAME` | Video storage (optional) |

See `sipvid status` for configuration details.
