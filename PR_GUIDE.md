# PR Guide: sip-videogen Development

## Overview
This PR implements the sip-videogen CLI tool that transforms vague video ideas into complete videos using an AI agent team.

## Current Progress

### Completed Tasks
- [x] **Task 1.1: Initialize Project Structure**
  - Created `pyproject.toml` with all dependencies
  - Directory structure: `src/sip_videogen/` with subfolders (agents, generators, models, config, assembler, storage)
  - `__init__.py` files in all packages
  - `__main__.py` for `python -m sip_videogen` execution
  - `.env.example` with all required environment variables
  - `.gitignore` for Python projects
  - Placeholder `cli.py` with Typer app

- [x] **Task 1.2: Implement Configuration with Pydantic Settings**
  - Created `src/sip_videogen/config/settings.py` with `Settings` class using pydantic-settings
  - All required settings: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `SIP_GCS_BUCKET_NAME`, `SIP_OUTPUT_DIR`, `SIP_DEFAULT_SCENES`, `SIP_VIDEO_DURATION`, `SIP_LOG_LEVEL`
  - Singleton `get_settings()` function with LRU cache for efficient access
  - `is_configured()` helper method to check setup status
  - Video duration validation to VEO-supported values (4, 6, 8 seconds)
  - Added `README.md` for package building requirements

- [x] **Task 1.3: Create CLI Skeleton with Typer**
  - Enhanced `src/sip_videogen/cli.py` with full CLI implementation
  - `generate` command: Takes idea as argument, `--scenes` option (1-10), `--dry-run` flag
  - `status` command: Validates all required env vars are set, displays settings table
  - `setup` command: Interactive guide with step-by-step setup instructions
  - Uses Rich for pretty output: Console, Panel, and Table components
  - Configuration validation with clear error messages

- [x] **Task 1.4: Set Up Logging with Rich**
  - Created `src/sip_videogen/config/logging.py` with `setup_logging()` and `get_logger()` functions
  - Uses `RichHandler` for pretty console output with rich tracebacks
  - Supports optional file logging
  - Log level configured from `SIP_LOG_LEVEL` environment variable (default: INFO)
  - Logging initialized in CLI `main()` function
  - Added logging calls to `generate` command for traceability

- [x] **Task 2.1: Implement Core Script Models**
  - Created `src/sip_videogen/models/script.py` with Pydantic models
  - `ElementType` enum: character, environment, prop
  - `SharedElement`: Visual elements needing consistency across scenes with reference image paths
  - `SceneAction`: Scene breakdown with action, setting, dialogue, camera direction
  - `VideoScript`: Complete script with helper methods (`total_duration`, `get_element_by_id`, `get_elements_for_scene`)
  - Updated `models/__init__.py` with exports

- [x] **Task 2.2: Implement Asset and Production Models**
  - Created `src/sip_videogen/models/assets.py` with Pydantic models
  - `AssetType` enum: reference_image, video_clip
  - `GeneratedAsset`: Tracks local paths and GCS URIs for generated images/videos
  - `ProductionPackage`: Aggregates script and all assets with helper methods:
    - `get_reference_image_for_element()`: Find reference image by element ID
    - `get_video_clip_for_scene()`: Find video clip by scene number
    - `is_complete` property: Verify all required assets are generated
  - Updated `models/__init__.py` with exports

- [x] **Task 2.3: Implement Agent Output Models**
  - Created `src/sip_videogen/models/agent_outputs.py` with structured output types
  - `ScreenwriterOutput`: Contains scenes list and narrative notes
  - `ProductionDesignerOutput`: Contains shared elements and design notes
  - `ContinuityIssue`: Model for tracking continuity issues found during validation
  - `ContinuitySupervisorOutput`: Contains validated script with optimized prompts and issues list
  - `ShowrunnerOutput`: Contains complete VideoScript ready for production
  - Updated `models/__init__.py` with exports for all agent output models

