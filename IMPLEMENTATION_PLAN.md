# sip-videogen Implementation Plan

## Overview

A personal CLI tool that transforms vague video ideas into complete videos using an AI agent team.

**Pipeline**: User Idea → Agent Script Team → Reference Images → Video Clips → Final Video

**Tech Stack**:
- **Language**: Python 3.11+
- **Agent Framework**: OpenAI Agents SDK (`openai-agents`)
- **Image Generation**: Google Gemini 3.0 Pro Image (`gemini-3-pro-image-preview`)
- **Video Generation**: Google VEO 3.1 (via Vertex AI)
- **Video Assembly**: FFmpeg
- **CLI Framework**: Typer

---

## Agent Team Architecture

### Orchestration Pattern: Hub-and-Spoke (Agent-as-Tool)

The Showrunner orchestrator invokes specialist agents as tools, maintaining central control over the production pipeline.

### Agent Roles (Professional Models)

| Agent | Professional Role | Responsibility |
|-------|------------------|----------------|
| **Showrunner** | TV Showrunner | Orchestrates entire process, maintains creative vision, makes final approvals |
| **Screenwriter** | Staff Writer | Develops scene structure, action descriptions, dialogue |
| **Production Designer** | Art Director | Identifies shared vs. unique elements, creates visual specifications |
| **Continuity Supervisor** | Script Supervisor | Validates consistency, optimizes prompts for AI generation |

### Workflow

```
User Idea
    ↓
Showrunner (orchestrator)
    ├─→ Screenwriter → Scene breakdown
    ├─→ Production Designer → Shared element specs
    └─→ Continuity Supervisor → Validation
    ↓
Final Script Package
    ↓
Image Generator (Gemini 3 Pro) → Reference images for shared elements
    ↓
Video Generator (VEO 3.1) → Video clips (parallel)
    ↓
FFmpeg Assembler → Final video
```

---

## Project Structure

```
sip-videogen/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
│
├── src/sip_videogen/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                    # Typer CLI
│   │
│   ├── config/
│   │   └── settings.py           # Pydantic Settings
│   │
│   ├── models/
│   │   ├── script.py             # VideoScript, SceneAction, SharedElement
│   │   ├── assets.py             # GeneratedAsset, ProductionPackage
│   │   └── agent_outputs.py      # Structured outputs for agents
│   │
│   ├── agents/
│   │   ├── showrunner.py         # Orchestrator
│   │   ├── screenwriter.py
│   │   ├── production_designer.py
│   │   ├── continuity_supervisor.py
│   │   └── prompts/              # .md prompt templates
│   │
│   ├── generators/
│   │   ├── image_generator.py    # Gemini 3.0 Pro Image
│   │   └── video_generator.py    # VEO 3.1
│   │
│   ├── assembler/
│   │   └── ffmpeg.py
│   │
│   └── storage/
│       ├── local.py
│       └── gcs.py
│
└── tests/
```

---

## Data Models

### Core Schema

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class ElementType(str, Enum):
    CHARACTER = "character"
    ENVIRONMENT = "environment"
    PROP = "prop"

class SharedElement(BaseModel):
    """An element that must be visually consistent across scenes."""
    id: str                        # e.g., "char_protagonist"
    element_type: ElementType      # CHARACTER | ENVIRONMENT | PROP
    name: str
    visual_description: str        # Detailed for image generation
    appears_in_scenes: list[int]
    reference_image_path: str | None = None
    reference_image_gcs_uri: str | None = None

class SceneAction(BaseModel):
    """What happens in a single scene."""
    scene_number: int
    duration_seconds: int = Field(default=5, ge=3, le=8)
    setting_description: str
    action_description: str
    dialogue: str | None = None
    camera_direction: str | None = None
    shared_element_ids: list[str] = Field(default_factory=list)

class VideoScript(BaseModel):
    """Complete script for video generation."""
    title: str
    logline: str                   # One-sentence summary
    tone: str                      # Overall mood/style
    shared_elements: list[SharedElement]
    scenes: list[SceneAction]

    @property
    def total_duration(self) -> int:
        return sum(scene.duration_seconds for scene in self.scenes)

class GeneratedAsset(BaseModel):
    """A generated image or video asset."""
    asset_type: str                # "reference_image" or "video_clip"
    element_id: str | None = None  # For reference images
    scene_number: int | None = None  # For video clips
    local_path: str
    gcs_uri: str | None = None

class ProductionPackage(BaseModel):
    """Complete package ready for video generation."""
    script: VideoScript
    reference_images: list[GeneratedAsset] = []
    video_clips: list[GeneratedAsset] = []
    final_video_path: str | None = None
