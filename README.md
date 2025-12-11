# sip-videogen

CLI tool that transforms vague video ideas into complete videos using an AI agent team.

## How It Works

```
User Idea → AI Agent Script Team → Reference Images → Video Clips → Final Video
```

1. You provide a video idea (e.g., "A cat astronaut explores Mars")
2. AI agents collaborate to write a script with scenes and shared visual elements
3. Reference images are generated for visual consistency (characters, props, environments)
4. Video clips are generated for each scene using Google VEO 3.1 (8 seconds per clip)
5. Clips are assembled into a final video with background music via FFmpeg

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
# Install pipx if you don't have it
pip install pipx

# Install sip-videogen
pipx install sip-videogen

# Run - first time will prompt for configuration
sipvid
```

On first run, you'll be prompted to paste your configuration. Just paste the entire config block and press Enter twice.

### Option 2: Run from Source

```bash
# Clone the repo
git clone https://github.com/chufeng-huang-sipaway/sip-videogen.git
cd sip-videogen

# Copy and fill in your API keys
cp .env.example .env

# Run (installs everything automatically on first run)
./start.sh
```

## Prerequisites

- Python 3.11+ (`brew install python@3.11` on macOS)
- FFmpeg (`brew install ffmpeg` on macOS)

### API Keys Required

Get these API keys:

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

## Configuration

### First-Time Setup

On first run, `sipvid` will prompt you to configure your environment. You can either:

1. **Paste a config block** (recommended) - Paste all your keys at once:
   ```
   OPENAI_API_KEY=sk-...
   GEMINI_API_KEY=AIza...
   GOOGLE_CLOUD_PROJECT=my-project
   SIP_GCS_BUCKET_NAME=my-bucket
   ```

2. **Enter keys individually** - Follow the interactive prompts

Configuration is stored in `~/.sip-videogen/.env` and works from any directory.

### Managing Configuration

```bash
sipvid config          # Interactive config editor
sipvid config --show   # Show current configuration status
sipvid config --reset  # Replace config with a new config block
```

## Usage

### Interactive Menu

```bash
sipvid
```

This launches a simplified interactive menu:

```
? Use arrow keys to navigate, Enter to select:
❯ Generate Video     Create a new video from your idea
  View History       See previous generations
  More Options...    Settings, resume, and other tools
  Exit
```

### Director's Pitch Workflow

When you select "Generate Video", you'll experience a streamlined creative workflow:

1. **Enter your idea** - Describe your video concept
2. **Select duration** - Choose from 15s, 30s, 45s, or 60s
3. **Review the pitch** - The AI presents a "Director's Pitch" with:
   - Title and logline
   - Tone and visual style
   - Key elements and scene breakdown
4. **Approve or refine** - Accept the pitch, provide feedback for revision, or cancel
5. **Generate** - Once approved, full video generation begins

The AI agent team decides the optimal scene count based on your story's complexity.

### View History

Access all your previous video generations from the main menu:
- See title, date, duration, and completion status
- Resume or regenerate from any previous script
- Open output folders directly

### Direct Commands

```bash
# Generate a video (uses interactive pitch flow)
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

## Automatic Updates

The tool automatically checks for updates on each run. When a new version is available, you'll see a notification:

```
┌─────────────────────────────────────────────────┐
│  Update available!                              │
│  Current version: 0.1.0                         │
│  Latest version:  0.2.0                         │
│  Run: sipvid update                             │
└─────────────────────────────────────────────────┘
```

Update commands:

```bash
sipvid update         # Check and install updates
sipvid update --check # Only check, don't install
```

## Architecture

The tool uses a hub-and-spoke agent pattern:

- **Showrunner** (orchestrator) - Coordinates the script development process
  - **Screenwriter** - Creates scene breakdown with professional cinematography
  - **Production Designer** - Identifies shared visual elements for consistency
  - **Continuity Supervisor** - Validates consistency and optimizes prompts
  - **Music Director** - Designs complementary background music

### VEO 3.1 Prompt Optimization

Prompts are structured following [Google's VEO 3.1 best practices](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1):

- **Prompt order**: `[Cinematography] → [Subject+Action] → [Setting] → [Style] → [Audio]`
- **Professional camera terminology**: dolly, tracking, crane shots with depth of field control
- **Dialogue integration**: Quotes and speaker attribution for natural delivery
- **Audio design**: `Ambient:` and `SFX:` prefixes for precise sound control

### Clip Duration & Timestamp Prompting

When using reference images for visual consistency (standard workflow), VEO generates **8-second clips**. To create rhythm and shot variety within this fixed duration, scenes can use **timestamp prompting**:

```
[00:00-00:02] Wide establishing shot of the food truck
[00:02-00:04] Medium shot, the vendor prepares ingredients
[00:04-00:06] Close-up of sizzling grill
[00:06-00:08] Medium shot, vendor plates the food
```

This creates dynamic multi-shot sequences within a single clip, similar to professional editing.

### Seamless Scene Flow

Video clips are generated in parallel for speed, but the system ensures smooth transitions:

- **Flow Context**: Each clip receives position-aware instructions (first/middle/last) to avoid awkward pauses
- **Scene Continuity**: Screenwriter creates scenes that flow seamlessly:
  - First scene: May open naturally, must end with action in progress
  - Middle scenes: Must begin AND end mid-action (no pauses)
  - Last scene: Must begin mid-action, may conclude naturally

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

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

### Publishing New Versions

```bash
# 1. Bump version in pyproject.toml
# 2. Run publish script
./scripts/publish.sh
```

## Cost Estimation

Before generating videos, the tool displays estimated costs:
- Gemini image generation: ~$0.13-0.24 per image
- VEO video generation: Check current Vertex AI pricing

Use `--yes` to skip the cost confirmation prompt.
