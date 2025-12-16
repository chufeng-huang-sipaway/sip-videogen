# PR Guide: Legacy Cleanup - Remove CLI, Keep Video Infrastructure

## Overview

This PR removes the legacy CLI tool and Brand Kit workflow while preserving the video generation infrastructure for future use. The goal is to focus the repo on Brand Studio + Brand Advisor.

## Task List Reference

See `docs/legacy-cleanup-video-infra-todo.md` for the complete task list.

## Completed Tasks

### Phase 0: Baseline & Inventory

**Commit:** `d375359` - chore: Complete Phase 0 baseline & inventory for legacy cleanup

**Changes:**
- Created branch `cleanup/remove-cli-keep-video-infra`
- Ran baseline checks:
  - `python -m pytest`: 505 passed (20 failures + 43 errors are pre-existing audio test issues)
  - `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- Inventoried files to be removed:
  - `src/sip_videogen/cli.py` (Typer + questionary) - 150KB
  - `src/sip_videogen/__main__.py` (runs CLI)
  - `start.sh` (CLI launcher)
  - `src/sip_videogen/utils/updater.py` (pipx update flow)
  - `src/sip_videogen/brand_kit/` (workflow.py)
  - `src/sip_videogen/config/setup.py` (CLI wizard)
  - Docs referencing pipx/CLI in README.md, scripts/publish.sh

**Verification:**
- Brand Studio import smoke test passes
- pytest baseline established (505 passing tests)

### Phase 1: Extract Video Backend API (Task 1)

**Commit:** `7711995` - feat: Add video backend API module (Phase 1, Task 1)

**Changes:**
- Created `src/sip_videogen/video/__init__.py` - module exports
- Created `src/sip_videogen/video/pipeline.py` - non-interactive pipeline API

**New API:**
- `VideoPipeline` class for full control over generation
- `PipelineConfig` dataclass for configuration
- `PipelineResult` dataclass for structured output
- `generate_video()` convenience function

**Pipeline Stages:**
1. Script development via Showrunner agent team
2. Reference image generation with quality review
3. Video clip generation via provider (VEO, Kling, Sora)
4. Optional background music generation
5. Final assembly via FFmpeg

**Verification:**
- `python -c "from sip_videogen.video import VideoPipeline"` passes
- Brand Studio import smoke test passes

### Phase 1: Extract Video Backend API (Task 2)

**Commit:** `ff5a00b` - test: Add unit tests for video pipeline API (Phase 1, Task 2)

**Changes:**
- Created `tests/test_video_pipeline.py` with 18 comprehensive unit tests

**Test Coverage:**
- `TestPipelineConfig` - validates default and custom configuration values
- `TestPipelineResult` - validates result dataclass fields
- `TestVideoPipeline` - core pipeline functionality:
  - Initialization and progress callback registration
  - Project ID generation format
  - Dry run mode (script only, no video)
  - Using existing script vs developing new
  - Custom project ID support
  - PipelineError on script development failure
- `TestVideoPipelineFullRun` - happy path test with mocked stages
- `TestVideoGeneratorFactoryIntegration` - provider selection:
  - VEO provider via explicit config
  - Kling provider via explicit config
  - Sora provider via UserPreferences fallback
- `TestGenerateVideoConvenience` - convenience function wrapper
- `TestPipelineError` - exception behavior

**Verification:**
- `python -m pytest`: 523 passed (18 new tests added)
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes

### Phase 2: Remove CLI Product Surface (Task 1)

**Commit:** `82fe504` - chore: Remove CLI script entries from pyproject.toml (Phase 2, Task 1)

**Changes:**
- Removed `[project.scripts]` section from `pyproject.toml`:
  - `sip-videogen = "sip_videogen.cli:app"`
  - `sipvid = "sip_videogen.cli:app"`

**Verification:**
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 2: Remove CLI Product Surface (Task 2)

**Commit:** `78944fb` - chore: Delete __main__.py CLI entrypoint (Phase 2, Task 2)

**Changes:**
- Deleted `src/sip_videogen/__main__.py`
  - This file only contained CLI entrypoint code (`from sip_videogen.cli import app`)
  - Removed the ability to run CLI via `python -m sip_videogen`

**Verification:**
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

## Remaining Tasks

### Phase 1: Extract Video Backend API
- [x] Create `src/sip_videogen/video/__init__.py` and `pipeline.py`
- [x] Move orchestration logic from cli.py to new API
- [x] Add unit tests for new API (mock external calls)
- [x] Run verification (pytest + smoke tests)

### Phase 2: Remove CLI Product Surface
- [x] Remove `[project.scripts]` entries from pyproject.toml
- [x] Delete `src/sip_videogen/__main__.py`
- [ ] Delete CLI files (cli.py, start.sh)
- [ ] Delete config/setup.py
- [ ] Delete utils/ directory
- [ ] Remove typer/questionary dependencies
- [ ] Update tests and documentation

### Phase 3: Remove Brand Kit Workflow
- [ ] Delete brand_kit/ directory
- [ ] Delete migration.py if not needed
- [ ] Remove Brand Kit exports/imports
- [ ] Delete NanoBananaImageGenerator if unused
- [ ] Update tests

### Phase 4: Final Hardening
- [ ] Add video backend smoke test
- [ ] Confirm Brand Studio packaging works
- [ ] Update README with "Video Generation Backend" section

## Testing

```bash
# Run all tests
source .venv/bin/activate && python -m pytest

# Brand Studio smoke test
python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"

# Launch Brand Studio (dev)
python -m sip_videogen.studio
```

## Notes

- Pre-existing test failures in `tests/test_video_generator_audio.py` are not related to this cleanup
- Video infrastructure (generators, assembler, models) must remain stable and importable
- Brand Studio must not be affected by any changes
