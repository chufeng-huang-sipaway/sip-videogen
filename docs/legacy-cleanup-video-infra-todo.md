# Legacy Cleanup Plan (Keep Video Infra, Remove CLI + Brand Kit)

## Background

This repo started as an experimental “video generation CLI” and later evolved into **Brand Studio** (a macOS app) + **Brand Advisor** (agent + tools + skills). The long-term direction is clear:

- **Core product**: Brand Studio + Brand Advisor (must remain stable).
- **Legacy**: CLI tool (`sipvid` / `sip-videogen`), pipx distribution + updater flow, and Brand Kit workflow.
- **Requirement**: We still want to **retain video generation infrastructure** (providers/models, generators, FFmpeg assembly, script/image/video models) for future reuse — but we do **not** need the full end-user CLI feature right now.

This document is a step-by-step to-do list to remove legacy surfaces while preserving the underlying capability.

## Goals

- Keep and maintain the **video generation infrastructure** (generators + provider selection + core models + assembly).
- Remove the **CLI product surface** (Typer app, interactive menus, start.sh, pipx update flow, pipx docs).
- Remove **Brand Kit workflow** (planning + Nano Banana asset generation + related CLI commands).
- Keep the repo focused on **Brand Studio** without breaking it.

## Non‑Goals

- Do **not** build new UI/flows for video generation inside Brand Studio yet.
- Do **not** refactor Brand Studio, Advisor, or Brand storage as part of this cleanup (unless strictly required to keep builds/tests working).

## Guardrails / Rules (Hard Requirements)

1. **Brand Studio must not break.**
   - Do not change anything under:
     - `src/sip_videogen/studio/**`
     - `src/sip_videogen/studio/frontend/**`
     - `src/sip_videogen/advisor/**`
     - `src/sip_videogen/brands/**`
   - Exception: only if a build/test is impossible without a tiny fix; in that case, make the smallest possible change and call it out explicitly.

2. **Make small, reviewable PRs.**
   - Keep scope tight. Prefer 2–4 small PRs over 1 huge PR.

3. **No “delete first, figure out later”.**
   - Extract and test the video “backend API” first. Only then delete the CLI/Brand Kit surfaces.

4. **Every PR must include verification.**
   - Minimum: `python -m pytest`
   - Plus a Brand Studio import smoke test:
     - `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`
   - If packaging is part of your workflow: confirm `pyinstaller BrandStudio.spec` still works.

5. **Keep video infra stable and importable as a library.**
   - After cleanup, the repo should still provide:
     - `sip_videogen.generators.*` (VEO/Kling/Sora)
     - `sip_videogen.generators.VideoGeneratorFactory`
     - `sip_videogen.assembler.FFmpegAssembler`
     - `sip_videogen.models.*` for script/assets

## High‑Risk Areas / Notes

- **Shared config file**: Brand Studio stores API keys in `~/.sip-videogen/config.json` (via `studio/bridge.py`). Video infra uses `UserPreferences` in `src/sip_videogen/config/user_preferences.py`, which also reads/writes the same file path. Today this is mostly safe because only the legacy CLI calls `.save()`, but future video work could overwrite API keys if it calls `UserPreferences.save()`.
  - Do not change this during cleanup unless you handle merging safely (see optional task in Phase 1).

---

# Decisions to Confirm Up Front (avoid mid‑implementation churn)

- [ ] **NanoBananaImageGenerator**: Remove or keep?
  - Recommendation: **remove** if it’s only used by Brand Kit (it is not part of video generation infrastructure).
  - Alternative: if you want to keep it for future experiments, move it under a `legacy/` module and keep it out of default exports.
- [ ] **Config setup wizard** (`src/sip_videogen/config/setup.py`): Delete or keep?
  - Recommendation: **delete** with the CLI; it is CLI-wizard oriented and not used by Brand Studio.
- [ ] **Brand Kit migration** (`src/sip_videogen/brands/migration.py`): Delete or keep?
  - Recommendation: **delete** if you don’t have legacy `brand_kit.json` runs to migrate.
  - Alternative: if you still need it, move it to `legacy/` and decouple it from Brand Kit code before deleting Brand Kit.
