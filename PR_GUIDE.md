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

### Phase 2: Remove CLI Product Surface (Task 3)

**Commit:** `e438ea5` - chore: Delete cli.py and start.sh (Phase 2, Task 3)

**Changes:**
- Deleted `src/sip_videogen/cli.py` (150KB Typer CLI application)
- Deleted `start.sh` (CLI launcher script)

**Verification:**
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 2: Remove CLI Product Surface (Task 4)

**Commit:** `dedb666` - chore: Delete CLI-only config wizard setup.py (Phase 2, Task 4)

**Changes:**
- Deleted `src/sip_videogen/config/setup.py`
  - Interactive CLI setup wizard that used questionary to configure API keys
  - Brand Studio handles API key management via `studio/bridge.py`, so this is no longer needed

**Verification:**
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 2: Remove CLI Product Surface (Task 5)

**Commit:** `cfa80b0` - chore: Delete utils/ directory with pipx updater (Phase 2, Task 5)

**Changes:**
- Deleted `src/sip_videogen/utils/__init__.py`
- Deleted `src/sip_videogen/utils/updater.py`
  - pipx CLI update flow implementation
  - utils/ was CLI-only and not used by Brand Studio or video infrastructure

**Verification:**
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 2: Remove CLI Product Surface (Task 6)

**Commit:** `40d04ba` - chore: Remove CLI deps and tests (Phase 2, Task 6)

**Changes:**
- Removed `typer[all]` and `questionary` from `pyproject.toml` dependencies
- Deleted `tests/test_cli.py` (tested deleted cli.py)
- Deleted `tests/test_setup.py` (tested deleted config/setup.py)
- Deleted `tests/test_updater.py` (tested deleted utils/updater.py)

**Verification:**
- `python -m pytest`: 474 passed (14 failures + 43 errors are pre-existing audio test issues)
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 2: Remove CLI Product Surface (Task 7)

**Commit:** `0f417a9` - docs: Remove CLI/pipx references, add video backend docs (Phase 2, Task 7)

**Changes:**
- Removed "Legacy: Video Generation CLI" section from README.md
- Replaced with "Video Generation Backend (Internal)" section showing API usage
- Updated scripts/publish.sh to remove pipx reference and note CLI removal
- README now only documents Brand Studio and internal video API

**Verification:**
- `python -m pytest`: 474 passed (14 failures + 43 errors are pre-existing audio test issues)
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 3: Remove Brand Kit Workflow (Task 1)

**Commit:** `c1aaad0` - chore: Delete brand_kit/ directory and update tests (Phase 3, Task 1)

**Changes:**
- Deleted `src/sip_videogen/brand_kit/` directory (including `__init__.py` and `workflow.py`)
- Updated `tests/test_brand_integration.py`:
  - Removed imports from `sip_videogen.brand_kit.workflow`
  - Removed test classes/methods that depended on brand_kit functions
  - Rewrote tests to verify brand storage directly instead of using brand_kit workflow
  - Kept brand-only workflow coverage intact (18 tests retained)

**Verification:**
- `python -m pytest`: 463 passed (14 failures are pre-existing issues unrelated to this change)
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 3: Remove Brand Kit Workflow (Task 2)

**Commit:** `93e477e` - chore: Delete brand_designer agent and prompt (Phase 3, Task 2)

**Changes:**
- Deleted `src/sip_videogen/agents/brand_designer.py` (Brand Kit planning agent)
- Deleted `src/sip_videogen/agents/prompts/brand_designer.md` (agent prompt file)
- Updated `src/sip_videogen/agents/__init__.py`:
  - Removed `brand_designer_agent` and `plan_brand_kit` imports
  - Removed from `__all__` exports

**Verification:**
- `python -m pytest`: 463 passed (14 failures + 43 errors are pre-existing audio test issues)
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 3: Remove Brand Kit Workflow (Task 3)

**Commit:** `58bd701` - chore: Delete brand_kit models and remove migration imports (Phase 3, Task 3)

**Changes:**
- Deleted `src/sip_videogen/models/brand_kit.py` (Brand Kit data models)
- Updated `src/sip_videogen/models/__init__.py`:
  - Removed brand_kit imports and exports (BrandAssetCategory, BrandAssetPrompt, BrandAssetResult, BrandDirection, BrandKitBrief, BrandKitPackage, BrandKitPlan)
- Updated `src/sip_videogen/brands/__init__.py`:
  - Removed migration imports (required to keep Brand Studio working since migration.py imported from brand_kit.py)
  - Removed migration exports from `__all__`
