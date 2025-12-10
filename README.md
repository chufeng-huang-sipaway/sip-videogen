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

## Prerequisites

- Python 3.11+
- FFmpeg installed (`brew install ffmpeg` on macOS)
- OpenAI API key
- Google Gemini API key
- Google Cloud project with Vertex AI enabled
- GCS bucket for video storage

## Installation

```bash
# Clone and install
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Setup

1. **Set up Google Cloud**:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT
   gcloud services enable aiplatform.googleapis.com storage.googleapis.com
   gsutil mb -l us-central1 gs://YOUR_BUCKET_NAME
   ```

2. **Create `.env` file** (copy from `.env.example`):
   ```bash
   OPENAI_API_KEY=sk-...
   GEMINI_API_KEY=...
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   SIP_GCS_BUCKET_NAME=your-bucket-name
   GOOGLE_GENAI_USE_VERTEXAI=True
   SIP_OUTPUT_DIR=./output
   ```

3. **Verify setup**:
   ```bash
   ./start.sh status
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