- [x] **Task 3.1: Implement Screenwriter Agent**
  - Created `src/sip_videogen/agents/screenwriter.py` with OpenAI Agents SDK
  - `screenwriter_agent`: Agent configured with structured output using `ScreenwriterOutput`
  - `develop_scenes()`: Async function to develop scene breakdown from creative idea
  - Detailed prompt stored in `src/sip_videogen/agents/prompts/screenwriter.md`
  - Prompt covers scene structure, action descriptions, duration guidelines, camera directions
  - Updated `agents/__init__.py` with exports for agent and function

- [x] **Task 3.2: Implement Production Designer Agent**
  - Created `src/sip_videogen/agents/production_designer.py` with OpenAI Agents SDK
  - `production_designer_agent`: Agent configured with structured output using `ProductionDesignerOutput`
  - `identify_shared_elements()`: Async function to analyze scenes and identify recurring visual elements
  - Detailed prompt stored in `src/sip_videogen/agents/prompts/production_designer.md`
  - Prompt covers element types (characters, environments, props), visual description guidelines, ID naming conventions
  - Updated `agents/__init__.py` with exports for agent and function

- [x] **Task 3.3: Implement Continuity Supervisor Agent**
  - Created `src/sip_videogen/agents/continuity_supervisor.py` with OpenAI Agents SDK
  - `continuity_supervisor_agent`: Agent configured with structured output using `ContinuitySupervisorOutput`
  - `validate_and_optimize()`: Async function to review scenes/elements for consistency and optimize prompts
  - Detailed prompt stored in `src/sip_videogen/agents/prompts/continuity_supervisor.md`
  - Prompt covers continuity checks (visual, logical, technical), prompt optimization for AI video generation, reference image compatibility
  - Updated `agents/__init__.py` with exports for agent and function

- [x] **Task 3.4: Implement Showrunner Orchestrator**
  - Created `src/sip_videogen/agents/showrunner.py` with OpenAI Agents SDK
  - `showrunner_agent`: Orchestrator agent using agent-as-tool pattern
  - Coordinates screenwriter, production_designer, and continuity_supervisor agents as tools
  - `develop_script()`: Async function as main entry point for script development
  - Detailed prompt stored in `src/sip_videogen/agents/prompts/showrunner.md`
  - Prompt covers 5-step orchestration process, creative guidelines, technical awareness (VEO constraints)
  - Updated `agents/__init__.py` with exports for showrunner_agent and develop_script

- [x] **Task 4.1: Implement Gemini Image Generator**
  - Created `src/sip_videogen/generators/image_generator.py` with Google GenAI SDK
  - `ImageGenerator` class using `google-genai` Client with API key authentication
  - `generate_reference_image()`: Async method to generate image for a SharedElement
  - `generate_all_reference_images()`: Batch method to process all shared elements
  - Uses `gemini-2.5-flash-image` model (production-ready, GA)
  - Automatic retry logic with exponential backoff using `tenacity`
  - Element-type-aware aspect ratios (1:1 for characters/props, 16:9 for environments)
  - Prompt building with type-specific context for better generation results
  - `ImageGenerationError` exception for proper error handling
  - Updated `generators/__init__.py` with exports