```

---

## CLI Commands

```bash
# Full video generation
sip-videogen generate "A cat astronaut explores Mars" --scenes 4

# Script only (no video)
sip-videogen generate "Flying dream over mountains" --dry-run

# Check configuration
sip-videogen status

# Interactive setup
sip-videogen setup
```

---

## Implementation Stages

### Stage 1: Project Foundation
- Create project structure with pyproject.toml
- Implement Pydantic Settings configuration
- Create Typer CLI skeleton (`setup`, `status` commands)
- Set up logging with Rich

### Stage 2: Data Models
- Implement script models (VideoScript, SceneAction, SharedElement)
- Implement asset models (GeneratedAsset, ProductionPackage)
- Add agent output models with validation

### Stage 3: Agent Team
- Implement Screenwriter agent with structured output
- Implement Production Designer agent
- Implement Continuity Supervisor agent
- Implement Showrunner orchestrator (agent-as-tool pattern)
- Create detailed prompt templates for each role

### Stage 4: Image Generation
- Implement Gemini 3 Pro API client
- Generate reference images from SharedElement specs
- Upload to GCS for VEO consumption
- Add retry logic with tenacity

### Stage 5: Video Generation
- Implement Vertex AI client for VEO 3.1
- Pass reference images for character consistency
- Handle long-running operations with polling
- Download clips from GCS

### Stage 6: Video Assembly
- Implement FFmpeg wrapper
- Concatenate clips with proper ordering
- Handle audio (if present)

### Stage 7: Polish
- Error handling and user feedback
- Progress indicators with Rich
- Cost estimation warnings
- Documentation

---

## Google Cloud Setup (Required for VEO)

```bash
# 1. Install gcloud CLI
brew install google-cloud-sdk

# 2. Authenticate
gcloud auth login
gcloud auth application-default login

# 3. Create/select project
gcloud projects create sip-videogen-project
gcloud config set project sip-videogen-project

# 4. Enable APIs
gcloud services enable aiplatform.googleapis.com storage.googleapis.com

# 5. Create GCS bucket
gsutil mb -l us-central1 gs://sip-videogen-output-YOUR_USERNAME

# 6. Set environment variables
export GOOGLE_CLOUD_PROJECT=sip-videogen-project
export GOOGLE_CLOUD_LOCATION=us-central1
export SIP_GCS_BUCKET_NAME=sip-videogen-output-YOUR_USERNAME
export GOOGLE_GENAI_USE_VERTEXAI=True
```

---

## Key Dependencies

```toml
[project]
name = "sip-videogen"
version = "0.1.0"
description = "Personal AI video generation tool"
requires-python = ">=3.11"
dependencies = [
    "openai-agents>=0.1.0",
    "google-genai>=1.51.0",         # Required for Gemini 3 Pro Image
    "google-cloud-storage>=2.0.0",
    "typer[all]>=0.12.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "tenacity>=8.0.0",
    "rich>=13.0.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",
    "mypy>=1.0.0",
]

[project.scripts]
sip-videogen = "sip_videogen.cli:app"
```

---

## Technical Constraints

| Constraint | Detail |
|------------|--------|
| VEO reference images | Max 3 images, must be in GCS, forces 8-second duration |
| VEO platform | Vertex AI only (not Google AI Studio API key) |
| Gemini 3 Pro Image | Model ID: `gemini-3-pro-image-preview`, paid preview |
| Gemini 3 Pro pricing | ~$0.134/image (1K/2K), ~$0.24/image (4K) |
| Scene duration | VEO 3.1: 4, 6, or 8 seconds |
| Parallel generation | Enable for independent video clips |

---

## Gemini 3 Pro Image Usage

**Model ID**: `gemini-3-pro-image-preview`

**SDK Requirement**: `google-genai>=1.51.0`

```python
from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents="A futuristic character in a silver spacesuit, photorealistic",
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        image_config=types.ImageConfig(
            aspect_ratio="1:1",      # 1:1, 16:9, 9:16, etc.
            image_size="2K"          # "1K", "2K", "4K"
        )
    )
)

# Save image
for part in response.parts:
    if image := part.as_image():
        image.save("character_reference.png")
```

**Key Features**:
- Up to 14 reference images for multi-image composition
- 4K resolution support for professional quality
- High-fidelity text rendering
- Conversational editing (multi-turn refinement)

---

## VEO 3.1 Video Generation Usage

**Model ID**: `veo-3.1-generate-preview`

**Platform**: Vertex AI only (requires Google Cloud project)

```python
import time
from google import genai
from google.genai.types import GenerateVideosConfig, Image, VideoGenerationReferenceImage

