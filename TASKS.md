# sip-videogen Development Tasks

## Project Overview

**sip-videogen** is a CLI tool that transforms vague video ideas into complete videos using an AI agent team. The pipeline is:

```
User Idea → AI Agent Script Team → Reference Images → Video Clips → Final Video
```

### Tech Stack
- **Python 3.11+** - Core language
- **OpenAI Agents SDK** (`openai-agents`) - Agent orchestration framework
- **Google Gemini** (`google-genai`) - Image generation (model: `gemini-2.5-flash-image` or `gemini-3-pro-image-preview`)
- **Google VEO 3.1** (via Vertex AI) - Video generation (model: `veo-3.1-generate-preview`)
- **FFmpeg** - Video assembly
- **Typer** - CLI framework
- **Pydantic** - Data models and settings

### Architecture: Hub-and-Spoke Agent Pattern

The **Showrunner** agent orchestrates specialist agents as tools:

```
User Idea
    ↓
Showrunner (orchestrator)
    ├── calls Screenwriter → Scene breakdown
    ├── calls Production Designer → Visual element specs
    └── calls Continuity Supervisor → Consistency validation
    ↓
Final Script Package (VideoScript with SharedElements)
    ↓
Image Generator → Reference images for shared elements (uploaded to GCS)
    ↓
Video Generator → Video clips (parallel, uses reference images)
    ↓
FFmpeg → Final concatenated video
```

### Key Data Flow
1. User provides a vague idea: "A cat astronaut explores Mars"
2. Agent team produces a `VideoScript` with `SharedElement`s (characters, props, environments)
3. Reference images are generated for each `SharedElement` using Gemini
4. Each scene becomes a video clip using VEO 3.1 (with reference images for consistency)
5. FFmpeg concatenates clips into final video

---

## Task List

### Stage 1: Project Foundation

#### Task 1.1: Initialize Project Structure
**Description**: Create the base project with proper Python packaging.

**Deliverables**:
- `pyproject.toml` with all dependencies listed
- Directory structure: `src/sip_videogen/` with subfolders (agents, generators, models, config, assembler, storage)
- `__init__.py` files in all packages
- `__main__.py` for `python -m sip_videogen` execution
- `.env.example` with all required environment variables
- `.gitignore` for Python projects

**Dependencies to include**:
```toml
dependencies = [
    "openai-agents>=0.1.0",
    "google-genai>=1.51.0",
    "google-cloud-storage>=2.0.0",
    "typer[all]>=0.12.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "tenacity>=8.0.0",
    "rich>=13.0.0",
    "httpx>=0.27.0",
]
```

**Entry point**: `sip-videogen = "sip_videogen.cli:app"`

---

#### Task 1.2: Implement Configuration with Pydantic Settings
**Description**: Create a settings module that loads configuration from environment variables.

**File**: `src/sip_videogen/config/settings.py`

**Required settings**:
- `OPENAI_API_KEY` - For agent orchestration
- `GEMINI_API_KEY` - For Gemini image generation
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `GOOGLE_CLOUD_LOCATION` - Region (default: `us-central1`)
- `SIP_GCS_BUCKET_NAME` - GCS bucket for VEO
- `SIP_OUTPUT_DIR` - Local output directory (default: `./output`)
- `SIP_DEFAULT_SCENES` - Default scene count (default: 3)
- `SIP_VIDEO_DURATION` - Default duration per scene (default: 5)

**Implementation hints**:
- Use `pydantic-settings` with `BaseSettings`
- Load from `.env` file using `SettingsConfigDict(env_file=".env")`
- Create a singleton getter function: `get_settings() -> Settings`

**Reference**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

---

#### Task 1.3: Create CLI Skeleton with Typer
**Description**: Implement the basic CLI structure with placeholder commands.

**File**: `src/sip_videogen/cli.py`

**Commands to implement**:
1. `sip-videogen generate <idea> [--scenes N] [--dry-run]` - Main command (placeholder for now)
2. `sip-videogen status` - Show configuration status (API keys set, GCS bucket exists, etc.)
3. `sip-videogen setup` - Interactive setup helper (optional, can be placeholder)

**Implementation hints**:
- Use `typer.Typer()` with `rich_markup_mode="rich"`
- Use `rich.console.Console` for pretty output
- The `status` command should validate that all required env vars are set

