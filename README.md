# sip-videogen

CLI tool that transforms vague video ideas into complete videos using an AI agent team.

## How It Works

```
User Idea → AI Agent Script Team → Reference Images → Video Clips → Final Video
```

1. You provide a video idea (e.g., "A cat astronaut explores Mars")
2. AI agents collaborate to write a script with scenes and shared visual elements
3. Reference images are generated for visual consistency (characters, props, environments)
4. Video clips are generated for each scene using Google VEO 3.1
5. Clips are assembled into a final video with FFmpeg

## Quick Start

```bash
# 1. Copy and fill in your API keys
cp .env.example .env

# 2. Run (installs everything automatically on first run)
./start.sh
```

That's it! The script handles Python environment setup and dependency installation.

## Prerequisites

- Python 3.11+ (`brew install python@3.11` on macOS)
- FFmpeg (`brew install ffmpeg` on macOS)

### API Keys Required

Get these and add them to your `.env` file:

| Key | Where to get it |
|-----|-----------------|
| `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com/api-keys) |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) |
| `GOOGLE_CLOUD_PROJECT` | [Google Cloud Console](https://console.cloud.google.com) |
| `SIP_GCS_BUCKET_NAME` | Create via `gsutil mb -l us-central1 gs://your-bucket` |

### Google Cloud Setup (one-time)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT
gcloud services enable aiplatform.googleapis.com storage.googleapis.com
gsutil mb -l us-central1 gs://YOUR_BUCKET_NAME
```

## Usage

### Interactive Menu
```bash
sipvid
```

This launches an interactive menu with arrow-key navigation. Use ↑/↓ to navigate and Enter to select.

### Direct Commands
```bash
# Generate a video
sipvid generate "A cat astronaut explores Mars"

# Regenerate videos from an existing run (reuse saved script + images)
sipvid resume output/sip_20251210_123855_e9a845e4

# Generate with specific number of scenes
sipvid generate "Epic space battle" --scenes 5

# Dry run (script only, no video generation)
sipvid generate "Underwater adventure" --dry-run

# Skip cost confirmation
sipvid generate "Robot dance party" --yes

# Check configuration status
sipvid status
```

## Architecture

The tool uses a hub-and-spoke agent pattern:

- **Showrunner** (orchestrator) - Coordinates the script development process
  - **Screenwriter** - Creates scene breakdown with narrative arc
  - **Production Designer** - Identifies shared visual elements
  - **Continuity Supervisor** - Validates consistency and optimizes prompts

### Seamless Scene Flow

Video clips are generated in parallel for speed, but the system ensures smooth transitions between clips:

- **VEO Prompt Context**: Each clip receives position-aware instructions (first/middle/last scene) to avoid awkward pauses at clip boundaries
- **Agent Guidelines**: Screenwriter and Continuity Supervisor are instructed to create scenes that flow seamlessly:
  - First scene: May open naturally, must end with action in progress
  - Middle scenes: Must begin AND end mid-action (no pauses at either end)
  - Last scene: Must begin mid-action, may conclude naturally

This prevents the "breathing space" effect where assembled clips have noticeable gaps between scenes.

## Development

```bash
# Run tests
python -m pytest

# Run specific test
python -m pytest tests/test_models.py -v

# Lint and format
ruff check .
ruff format .

# Type check
mypy src/
```

## Cost Estimation

Before generating videos, the tool displays estimated costs:
- Gemini image generation: ~$0.13-0.24 per image
- VEO video generation: Check current Vertex AI pricing

Use `--yes` to skip the cost confirmation prompt.
