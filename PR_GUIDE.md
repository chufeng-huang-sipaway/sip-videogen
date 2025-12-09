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

### Pending Tasks
- [ ] Task 2.2: Implement Asset and Production Models
- [ ] Task 2.3: Implement Agent Output Models
- [ ] Task 3.1-3.4: Agent Team Implementation
- [ ] Task 4.1-4.2: Image Generation
- [ ] Task 5.1-5.3: Video Generation
- [ ] Task 6.1: FFmpeg Wrapper
- [ ] Task 7.1-7.4: Integration and Polish

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
│       ├── agents/
│       │   ├── __init__.py
│       │   └── prompts/
│       │       └── __init__.py
│       ├── assembler/
│       │   └── __init__.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── logging.py
│       │   └── settings.py
│       ├── generators/
│       │   └── __init__.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── script.py
│       └── storage/
│           └── __init__.py
└── tests/
    └── __init__.py
```

## How to Continue
1. Read `TASKS.md` for detailed task specifications
2. The next task is **Task 2.2: Implement Asset and Production Models**
3. Follow the implementation hints in the task description

## Testing
```bash
# Install in development mode
pip install -e ".[dev]"

# Run the CLI
sip-videogen --help
```