**Reference**: https://typer.tiangolo.com/

---

#### Task 1.4: Set Up Logging with Rich
**Description**: Configure structured logging that works well in CLI.

**Implementation hints**:
- Use `rich.logging.RichHandler` for pretty console output
- Configure logging level from environment variable `SIP_LOG_LEVEL` (default: INFO)
- Log to both console and optionally a file

---

### Stage 2: Data Models

#### Task 2.1: Implement Core Script Models
**Description**: Create the Pydantic models that represent the video script structure.

**File**: `src/sip_videogen/models/script.py`

**Models to implement**:

```python
class ElementType(str, Enum):
    CHARACTER = "character"
    ENVIRONMENT = "environment"
    PROP = "prop"

class SharedElement(BaseModel):
    """An element that must be visually consistent across scenes."""
    id: str                           # e.g., "char_protagonist"
    element_type: ElementType
    name: str
    visual_description: str           # Detailed description for image generation
    appears_in_scenes: list[int]
    reference_image_path: str | None = None
    reference_image_gcs_uri: str | None = None

class SceneAction(BaseModel):
    """What happens in a single scene."""
    scene_number: int
    duration_seconds: int = Field(default=5, ge=4, le=8)  # VEO supports 4, 6, 8
    setting_description: str
    action_description: str
    dialogue: str | None = None
    camera_direction: str | None = None
    shared_element_ids: list[str] = Field(default_factory=list)

class VideoScript(BaseModel):
    """Complete script for video generation."""
    title: str
    logline: str                      # One-sentence summary
    tone: str                         # Overall mood/style
    shared_elements: list[SharedElement]
    scenes: list[SceneAction]

    @property
    def total_duration(self) -> int:
        return sum(scene.duration_seconds for scene in self.scenes)

    def get_element_by_id(self, element_id: str) -> SharedElement | None:
        """Helper to find a shared element by ID."""
        ...
```

**Notes**:
- VEO 3.1 only supports 4, 6, or 8 second durations
- When using reference images, VEO forces 8-second duration

---

#### Task 2.2: Implement Asset and Production Models
**Description**: Create models for tracking generated assets.

**File**: `src/sip_videogen/models/assets.py`

**Models to implement**:

```python
class AssetType(str, Enum):
    REFERENCE_IMAGE = "reference_image"
    VIDEO_CLIP = "video_clip"

class GeneratedAsset(BaseModel):
    """A generated image or video asset."""
    asset_type: AssetType
    element_id: str | None = None     # For reference images
    scene_number: int | None = None   # For video clips
    local_path: str
    gcs_uri: str | None = None

class ProductionPackage(BaseModel):
    """Complete package for video production."""
    script: VideoScript
    reference_images: list[GeneratedAsset] = []
    video_clips: list[GeneratedAsset] = []
    final_video_path: str | None = None
```

---

#### Task 2.3: Implement Agent Output Models
**Description**: Create structured output types for each agent.

**File**: `src/sip_videogen/models/agent_outputs.py`

**Models to implement**:
- `ScreenwriterOutput` - Contains `scenes: list[SceneAction]`
- `ProductionDesignerOutput` - Contains `shared_elements: list[SharedElement]`
- `ContinuitySupervisorOutput` - Contains validated script with optimized prompts
- `ShowrunnerOutput` - Contains complete `VideoScript`

These models are used with OpenAI Agents SDK's `output_type` parameter for structured responses.

---

### Stage 3: Agent Team

#### Task 3.1: Implement Screenwriter Agent
**Description**: Create the agent that breaks down ideas into scenes.

**File**: `src/sip_videogen/agents/screenwriter.py`