- [ ] **Integration test coverage**: Don’t silently drop coverage.
  - Recommendation: **rewrite** `tests/test_brand_integration.py` to be brand-only (remove Brand Kit usage) instead of deleting the entire file.

# Task List (Step‑By‑Step)

## Phase 0 — Baseline & Inventory (no behavior changes)

- [x] Create a branch for cleanup work (e.g., `cleanup/remove-cli-keep-video-infra`).
- [x] Run baseline checks:
  - [x] `python -m pytest` — 505 passed (20 failures + 43 errors are pre-existing audio test issues)
  - [x] `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"` — ✅ passes
- [x] Inventory what will be removed (confirm these are CLI/legacy-only):
  - [x] `src/sip_videogen/cli.py` (Typer + questionary) — exists, 150KB
  - [x] `src/sip_videogen/__main__.py` (currently runs the CLI) — exists
  - [x] `start.sh` — exists
  - [x] `src/sip_videogen/utils/updater.py` (pipx update flow) — exists
  - [x] `src/sip_videogen/brand_kit/**` and brand-kit related models/agents — exists (workflow.py)
  - [x] Docs referencing pipx/CLI in `README.md`, `scripts/publish.sh`, etc. — to be updated

## Phase 1 — Extract a Stable Video Backend API (keep everything working)

**Objective**: Make video generation callable via a small library surface that does not depend on CLI/UI code.

- [x] Create a new package for video orchestration (example):
  - [x] `src/sip_videogen/video/__init__.py`
  - [x] `src/sip_videogen/video/pipeline.py`
- [x] Move orchestration logic out of `cli.py` into the new API (minimal refactor):
  - [x] Script development (Showrunner agents) → return `VideoScript`
  - [x] Reference image generation → return list of `GeneratedAsset` reference images
  - [x] Provider selection → keep using `VideoProvider` + `VideoGeneratorFactory`
  - [x] Clip generation → `generate_all_video_clips(...)`
  - [x] Assembly → `FFmpegAssembler` (optional, but keep available)
- [x] Ensure the new API is non-interactive:
  - [x] No Typer, no questionary, no "press y to continue"
  - [x] Any confirmation/cost logic should live outside the library layer
- [x] Add unit tests for the new API (mock external calls):
  - [x] "happy path" test that calls pipeline with mocks and verifies calls/outputs
  - [x] provider selection test uses `VideoGeneratorFactory` correctly
- [x] Run verification:
  - [x] `python -m pytest` — 523 passed (18 new tests added)
  - [x] `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"` — ✅ passes

**Optional (future-proofing)** — avoid config.json overwrite risk:
- [ ] Update `UserPreferences.save()` to **merge** into existing `~/.sip-videogen/config.json` instead of overwriting (preserve `api_keys` and update settings). Only do this if you can do it safely and with tests.

## Phase 2 — Remove the CLI Product Surface (keep video infra + Brand Studio intact)

**Objective**: Remove CLI entrypoints and interactive flows while keeping underlying modules.

- [x] Packaging cleanup:
  - [x] Remove `[project.scripts]` entries from `pyproject.toml`:
    - [x] `sip-videogen = "sip_videogen.cli:app"`
    - [x] `sipvid = "sip_videogen.cli:app"`
  - [x] Remove `src/sip_videogen/__main__.py` (or repurpose to a helpful message; simplest is delete).
- [x] Delete legacy CLI files:
  - [x] Delete `src/sip_videogen/cli.py`
  - [x] Delete `start.sh`
- [ ] Delete CLI-only config wizard:
  - [ ] Delete `src/sip_videogen/config/setup.py`
- [ ] Delete pipx updater / CLI-only updater package:
  - [ ] Delete `src/sip_videogen/utils/` (including `src/sip_videogen/utils/__init__.py` + `src/sip_videogen/utils/updater.py`)
- [ ] Remove CLI-only dependencies from `pyproject.toml` after confirming no other usage:
  - [ ] `typer[all]`
  - [ ] `questionary`
