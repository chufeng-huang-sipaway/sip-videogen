# SIP VideoGen

AI-powered brand management and video generation platform.

**Current Version: v0.9.0**

## Overview

SIP VideoGen has two main components:

1. **Sip Studio** - macOS desktop app for creating and managing brand identities with AI assistance
2. **Video Generation API** - Programmatic video generation using AI agents

## Table of Contents

- [Sip Studio](#sip-studio)
- [Video Generation API](#video-generation-api)
- [Installation](#installation)
- [Configuration](#configuration)
- [Development](#development)
- [Project Structure](#project-structure)

---

## Sip Studio

A macOS desktop app for creating and managing brand identities with AI assistance.

### Features

- **Brand Strategy** - Mission, values, positioning, target audience, competitive analysis
- **Visual Identity** - Color palette, typography, imagery guidelines
- **Brand Voice** - Tone, messaging, communication style
- **Asset Library** - Organized storage for logos, marketing materials, documents
- **Product Management** - Product specifications and style references
- **AI Brand Advisor** - Chat interface with brand-aware AI assistant and specialized skills

### Installation

#### Option 1: Download DMG (Recommended)

1. Go to [GitHub Releases](https://github.com/chufeng-huang-sipaway/sip-videogen/releases)
2. Download `Brand-Studio-X.Y.Z.dmg`
3. Open the DMG and drag Sip Studio to Applications

#### Option 2: Terminal Install

```bash
curl -sSL https://raw.githubusercontent.com/chufeng-huang-sipaway/sip-videogen/main/scripts/install-sip-studio.sh | bash
```

### First-Time Setup

1. Launch Sip Studio from Applications
2. Enter your API keys when prompted:
   - **OpenAI API Key** - [Get one here](https://platform.openai.com/api-keys)
   - **Gemini API Key** - [Get one here](https://aistudio.google.com/apikey)
3. Create your first brand

### Usage

#### Creating a Brand

1. Click **New Brand** in the sidebar
2. Optionally upload reference materials (images, documents)
3. Describe your brand concept
4. The AI Brand Director team develops your complete identity

#### AI Brand Advisor

Chat with an AI that understands your brand's voice, values, and visual identity. The advisor uses specialized skills:

- **Brand Identity** - Develop and refine brand strategy
- **Logo Design** - Create logo concepts and variations
- **Mascot Generation** - Design brand mascots
- **Image Composition** - Generate brand-aligned imagery
- **Product Image Strategy** - Product photography direction
- **Video Prompts** - Video generation prompt engineering
- **Style References** - Analyze and apply visual styles
- **Brand Evolution** - Guide brand growth and changes

**Attachments**: Drag and drop files into the chat to reference assets or documents.

#### Asset Library

Organize your brand materials by category:

| Category | Purpose |
|----------|---------|
| `logo/` | Brand logos and variations |
| `packaging/` | Product packaging designs |
| `lifestyle/` | Lifestyle and mood imagery |
| `mascot/` | Brand mascot variations |
| `marketing/` | Marketing materials |
| `generated/` | AI-generated assets |
| `video/` | Video files |

### Data Storage

All brand data is stored locally at `~/.sip-studio/brands/`:

```
~/.sip-studio/brands/
├── index.json              # Brand registry
├── my-brand/
│   ├── identity.json       # Brand summary (fast loading)
│   ├── identity_full.json  # Complete identity
│   ├── products/           # Product specifications
│   ├── projects/           # Project data
│   ├── assets/
│   └── docs/
```

---

## Video Generation API

Transform ideas into complete videos using AI agents. The pipeline orchestrates script development, reference image generation, video clip creation, and final assembly.

### Pipeline Architecture

```
User Idea → Showrunner Agent Team → VideoScript
         → Reference Images (Gemini) → SharedElements
         → Video Clips (VEO/Kling/Sora) → Scenes
         → Music (Lyria, optional) → Background
         → FFmpeg Assembly → Final Video
```

### Basic Usage

```python
import asyncio
from sip_studio.generators.base import VideoProvider
from sip_studio.video import PipelineConfig, VideoPipeline

async def main():
    config = PipelineConfig(
        idea="A cat playing piano in a jazz club",
        num_scenes=3,
        provider=VideoProvider.VEO,
    )
    result = await VideoPipeline(config).run()
    print(f"Video: {result.final_video_path}")

asyncio.run(main())
```

### Dry Run Mode

Generate script only without video generation:

```python
config = PipelineConfig(
    idea="A sunset over mountains",
    num_scenes=3,
    dry_run=True,
)
result = await VideoPipeline(config).run()
print(result.script.title)
for scene in result.script.scenes:
    print(f"- {scene.setting}: {scene.action}")
```

### Video Providers

| Provider | Durations | Requirements |
|----------|-----------|--------------|
| **VEO** (Google) | 4, 6, 8 sec | `GEMINI_API_KEY`, `SIP_GCS_BUCKET_NAME` |
| **Kling AI** | 5, 10 sec | `KLING_ACCESS_KEY`, `KLING_SECRET_KEY` |
| **Sora** (OpenAI) | 5, 10, 15, 20 sec | `OPENAI_API_KEY` |

### Agent Architecture

The **Showrunner** orchestrates specialist agents:

- **Screenwriter** - Scene breakdown, dialogue, timing
- **Production Designer** - Identify shared visual elements
- **Continuity Supervisor** - Validate consistency, optimize prompts
- **Music Director** - Design background music briefs

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend development)
- ffmpeg (for video assembly)

### Install from Source

```bash
git clone https://github.com/chufeng-huang-sipaway/sip-videogen.git
cd sip-videogen
pip install -e ".[dev]"
```

### GCS Setup (required for VEO)

```bash
gcloud auth application-default login
gsutil mb -l us-central1 gs://YOUR_BUCKET_NAME
```

---

## Configuration

Settings are loaded from environment variables. Create `.env` file or set them in `~/.sip-studio/.env`:

### Required

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Agent orchestration + Sora provider |
| `GEMINI_API_KEY` | Image generation + VEO video |

### Optional

| Variable | Purpose | Default |
|----------|---------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP project (VEO, music) | - |
| `SIP_GCS_BUCKET_NAME` | VEO reference image storage | - |
| `KLING_ACCESS_KEY` | Kling video generation | - |
| `KLING_SECRET_KEY` | Kling video generation | - |
| `FIRECRAWL_API_KEY` | URL content fetching | - |
| `SIP_OUTPUT_DIR` | Local output directory | `./output` |
| `SIP_DEFAULT_SCENES` | Default scene count (1-10) | `3` |
| `SIP_VIDEO_DURATION` | Duration per scene (4/6/8 sec) | `6` |
| `SIP_LOG_LEVEL` | DEBUG/INFO/WARNING/ERROR | `INFO` |
| `SIP_ENABLE_BACKGROUND_MUSIC` | Enable Lyria music | `true` |
| `SIP_MUSIC_VOLUME` | Music volume (0.0-1.0) | `0.4` |

---

## Development

### Running Sip Studio

```bash
# Production mode
python -m sip_studio.studio

# Development mode (with hot reload)
STUDIO_DEV=1 python -m sip_studio.studio
```

### Frontend Development

```bash
cd src/sip_studio/studio/frontend
npm install
npm run dev      # Dev server on localhost:5173
npm run build    # Production build
npm run test     # Run tests
```

### Testing & Linting

```bash
python -m pytest               # Run all tests
python -m pytest -k "test_name" # Run specific test
ruff check .                   # Lint
ruff format .                  # Format
mypy src/                      # Type check
```

### Building a Release

```bash
./scripts/build-release.sh 0.9.0    # Build DMG
gh release create v0.9.0 dist/Brand-Studio-0.9.0.dmg \
  --title "Sip Studio v0.9.0" \
  --notes "Release notes here"
```

---

## Project Structure

```
sip-videogen/
├── src/sip_studio/
│   ├── video/              # Video generation pipeline
│   ├── generators/         # Provider implementations (VEO, Kling, Sora)
│   ├── agents/             # AI agents (Showrunner, Screenwriter, etc.)
│   ├── advisor/            # Brand Advisor agent + skills
│   │   ├── agent.py        # Main advisor with skills architecture
│   │   ├── skills/         # Specialized skills (logo, mascot, etc.)
│   │   └── tools/          # Advisor tools
│   ├── brands/             # Brand management system
│   │   ├── context.py      # Context builder for AI agents
│   │   ├── memory.py       # Brand memory/storage layer
│   │   ├── models/         # Brand data structures
│   │   └── storage/        # Persistent brand storage
│   ├── studio/             # Desktop app
│   │   ├── frontend/       # React + TypeScript + Vite
│   │   ├── services/       # Service layer
│   │   ├── app.py          # PyWebView entry point
│   │   ├── bridge.py       # Python ↔ JS bridge
│   │   └── state.py        # Application state
│   ├── assembler/          # FFmpeg integration
│   ├── models/             # Pydantic data models
│   └── config/             # Settings and configuration
├── tests/                  # Test suite
├── scripts/                # Build and release scripts
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

---

## License

MIT License - see LICENSE file for details.