**Responsibilities**:
- Take a creative brief (user's idea + parameters)
- Produce 3-5 scenes with clear narrative arc
- Write concrete, visual action descriptions
- Suggest dialogue if applicable

**Implementation using OpenAI Agents SDK**:

```python
from agents import Agent
from ..models.agent_outputs import ScreenwriterOutput

screenwriter_agent = Agent(
    name="Screenwriter",
    instructions="""You are a professional screenwriter specializing in short-form video content.
Given a creative brief, produce:
1. Scene breakdown with clear narrative arc
2. Action descriptions (concrete, visual, suitable for AI video generation)
3. Dialogue if applicable
4. Duration per scene (4, 6, or 8 seconds)

Emphasize clear, visual descriptions. Each scene should be 4-8 seconds.
""",
    output_type=ScreenwriterOutput,
)
```

**Store detailed prompts in**: `src/sip_videogen/agents/prompts/screenwriter.md`

**Reference**: https://openai.github.io/openai-agents-python/

---

#### Task 3.2: Implement Production Designer Agent
**Description**: Create the agent that identifies visual elements needing consistency.

**File**: `src/sip_videogen/agents/production_designer.py`

**Responsibilities**:
- Analyze scenes to identify recurring elements (characters, props, environments)
- Create detailed visual specifications for each shared element
- Distinguish between shared elements (need reference images) and unique elements

**Output**: `ProductionDesignerOutput` with list of `SharedElement`s

**Key considerations**:
- Visual descriptions must be detailed enough for image generation
- Include physical attributes, clothing, colors, distinguishing features
- Track which scenes each element appears in

---

#### Task 3.3: Implement Continuity Supervisor Agent
**Description**: Create the agent that validates consistency.

**File**: `src/sip_videogen/agents/continuity_supervisor.py`

**Responsibilities**:
- Review scenes and shared elements for consistency
- Optimize prompts for AI generation (add specific descriptors)
- Flag potential continuity issues
- Ensure reference image descriptions match scene descriptions

**Output**: `ContinuitySupervisorOutput` with validated/optimized script

---

#### Task 3.4: Implement Showrunner Orchestrator
**Description**: Create the main orchestrator using the agent-as-tool pattern.

**File**: `src/sip_videogen/agents/showrunner.py`

**This is the key integration point.** The Showrunner invokes other agents as tools.

**Implementation pattern**:

```python
from agents import Agent, Runner

# Convert specialist agents to tools
showrunner_agent = Agent(
    name="Showrunner",
    instructions="""You are an experienced showrunner with creative control.
Your job is to:
1. Interpret the user's idea into a creative vision
2. Call the screenwriter to develop scenes
3. Call the production designer to identify shared elements
4. Call the continuity supervisor to validate consistency
5. Synthesize everything into a final VideoScript
""",
    tools=[
        screenwriter_agent.as_tool(
            tool_name="screenwriter",
            tool_description="Develops scene breakdown and action descriptions",
        ),
        production_designer_agent.as_tool(
            tool_name="production_designer",
            tool_description="Identifies shared visual elements needing consistency",
        ),
        continuity_supervisor_agent.as_tool(
            tool_name="continuity_supervisor",
            tool_description="Validates consistency and optimizes prompts",
        ),
    ],
    output_type=VideoScript,  # Final structured output
)

# Function to run the orchestration
async def develop_script(idea: str, num_scenes: int) -> VideoScript:
    result = await Runner.run(
        showrunner_agent,
        f"Create a {num_scenes}-scene video from this idea: {idea}"
    )
    return result.final_output_as(VideoScript)
```

**Reference**:
- Agent-as-tool pattern: https://openai.github.io/openai-agents-python/agents/#agents-as-tools
- Structured outputs: https://openai.github.io/openai-agents-python/results/#structured-output-types

---

### Stage 4: Image Generation

#### Task 4.1: Implement Gemini Image Generator
**Description**: Create the image generation service using Google's Gemini API.

**File**: `src/sip_videogen/generators/image_generator.py`

**Functionality**:
- Generate reference images for each `SharedElement`
- Save images locally and upload to GCS
- Return updated `SharedElement` with paths

**Implementation using google-genai SDK**:

```python
from google import genai
from google.genai import types

class ImageGenerator:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def generate_reference_image(
        self,
        element: SharedElement,
        output_dir: Path,
    ) -> GeneratedAsset:
        """Generate a reference image for a shared element."""
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-image",  # or gemini-3-pro-image-preview for higher quality
            contents=element.visual_description,
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",  # Square for character references
                    # image_size="2K"  # Only for gemini-3-pro-image-preview
                )
            )
        )

        # Save image
        for part in response.parts:
            if part.inline_data:
                image = part.as_image()
                image_path = output_dir / f"{element.id}.png"
                image.save(str(image_path))
                return GeneratedAsset(
                    asset_type=AssetType.REFERENCE_IMAGE,
                    element_id=element.id,
                    local_path=str(image_path),
                )
```

**Notes**:
- Use `gemini-2.5-flash-image` for production (more stable)
- Use `gemini-3-pro-image-preview` if 4K quality is needed
- Wrap in retry logic using `tenacity`

**Reference**: https://ai.google.dev/gemini-api/docs/image-generation

---

#### Task 4.2: Implement GCS Upload for Reference Images
**Description**: Upload generated images to Google Cloud Storage for VEO consumption.

**File**: `src/sip_videogen/storage/gcs.py`

**Functionality**:
- Upload local image files to GCS bucket
- Return GCS URI (`gs://bucket/path/file.png`)
- Handle authentication via ADC (Application Default Credentials)

**Implementation**:

```python
from google.cloud import storage

class GCSStorage:
    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def upload_file(self, local_path: Path, remote_path: str) -> str:
        """Upload a file and return its GCS URI."""
        blob = self.bucket.blob(remote_path)
        blob.upload_from_filename(str(local_path))
        return f"gs://{self.bucket.name}/{remote_path}"
```

**Important**: VEO requires images to be in GCS, not local paths.

---

### Stage 5: Video Generation

#### Task 5.1: Implement VEO 3.1 Video Generator
**Description**: Create the video generation service using Vertex AI.

**File**: `src/sip_videogen/generators/video_generator.py`

**Key constraint**: Must use Vertex AI client (not API key auth).

**Implementation**:

```python
from google import genai
from google.genai.types import GenerateVideosConfig, VideoGenerationReferenceImage, Image
import time

class VideoGenerator:
    def __init__(self, project: str, location: str):
        # Client uses Vertex AI when GOOGLE_GENAI_USE_VERTEXAI=True
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )

    async def generate_video_clip(
        self,
        scene: SceneAction,
        reference_images: list[GeneratedAsset],
        output_gcs_uri: str,
    ) -> GeneratedAsset:
        """Generate a video clip for a scene."""
        # Build reference image configs
        ref_configs = []
        for asset in reference_images[:3]:  # Max 3 reference images
            ref_configs.append(
                VideoGenerationReferenceImage(
                    image=Image(
                        gcs_uri=asset.gcs_uri,
                        mime_type="image/png",
                    ),
                    reference_type="asset",
                )
            )

        # Generate video
        operation = self.client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=self._build_prompt(scene),
            config=GenerateVideosConfig(
                reference_images=ref_configs if ref_configs else None,
                duration_seconds=8 if ref_configs else scene.duration_seconds,
                aspect_ratio="16:9",
                output_gcs_uri=output_gcs_uri,
                generate_audio=True,
            ),
        )

        # Poll for completion
        while not operation.done:
            time.sleep(15)
            operation = self.client.operations.get(operation)

        video_uri = operation.result.generated_videos[0].video.uri
        return GeneratedAsset(
            asset_type=AssetType.VIDEO_CLIP,
            scene_number=scene.scene_number,
            gcs_uri=video_uri,
            local_path="",  # Will be set after download
        )

    def _build_prompt(self, scene: SceneAction) -> str:
        """Combine scene elements into a generation prompt."""
        parts = [scene.action_description]
        if scene.setting_description:
            parts.insert(0, f"Setting: {scene.setting_description}")
        if scene.camera_direction:
            parts.append(f"Camera: {scene.camera_direction}")
        return ". ".join(parts)
```

**Critical constraints**:
- Max 3 reference images per video
- Reference images force 8-second duration
- Images must be GCS URIs
- Duration must be 4, 6, or 8 seconds

**Reference**: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation

---

#### Task 5.2: Implement Parallel Video Generation
**Description**: Generate multiple video clips in parallel for efficiency.

**Implementation hints**:
- Use `asyncio.gather()` to run multiple generations concurrently
- Respect rate limits (add small delays if needed)
- Track progress with Rich progress bar

---

#### Task 5.3: Implement Video Download from GCS
**Description**: Download generated videos from GCS to local filesystem.

Add to `src/sip_videogen/storage/gcs.py`:

```python
def download_file(self, gcs_uri: str, local_path: Path) -> Path:
    """Download a file from GCS."""
    # Parse gs://bucket/path format
    parts = gcs_uri.replace("gs://", "").split("/", 1)
    bucket_name, blob_path = parts[0], parts[1]

    blob = self.client.bucket(bucket_name).blob(blob_path)
    blob.download_to_filename(str(local_path))
    return local_path
```

---

### Stage 6: Video Assembly

#### Task 6.1: Implement FFmpeg Wrapper
**Description**: Concatenate video clips into final video.

**File**: `src/sip_videogen/assembler/ffmpeg.py`

**Prerequisites**: FFmpeg must be installed on the system.

**Implementation**:

```python
import subprocess
from pathlib import Path

class FFmpegAssembler:
    def concatenate_clips(
        self,
        clip_paths: list[Path],
        output_path: Path,
    ) -> Path:
        """Concatenate video clips in order."""
        # Create concat file
        concat_file = output_path.parent / "concat_list.txt"
        with open(concat_file, "w") as f:
            for clip in clip_paths:
                f.write(f"file '{clip.absolute()}'\n")

        # Run FFmpeg
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # Cleanup
        concat_file.unlink()
        return output_path
```

**Notes**:
- Use `-c copy` for fast concatenation without re-encoding (if codecs match)
- May need re-encoding if clips have different parameters

---

### Stage 7: Integration and Polish

#### Task 7.1: Wire Up the Full Pipeline in CLI
**Description**: Connect all components in the `generate` command.

**File**: `src/sip_videogen/cli.py`

**Flow**:
1. Load settings and validate configuration
2. Run Showrunner to develop script (`--dry-run` stops here)
3. Generate reference images for shared elements
4. Upload reference images to GCS
5. Generate video clips (parallel where possible)
6. Download video clips from GCS
7. Concatenate clips with FFmpeg
8. Display final video path

**Use Rich for progress**:
- Progress bars for each stage
- Status messages
- Final summary with video details

---

#### Task 7.2: Implement Error Handling
**Description**: Add robust error handling throughout.

**Key areas**:
- API failures (add retry with `tenacity`)
- Missing configuration (clear error messages)
- GCS permission errors
- FFmpeg not installed
- Invalid user input

**Pattern**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
)
async def generate_with_retry(...):
    ...