- [x] **Task 4.2: Implement GCS Upload for Reference Images**
  - Created `src/sip_videogen/storage/gcs.py` with Google Cloud Storage client
  - `GCSStorage` class using `google-cloud-storage` Client with Application Default Credentials (ADC)
  - `upload_file()`: Upload local files to GCS bucket, returns GCS URI (gs://bucket/path)
  - `download_file()`: Download files from GCS URIs to local filesystem
  - `file_exists()`: Check if a file exists in the bucket
  - `delete_file()`: Delete files from the bucket
  - `generate_remote_path()`: Helper to generate remote paths with prefixes
  - Automatic retry logic with exponential backoff using `tenacity`
  - `GCSStorageError` exception for proper error handling
  - Updated `storage/__init__.py` with exports

- [x] **Task 5.1: Implement VEO 3.1 Video Generator**
  - Created `src/sip_videogen/generators/video_generator.py` with Google VEO 3.1 via Vertex AI
  - `VideoGenerator` class using `google-genai` Client with Vertex AI authentication
  - `generate_video_clip()`: Async method to generate video for a SceneAction
  - Supports up to 3 reference images for visual consistency
  - Handles VEO constraints: valid durations (4, 6, 8 seconds), forced 8s with reference images
  - Builds prompts from scene details (setting, action, camera direction, dialogue)
  - Polls for operation completion with configurable interval (15 seconds default)
  - Automatic retry logic with exponential backoff using `tenacity`
  - `VideoGenerationError` exception for proper error handling
  - Updated `generators/__init__.py` with exports

- [x] **Task 5.2: Implement Parallel Video Generation**
  - Added `generate_all_video_clips()` async method to `VideoGenerator` class
  - Uses `asyncio.gather()` for concurrent video generation across all scenes
  - Semaphore-controlled concurrency (default: 3 concurrent generations)
  - Inter-request delay (default: 2.0s) for API rate limit compliance
  - Rich progress bar with real-time status updates (spinner, progress %, elapsed time)
  - `_build_scene_reference_map()`: Maps scenes to their relevant reference images
  - Results sorted by scene number for proper video ordering
  - `VideoGenerationResult` dataclass for tracking generation outcomes:
    - `successful`: List of generated video clips
    - `failed_scenes`: List of scene numbers that failed
    - `success_rate` property: Percentage of successful generations
    - `all_succeeded` property: Boolean check for complete success
  - Updated `generators/__init__.py` with `VideoGenerationResult` export

- [x] **Task 5.3: Implement Video Download from GCS**
  - Already implemented as part of Task 4.2
  - `download_file()` method in `GCSStorage` class handles GCS to local file downloads
  - Parses GCS URI format (gs://bucket/path)
  - Creates parent directories automatically
  - Includes retry logic with exponential backoff

- [x] **Task 6.1: Implement FFmpeg Wrapper**
  - Created `src/sip_videogen/assembler/ffmpeg.py` with FFmpeg integration
  - `FFmpegAssembler` class for video concatenation operations
  - `concatenate_clips()`: Concatenate multiple video clips using FFmpeg concat demuxer
    - Supports both stream copy (fast, -c copy) and re-encode (compatible) modes
    - Creates temporary concat list file, cleans up after completion
    - Handles path escaping for special characters
  - `get_video_duration()`: Get video duration using ffprobe
  - `get_video_info()`: Get detailed video metadata (codec, resolution, fps, size)
  - `_verify_ffmpeg_installed()`: Automatic verification that FFmpeg is available in PATH
  - `FFmpegError` exception for proper error handling
  - Updated `assembler/__init__.py` with exports

- [x] **Task 7.1: Wire Up the Full Pipeline in CLI**
  - Implemented complete video generation pipeline in `src/sip_videogen/cli.py`
  - 6-stage pipeline with Rich progress bars:
    - Stage 1: Develop script using Showrunner agent orchestration
    - Stage 2: Generate reference images for shared elements using Gemini
    - Stage 3: Upload reference images to GCS for VEO consumption
    - Stage 4: Generate video clips in parallel using VEO 3.1
    - Stage 5: Download video clips from GCS
    - Stage 6: Concatenate clips into final video using FFmpeg
  - Dry-run mode (`--dry-run`) stops after script generation
  - Unique project IDs with timestamped folders for each run
  - Script saved as JSON for debugging/reuse
  - Script summary display with scenes and shared elements
  - Final summary with video duration and asset counts
  - Configuration validation before pipeline start
  - Proper error handling with user-friendly messages

- [x] **Task 7.2: Implement Error Handling**
  - Created `src/sip_videogen/exceptions.py` with centralized exception hierarchy:
    - `SipVideoGenError`: Base exception for all custom errors
    - `ConfigurationError`: For missing or invalid configuration
    - `AuthenticationError`: For API authentication failures
    - `APIError`, `RateLimitError`, `QuotaExceededError`: For API-related issues
    - `ValidationError`: For input validation failures
    - `PipelineError`: For pipeline execution failures
  - Enhanced `src/sip_videogen/storage/gcs.py` with specific GCS exceptions:
    - `GCSAuthenticationError`: For Google Cloud credential issues
    - `GCSBucketNotFoundError`: For missing buckets with creation instructions
    - `GCSPermissionError`: For access denied with IAM guidance
    - Bucket access verification on initialization
  - Added retry logic with `tenacity` to `src/sip_videogen/agents/showrunner.py`:
    - `ScriptDevelopmentError` exception for agent failures
    - Automatic retry (3 attempts) with exponential backoff
    - Input validation for idea string (length, emptiness)
  - Enhanced `src/sip_videogen/cli.py` with comprehensive error handling:
    - `_validate_idea()` function for input validation
    - Specific error handlers for each exception type
    - User-friendly error panels with actionable guidance
    - Descriptive error messages with troubleshooting hints
  - Updated `storage/__init__.py` and `agents/__init__.py` with new exception exports
  - Updated main `__init__.py` to export base exception classes

- [x] **Task 7.3: Add Cost Estimation**
  - Created `src/sip_videogen/config/costs.py` with cost estimation functions
  - `CostEstimate` dataclass for structured cost breakdown:
    - Image generation costs (count, per-unit, total)
    - Video generation costs (count, duration, per-second, total)
    - Total cost range (min/max)
  - `estimate_costs()`: Calculate costs from VideoScript or explicit counts
  - `estimate_pre_generation_costs()`: Estimate costs before script generation
  - Pricing constants (Dec 2024):
    - Gemini image: ~$0.02-0.13/image
    - VEO video: ~$0.08-0.15/second
    - OpenAI agent orchestration: ~$0.10 estimated
  - Enhanced `src/sip_videogen/cli.py` with cost confirmation:
    - Cost estimate panel displayed before video generation
    - Interactive confirmation prompt (can cancel)
    - `--yes/-y` flag to skip confirmation for automation
    - Cost estimation skipped for dry-run mode
  - Updated `config/__init__.py` with cost estimation exports

### Pending Tasks
- [ ] Task 7.4: Write Tests

## Project Structure
```
sip-videogen/
├── pyproject.toml
├── .env.example
├── .gitignore
├── src/
│   └── sip_videogen/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── exceptions.py          # NEW: Centralized exception hierarchy
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── screenwriter.py
│       │   ├── production_designer.py
│       │   ├── continuity_supervisor.py
│       │   ├── showrunner.py
│       │   └── prompts/
│       │       ├── __init__.py
│       │       ├── screenwriter.md
│       │       ├── production_designer.md
│       │       ├── continuity_supervisor.md
│       │       └── showrunner.md
│       ├── assembler/
│       │   ├── __init__.py
│       │   └── ffmpeg.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── costs.py               # NEW: Cost estimation module
│       │   ├── logging.py
│       │   └── settings.py
│       ├── generators/
│       │   ├── __init__.py
│       │   ├── image_generator.py
│       │   └── video_generator.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── agent_outputs.py
│       │   ├── assets.py
│       │   └── script.py
│       └── storage/
│           ├── __init__.py
│           └── gcs.py
└── tests/
    └── __init__.py
```

## How to Continue
1. Read `TASKS.md` for detailed task specifications
2. The next task is **Task 7.4: Write Tests**
3. Follow the implementation hints in the task description

## Testing
```bash
# Install in development mode
pip install -e ".[dev]"

# Run the CLI
sip-videogen --help
```