- Deleted `tests/test_brands_migration.py` (tested now-broken migration functionality)

**Verification:**
- `python -m pytest`: 444 passed (14 failures + 43 errors are pre-existing audio test issues)
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 3: Remove Brand Kit Workflow (Task 4)

**Commit:** `5df6f3e` - chore: Delete brands/migration.py (Phase 3, Task 4)

**Changes:**
- Deleted `src/sip_videogen/brands/migration.py`
  - Brand Kit migration module that converted legacy `brand_kit.json` to new brand format
  - Module depended on deleted `models/brand_kit.py` and was no longer importable
  - Migration imports were already removed from `brands/__init__.py` in Task 3

**Verification:**
- `python -m pytest`: 444 passed (14 failures + 43 errors are pre-existing audio test issues)
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 3: Remove Brand Kit Workflow (Task 5)

**Commit:** `4034180` - chore: Delete NanoBananaImageGenerator (Phase 3, Task 5)

**Changes:**
- Deleted `src/sip_videogen/generators/nano_banana_generator.py`
  - Nano Banana Pro image generator was only used by Brand Kit workflow
  - Wrapper around Google's Gemini image generation API
- Updated `src/sip_videogen/generators/__init__.py`:
  - Removed `NanoBananaImageGenerator` import
  - Removed `NanoBananaImageGenerator` from `__all__` exports

**Verification:**
- `python -m pytest`: 444 passed (14 failures + 43 errors are pre-existing audio test issues)
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

### Phase 4: Final Hardening (Task 1)

**Commit:** `8f6980f` - test: Add video backend smoke tests (Phase 4, Task 1)

**Changes:**
- Created `tests/test_video_backend_smoke.py` with 16 smoke tests:
  - `TestVideoBackendImports`: Verify all video backend modules are importable
    - Video pipeline module (VideoPipeline, PipelineConfig, etc.)
    - Generator module (VEO, Kling, Sora generators)
    - Assembler module (FFmpegAssembler)
    - Video-related models (VideoScript, GeneratedAsset, etc.)
  - `TestVideoGeneratorFactorySmoke`: Factory instantiation with mocked credentials
    - VEO generator creation
    - Kling generator creation
    - Sora generator creation
    - Factory method existence checks
  - `TestVideoPipelineSmoke`: Pipeline class instantiation
    - Pipeline config dataclass
    - Pipeline result dataclass
  - `TestVideoProviderEnum`: Provider enum values

**Verification:**
- `python -m pytest`: 460 passed (16 new tests, 14 failures + 43 errors are pre-existing audio test issues)
- `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`: passes
- `python -c "from sip_videogen.video import VideoPipeline"`: passes

## Remaining Tasks

### Phase 1: Extract Video Backend API
- [x] Create `src/sip_videogen/video/__init__.py` and `pipeline.py`
- [x] Move orchestration logic from cli.py to new API
- [x] Add unit tests for new API (mock external calls)
- [x] Run verification (pytest + smoke tests)

### Phase 2: Remove CLI Product Surface ✅ COMPLETE
- [x] Remove `[project.scripts]` entries from pyproject.toml
- [x] Delete `src/sip_videogen/__main__.py`
- [x] Delete CLI files (cli.py, start.sh)
- [x] Delete config/setup.py
- [x] Delete utils/ directory
- [x] Remove typer/questionary dependencies
- [x] Delete CLI-dependent tests (test_cli.py, test_setup.py, test_updater.py)
- [x] Documentation cleanup (README.md, scripts/publish.sh)
- [x] Manual verification: `python -m sip_videogen.studio` launches in dev

### Phase 3: Remove Brand Kit Workflow ✅ COMPLETE
- [x] Delete brand_kit/ directory
- [x] Update test_brand_integration.py to remove brand_kit imports
- [x] Delete brand-kit-only agents (brand_designer.py) if unused
- [x] Update agents/__init__.py to remove Brand Kit planner exports
- [x] Delete brand-kit-only models (models/brand_kit.py) if unused
- [x] Remove Brand Kit exports from models/__init__.py
- [x] Update brands/__init__.py to remove migration imports
- [x] Delete test_brands_migration.py
- [x] Delete migration.py file
- [x] Delete NanoBananaImageGenerator if unused

### Phase 4: Final Hardening
- [x] Add video backend smoke test
- [ ] Confirm Brand Studio packaging works
- [ ] Update README with "Video Generation Backend" section (already done in Phase 2)

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