```

---

#### Task 7.3: Add Cost Estimation
**Description**: Warn users about potential costs before generation.

**Approximate costs** (as of Dec 2024):
- Gemini image: ~$0.13/image (2K) to $0.24/image (4K)
- VEO video: Check current Vertex AI pricing

Display estimated cost before proceeding (can be bypassed with `--yes` flag).

---

#### Task 7.4: Write Tests
**Description**: Create test suite for critical components.

**Test files**:
- `tests/test_models.py` - Model validation
- `tests/test_agents.py` - Agent mocking and integration
- `tests/test_generators.py` - Generator mocking
- `tests/test_cli.py` - CLI command testing

**Use pytest fixtures** for common setup.

---

## Environment Setup Checklist

For developers to get started:

1. **Install Python 3.11+**

2. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Install FFmpeg**:
   ```bash
   brew install ffmpeg  # macOS
   ```

4. **Set up Google Cloud**:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT
   gcloud services enable aiplatform.googleapis.com storage.googleapis.com
   gsutil mb -l us-central1 gs://YOUR_BUCKET_NAME
   ```

5. **Create `.env` file**:
   ```bash
   OPENAI_API_KEY=sk-...
   GEMINI_API_KEY=...
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   SIP_GCS_BUCKET_NAME=your-bucket-name
   GOOGLE_GENAI_USE_VERTEXAI=True
   SIP_OUTPUT_DIR=./output
   ```

6. **Verify setup**:
   ```bash
   sip-videogen status
   ```

---

## Documentation References

- **OpenAI Agents SDK**: https://openai.github.io/openai-agents-python/
- **Google GenAI SDK**: https://github.com/googleapis/python-genai
- **Gemini Image Generation**: https://ai.google.dev/gemini-api/docs/image-generation
- **VEO 3.1 on Vertex AI**: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation
- **Typer CLI**: https://typer.tiangolo.com/
- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- **Rich Library**: https://rich.readthedocs.io/
- **FFmpeg Documentation**: https://ffmpeg.org/documentation.html