- [ ] Remove/update tests that depend on the CLI:
  - [ ] Delete or rewrite `tests/test_cli.py` (should not exist after CLI removal)
  - [ ] Delete or rewrite `tests/test_setup.py` (tests `sip_videogen.config.setup`)
  - [ ] Delete or rewrite `tests/test_updater.py` (tests `sip_videogen.utils.updater` / pipx flow)
- [ ] Documentation cleanup:
  - [ ] Remove pipx install/run instructions from `README.md` (keep Brand Studio instructions)
  - [ ] Update `scripts/publish.sh` (remove pipx references or archive the script)
  - [ ] Ensure `README.md` no longer advertises `sipvid`/CLI usage
- [ ] Verification (must pass):
  - [ ] `python -m pytest`
  - [ ] `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`
  - [ ] (Recommended) `python -m sip_videogen.studio` launches in dev

## Phase 3 — Remove Brand Kit Workflow (and associated models/agents/tests)

**Objective**: Remove Brand Kit as a feature while keeping Brand Studio + Advisor stable.

- [ ] Remove Brand Kit implementation modules:
  - [ ] Delete `src/sip_videogen/brand_kit/**`
  - [ ] Delete brand-kit-only agent(s) (e.g., `src/sip_videogen/agents/brand_designer.py`) if unused
  - [ ] Delete brand-kit-only models (e.g., `src/sip_videogen/models/brand_kit.py`) if unused
- [ ] Remove Brand Kit migration if not needed:
  - [ ] Delete `src/sip_videogen/brands/migration.py`
  - [ ] Update `src/sip_videogen/brands/__init__.py` to remove migration imports/exports
  - [ ] Delete or rewrite `tests/test_brands_migration.py`
- [ ] Remove Brand Kit exports/imports:
  - [ ] Update `src/sip_videogen/models/__init__.py` to stop exporting brand-kit types
  - [ ] Update `src/sip_videogen/agents/__init__.py` to stop exporting Brand Kit planner
- [ ] Remove Brand Kit related tests:
  - [ ] Rewrite `tests/test_brand_integration.py` to remove `sip_videogen.brand_kit.*` imports and keep brand-only workflow coverage
  - [ ] Delete or rewrite any remaining brand-kit model tests (search via `rg "brand_kit" tests/`)
- [ ] NanoBanana decision:
  - [ ] If Brand Kit is removed and NanoBanana is unused, delete `src/sip_videogen/generators/nano_banana_generator.py` and remove it from `src/sip_videogen/generators/__init__.py`
- [ ] Verification (must pass):
  - [ ] `python -m pytest`
  - [ ] `python -c "import sip_videogen.studio.bridge; import sip_videogen.advisor.agent"`
  - [ ] (Recommended) `python -m sip_videogen.studio` still launches

## Phase 4 — Final Hardening (focus + future maintainability)

- [ ] Add/keep a lightweight developer-facing “video backend smoke test”:
  - [ ] A unit test that imports `sip_videogen.video.pipeline` and instantiates a generator via `VideoGeneratorFactory` (mocked credentials).
- [ ] Confirm Brand Studio packaging remains functional:
  - [ ] `BrandStudio.spec` still includes required frontend dist + prompts
  - [ ] `pyinstaller BrandStudio.spec` works (or confirm your existing release process)
- [ ] Ensure “video infra retained” is visible:
  - [ ] Add a short README section like “Video Generation Backend (internal)” describing the new library entrypoint and noting that the CLI was removed intentionally.

---

## Acceptance Criteria (Definition of Done)

- [ ] Brand Studio runs and is unaffected (dev launch + import smoke tests).
- [ ] No CLI entrypoints remain in packaging (`pyproject.toml` scripts removed; no `sip_videogen.cli`).
- [ ] No pipx instructions/updater code remains.
- [ ] Brand Kit workflow removed (code + tests + docs).
- [ ] Video generation infrastructure remains importable and tested:
  - [ ] Providers still selectable via `VideoProvider` + `VideoGeneratorFactory`
  - [ ] Generators + FFmpeg assembler still exist and tests pass