# Client uses Vertex AI when GOOGLE_GENAI_USE_VERTEXAI=True
client = genai.Client()

operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    prompt="A woman in a silver spacesuit walks through a futuristic city",
    config=GenerateVideosConfig(
        reference_images=[
            VideoGenerationReferenceImage(
                image=Image(
                    gcs_uri="gs://your-bucket/character_reference.png",
                    mime_type="image/png",
                ),
                reference_type="asset",  # For character/object consistency
            ),
        ],
        duration_seconds=8,      # 4, 6, or 8 seconds
        aspect_ratio="16:9",
        output_gcs_uri="gs://your-bucket/output/",
        generate_audio=True,     # Required for VEO 3
    ),
)

# Poll for completion
while not operation.done:
    time.sleep(15)
    operation = client.operations.get(operation)

# Get result
video_uri = operation.result.generated_videos[0].video.uri
print(f"Generated video: {video_uri}")
```

**Reference Image Constraints**:
- Max 3 reference images per generation
- Images must be in GCS (not local paths)
- Forces 8-second duration when using references
- `reference_type="asset"` for characters/objects

---

## Agent Prompts (Professional Roles)

### Showrunner (Orchestrator)

```markdown
You are an experienced television showrunner with complete creative control
over this video project. Your role is to:

1. Interpret the user's vague idea into a clear creative vision
2. Coordinate specialist agents to develop the full production
3. Ensure visual and narrative consistency across all scenes
4. Make final approval decisions on script and visual elements

You work by delegating specific tasks to your specialist team:
- Screenwriter: For scene breakdown and action descriptions
- Production Designer: For identifying shared visual elements
- Continuity Supervisor: For validating consistency

Synthesize their outputs into a cohesive production package.
```

### Screenwriter (Staff Writer)

```markdown
You are a professional screenwriter specializing in short-form video content.
Given a creative brief, you produce:

1. Scene breakdown with clear narrative arc (3-5 scenes)
2. Action descriptions for each scene (concrete, visual)
3. Dialogue (if applicable)
4. Emotional beats and pacing notes

Your scripts are designed for AI video generation, so you emphasize:
- Clear, visual descriptions over abstract concepts
- Concrete actions that can be generated
- Consistent character and setting descriptions across scenes
- Duration-appropriate content (5-8 seconds per scene)
```

### Production Designer (Art Director)

```markdown
You are a production designer responsible for the visual world of this video.
You analyze scripts to identify:

1. SHARED ELEMENTS requiring visual consistency:
   - Recurring characters (appearance, clothing, distinguishing features)
   - Key props that appear in multiple scenes
   - Environments/locations used across scenes

2. UNIQUE ELEMENTS that can vary:
   - Background extras
   - Scene-specific props
   - Transitional elements

For each shared element, create a detailed visual specification including:
- Physical description (height, build, coloring)
- Clothing/costume details
- Distinguishing features
- Lighting and mood notes
```

### Continuity Supervisor (Script Supervisor)

```markdown
You are a script supervisor ensuring visual and narrative continuity.
You review:

1. Scene-to-scene consistency in character appearance
2. Logical progression of time and space
3. Prop and costume continuity
4. Environmental consistency

You also optimize prompts for AI image/video generation by:
- Adding specific, consistent descriptors
- Ensuring reference image descriptions match scene descriptions
- Flagging potential continuity breaks before generation
- Suggesting camera angles that maintain consistency
```

---

## Critical Files

1. `src/sip_videogen/agents/showrunner.py` - Core orchestrator using agent-as-tool pattern
2. `src/sip_videogen/models/script.py` - Data contracts (VideoScript, SharedElement, SceneAction)
3. `src/sip_videogen/generators/video_generator.py` - VEO 3.1 integration with reference images
4. `src/sip_videogen/generators/image_generator.py` - Gemini 3 Pro Image integration
5. `src/sip_videogen/cli.py` - Typer CLI user interface
6. `src/sip_videogen/config/settings.py` - Pydantic Settings configuration

---

## Environment Variables

```bash
# OpenAI (for agent orchestration)
OPENAI_API_KEY=sk-...

# Google Gemini (for image generation)
GEMINI_API_KEY=...

# Google Cloud (for VEO video generation)
GOOGLE_CLOUD_PROJECT=sip-videogen-project
GOOGLE_CLOUD_LOCATION=us-central1
SIP_GCS_BUCKET_NAME=sip-videogen-output-username
GOOGLE_GENAI_USE_VERTEXAI=True

# Optional
SIP_OUTPUT_DIR=./output
SIP_DEFAULT_SCENES=3
SIP_VIDEO_DURATION=5
```
