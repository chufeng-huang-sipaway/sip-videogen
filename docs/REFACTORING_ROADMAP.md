# Code Review & Refactoring Roadmap

> **Generated:** 2026-01-06
> **Codebase:** sip-videogen v0.8.5
> **Scope:** ~16,000 lines Python + React/TypeScript frontend

## Executive Summary

This document outlines refactoring opportunities identified during a comprehensive code review. The codebase has good overall architecture, but rapid feature development has created technical debt in several areas. We've identified **~1,500+ lines of duplicated code** that can be consolidated, along with structural issues that will improve maintainability.

### Key Metrics

| Metric | Value |
|--------|-------|
| Total Python Files | 112 |
| Total Python Lines | ~16,000 |
| Duplicated Code | ~1,500+ lines |
| God Modules | 2 (models.py, validation.py) |
| Storage Modules with CRUD Duplication | 4 |

---

## Table of Contents

1. [High Priority - Critical Refactoring](#high-priority---critical-refactoring)
2. [Medium Priority - Structural Improvements](#medium-priority---structural-improvements)
3. [Low Priority - Quick Wins](#low-priority---quick-wins)
4. [Frontend Improvements](#frontend-improvements)
5. [Execution Plan](#execution-plan)
6. [Appendix: Detailed File References](#appendix-detailed-file-references)

---

## High Priority - Critical Refactoring

### 1. God Module: `brands/models.py`

**Location:** `src/sip_videogen/brands/models.py`
**Size:** 1,106 lines, 43+ classes
**Severity:** 🔴 Critical

#### Problem

Single file containing models for 4 different domains - violates Single Responsibility Principle.

#### Current Structure

```
brands/models.py
├── Brand models (BrandSummary, BrandIdentityFull, ColorDefinition, TypographyRule,
│                 VisualIdentity, VoiceGuidelines, AudienceProfile, etc.)
├── Product models (ProductSummary, ProductFull, ProductAttribute,
│                   PackagingTextElement, PackagingTextDescription)
├── Project models (ProjectStatus, ProjectSummary, ProjectFull, ProjectIndex)
└── StyleReference models (StyleReferenceSummary, StyleReferenceFull, StyleSpec,
                          CanvasSpec, MessageSpec, GeometrySpec, AppearanceSpec,
                          ContentSpec, ConstraintSpec, LayoutElement, etc.)
```

#### Recommended Structure

```
brands/models/
├── __init__.py              # Re-exports all models for backward compatibility
├── brand.py                 # Brand* classes (~300 lines)
│   ├── BrandSummary
│   ├── BrandIdentityFull
│   ├── BrandCoreIdentity
│   ├── ColorDefinition
│   ├── TypographyRule
│   ├── VisualIdentity
│   ├── VoiceGuidelines
│   ├── AudienceProfile
│   ├── CompetitivePositioning
│   ├── BrandIndexEntry
│   └── BrandIndex
├── product.py               # Product* classes (~200 lines)
│   ├── ProductAttribute
│   ├── ProductSummary
│   ├── ProductFull
│   ├── ProductIndex
│   ├── PackagingTextElement
│   └── PackagingTextDescription
├── project.py               # Project* classes (~150 lines)
│   ├── ProjectStatus
│   ├── ProjectSummary
│   ├── ProjectFull
│   └── ProjectIndex
└── style_reference.py       # StyleReference* + spec classes (~400 lines)
    ├── StyleSpec
    ├── CanvasSpec
    ├── MessageSpec
    ├── GeometrySpec
    ├── AppearanceSpec
    ├── ContentSpec
    ├── ConstraintSpec
    ├── LayoutElement
    ├── InteractionSpec
    ├── ProductSlot
    ├── VisualSceneSpec
    ├── LayoutStructureSpec
    ├── StyleReferenceConstraintsSpec
    ├── StyleReferenceAnalysis*
    ├── StyleReferenceSummary
    ├── StyleReferenceFull
    └── StyleReferenceIndex
```

#### Migration Strategy

1. Create `brands/models/` directory
2. Move classes to appropriate files
3. Update `brands/models/__init__.py` to re-export everything:
   ```python
   from .brand import BrandSummary, BrandIdentityFull, ...
   from .product import ProductSummary, ProductFull, ...
   from .project import ProjectSummary, ProjectFull, ...
   from .style_reference import StyleReferenceSummary, ...

   __all__ = [...]
   ```
4. No changes needed to importing modules (backward compatible)

#### Impact

- Better code organization and navigation
- Reduced merge conflicts
- Easier to understand domain boundaries
- Faster IDE indexing

---

### 2. Video Generator Duplication

**Locations:**
- `src/sip_videogen/generators/video_generator.py` (1,152 lines)
- `src/sip_videogen/generators/kling_generator.py` (696 lines)
- `src/sip_videogen/generators/sora_generator.py` (511 lines)

**Duplicated Lines:** ~525+
**Severity:** 🔴 Critical

#### Duplicated Methods Analysis

| Method | video_generator.py | kling_generator.py | sora_generator.py |
|--------|-------------------|-------------------|-------------------|
| `_build_flow_context()` | Lines 297-342 | Lines 529-564 | Lines 340-375 |
| `_build_scene_reference_map()` | Lines 1096-1131 | Lines 660-696 | Lines 475-511 |
| `GenerationResult` dataclass | Lines 1134-1152 | Lines 56-72 | Lines 55-71 |
| `generate_all_video_clips()` | Lines 891-1094 | Lines 566-658 | Lines 377-473 |
| Aspect ratio validation | Lines 125-131 | Lines 199-206 | Lines 193-200 |
| `_build_prompt()` signature | Lines 440-486 | Lines 495-527 | Lines 306-338 |

#### Recommended Refactoring

**Step 1: Create shared `GenerationResult` dataclass**

```python
# generators/result.py (new file)
from dataclasses import dataclass
from sip_videogen.models.assets import GeneratedAsset

@dataclass
class GenerationResult:
    """Result of batch video generation."""
    successful: list[GeneratedAsset]
    failed_scenes: list[int]
    total_scenes: int

    @property
    def success_rate(self) -> float:
        if self.total_scenes == 0:
            return 0.0
        return len(self.successful) / self.total_scenes * 100

    @property
    def all_succeeded(self) -> bool:
        return len(self.failed_scenes) == 0
```

**Step 2: Enhance `base.py` with common implementations**

```python
# generators/base.py (enhanced)
class BaseVideoGenerator(ABC):
    # ... existing code ...

    def _build_flow_context(
        self,
        scene_num: int,
        total_scenes: int | None
    ) -> str:
        """Build flow context for scene positioning."""
        if total_scenes is None or total_scenes <= 1:
            return ""

        if scene_num == 1:
            position = "FIRST"
            guidance = "Establish setting, introduce elements"
        elif scene_num == total_scenes:
            position = "LAST"
            guidance = "Conclude narrative, final imagery"
        else:
            position = "MIDDLE"
            guidance = "Continue narrative flow"

        return f"[FLOW: {position} scene ({scene_num}/{total_scenes}) - {guidance}]"

    def _build_scene_reference_map(
        self,
        script: VideoScript,
        reference_images: list[GeneratedAsset] | None,
    ) -> dict[int, list[GeneratedAsset]]:
        """Map scene numbers to their relevant reference images."""
        if not reference_images:
            return {}

        # Build element_id -> image mapping
        element_to_image: dict[str, GeneratedAsset] = {}
        for img in reference_images:
            if img.element_id:
                element_to_image[img.element_id] = img

        # Build scene -> references mapping
        scene_refs: dict[int, list[GeneratedAsset]] = {}
        for scene in script.scenes:
            refs = []
            for elem_id in scene.shared_element_ids or []:
                if elem_id in element_to_image:
                    refs.append(element_to_image[elem_id])
            if refs:
                scene_refs[scene.scene_number] = refs[:self.MAX_REFERENCE_IMAGES]

        return scene_refs

    def _validate_aspect_ratio(self, aspect_ratio: str, scene_num: int) -> str:
        """Validate and potentially adjust aspect ratio for this provider."""
        from sip_videogen.models.aspect_ratio import (
            validate_aspect_ratio,
            get_supported_ratio,
        )
        validated = validate_aspect_ratio(aspect_ratio)
        actual, was_fallback = get_supported_ratio(validated, self.PROVIDER_NAME)
        if was_fallback:
            logger.warning(
                f"Scene {scene_num}: Using fallback ratio {actual.value} "
                f"(requested: {aspect_ratio})"
            )
        return actual.value
```

**Step 3: Use Template Method pattern for `generate_all_video_clips()`**

```python
# generators/base.py (continued)
class BaseVideoGenerator(ABC):
    async def generate_all_video_clips(
        self,
        script: VideoScript,
        output_dir: str,
        reference_images: list[GeneratedAsset] | None = None,
        max_concurrent: int = 3,
        show_progress: bool = True,
    ) -> GenerationResult:
        """Template method for batch generation."""
        scenes = script.scenes
        total_scenes = len(scenes)
        scene_refs = self._build_scene_reference_map(script, reference_images)

        results: list[GeneratedAsset] = []
        failed_scenes: list[int] = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(scene: SceneAction) -> GeneratedAsset | None:
            async with semaphore:
                try:
                    return await self.generate_video_clip(
                        scene=scene,
                        output_dir=output_dir,
                        reference_images=scene_refs.get(scene.scene_number),
                        total_scenes=total_scenes,
                        script=script,
                    )
                except Exception as e:
                    logger.error(f"Scene {scene.scene_number} failed: {e}")
                    return None

        # Provider-specific progress display can be overridden
        tasks = [generate_with_semaphore(scene) for scene in scenes]
        outputs = await asyncio.gather(*tasks)

        for scene, output in zip(scenes, outputs):
            if output:
                results.append(output)
            else:
                failed_scenes.append(scene.scene_number)

        return GenerationResult(
            successful=sorted(results, key=lambda x: x.scene_number or 0),
            failed_scenes=failed_scenes,
            total_scenes=total_scenes,
        )
```

#### Impact

- Eliminates ~400+ lines of duplication
- Single point of maintenance for core logic
- Easier to add new providers (just implement `generate_video_clip()`)
- Consistent behavior across all providers

---

### 3. Storage Layer CRUD Duplication

**Locations:**
- `src/sip_videogen/brands/storage/brand_storage.py`
- `src/sip_videogen/brands/storage/product_storage.py`
- `src/sip_videogen/brands/storage/project_storage.py`
- `src/sip_videogen/brands/storage/style_reference_storage.py`

**Duplicated Lines:** ~300+
**Severity:** 🔴 Critical

#### Current Pattern (Repeated 4 Times)

Each storage module implements identical CRUD operations:

```python
# This pattern appears in all 4 storage modules:

def create_X(brand_slug: str, data: XFull) -> str:
    dir = get_X_dir(brand_slug, data.slug)
    dir.mkdir(parents=True, exist_ok=True)
    write_atomically(dir / "X.json", data.to_summary().model_dump_json(indent=2))
    write_atomically(dir / "X_full.json", data.model_dump_json(indent=2))
    idx = load_X_index(brand_slug)
    idx.add(data.to_summary())
    save_X_index(brand_slug, idx)
    return data.slug

def load_X(brand_slug: str, slug: str) -> XFull | None:
    path = get_X_dir(brand_slug, slug) / "X_full.json"
    if not path.exists():
        return None
    try:
        return XFull.model_validate_json(path.read_text())
    except Exception as e:
        logger.warning(f"Failed to load X: {e}")
        return None

def load_X_summary(brand_slug: str, slug: str) -> XSummary | None:
    # Similar pattern...

def save_X(brand_slug: str, data: XFull) -> None:
    # Similar pattern...

def delete_X(brand_slug: str, slug: str) -> bool:
    # Similar pattern...

def list_X(brand_slug: str) -> list[XSummary]:
    # Similar pattern...
```

#### Recommended Refactoring

**Create a generic `EntityStorage` base class:**

```python
# brands/storage/entity_storage.py (new file)
from typing import TypeVar, Generic, Callable
from pathlib import Path
from pydantic import BaseModel

TSummary = TypeVar("TSummary", bound=BaseModel)
TFull = TypeVar("TFull", bound=BaseModel)
TIndex = TypeVar("TIndex", bound=BaseModel)

class EntityStorage(Generic[TSummary, TFull, TIndex]):
    """Generic storage for brand-related entities."""

    def __init__(
        self,
        entity_name: str,
        get_entity_dir: Callable[[str, str], Path],
        get_index_path: Callable[[str], Path],
        summary_class: type[TSummary],
        full_class: type[TFull],
        index_class: type[TIndex],
        get_summary: Callable[[TFull], TSummary],
        add_to_index: Callable[[TIndex, TSummary], None],
        remove_from_index: Callable[[TIndex, str], None],
    ):
        self.entity_name = entity_name
        self.get_entity_dir = get_entity_dir
        self.get_index_path = get_index_path
        self.summary_class = summary_class
        self.full_class = full_class
        self.index_class = index_class
        self.get_summary = get_summary
        self.add_to_index = add_to_index
        self.remove_from_index = remove_from_index

    def create(self, brand_slug: str, entity: TFull) -> str:
        """Create a new entity."""
        slug = getattr(entity, "slug")
        entity_dir = self.get_entity_dir(brand_slug, slug)
        entity_dir.mkdir(parents=True, exist_ok=True)

        summary = self.get_summary(entity)
        write_atomically(
            entity_dir / f"{self.entity_name}.json",
            summary.model_dump_json(indent=2)
        )
        write_atomically(
            entity_dir / f"{self.entity_name}_full.json",
            entity.model_dump_json(indent=2)
        )

        idx = self._load_index(brand_slug)
        self.add_to_index(idx, summary)
        self._save_index(brand_slug, idx)

        logger.info(f"Created {self.entity_name}: {slug}")
        return slug

    def load(self, brand_slug: str, entity_slug: str) -> TFull | None:
        """Load full entity data."""
        path = self.get_entity_dir(brand_slug, entity_slug) / f"{self.entity_name}_full.json"
        if not path.exists():
            return None
        try:
            return self.full_class.model_validate_json(path.read_text())
        except Exception as e:
            logger.warning(f"Failed to load {self.entity_name} {entity_slug}: {e}")
            return None

    def load_summary(self, brand_slug: str, entity_slug: str) -> TSummary | None:
        """Load entity summary only."""
        path = self.get_entity_dir(brand_slug, entity_slug) / f"{self.entity_name}.json"
        if not path.exists():
            return None
        try:
            return self.summary_class.model_validate_json(path.read_text())
        except Exception as e:
            logger.warning(f"Failed to load {self.entity_name} summary {entity_slug}: {e}")
            return None

    def save(self, brand_slug: str, entity: TFull) -> None:
        """Save entity (update existing)."""
        slug = getattr(entity, "slug")
        entity_dir = self.get_entity_dir(brand_slug, slug)

        summary = self.get_summary(entity)
        write_atomically(
            entity_dir / f"{self.entity_name}.json",
            summary.model_dump_json(indent=2)
        )
        write_atomically(
            entity_dir / f"{self.entity_name}_full.json",
            entity.model_dump_json(indent=2)
        )

        idx = self._load_index(brand_slug)
        self.add_to_index(idx, summary)
        self._save_index(brand_slug, idx)

        logger.debug(f"Saved {self.entity_name}: {slug}")

    def delete(self, brand_slug: str, entity_slug: str) -> bool:
        """Delete an entity."""
        entity_dir = self.get_entity_dir(brand_slug, entity_slug)
        if not entity_dir.exists():
            return False

        shutil.rmtree(entity_dir)

        idx = self._load_index(brand_slug)
        self.remove_from_index(idx, entity_slug)
        self._save_index(brand_slug, idx)

        logger.info(f"Deleted {self.entity_name}: {entity_slug}")
        return True

    def list_all(self, brand_slug: str) -> list[TSummary]:
        """List all entity summaries."""
        idx = self._load_index(brand_slug)
        return list(getattr(idx, f"{self.entity_name}s", []))

    def _load_index(self, brand_slug: str) -> TIndex:
        """Load or create index."""
        path = self.get_index_path(brand_slug)
        if path.exists():
            try:
                return self.index_class.model_validate_json(path.read_text())
            except Exception as e:
                logger.warning(f"Failed to load {self.entity_name} index: {e}")
        return self.index_class()

    def _save_index(self, brand_slug: str, index: TIndex) -> None:
        """Save index atomically."""
        path = self.get_index_path(brand_slug)
        write_atomically(path, index.model_dump_json(indent=2))
```

**Usage example:**

```python
# brands/storage/product_storage.py (simplified)
from .entity_storage import EntityStorage
from ..models import ProductSummary, ProductFull, ProductIndex

product_storage = EntityStorage[ProductSummary, ProductFull, ProductIndex](
    entity_name="product",
    get_entity_dir=get_product_dir,
    get_index_path=get_product_index_path,
    summary_class=ProductSummary,
    full_class=ProductFull,
    index_class=ProductIndex,
    get_summary=lambda p: p.to_summary(),
    add_to_index=lambda idx, s: idx.products.append(s),
    remove_from_index=lambda idx, slug: idx.products.remove(
        next(p for p in idx.products if p.slug == slug)
    ),
)

# Export functions for backward compatibility
create_product = product_storage.create
load_product = product_storage.load
load_product_summary = product_storage.load_summary
save_product = product_storage.save
delete_product = product_storage.delete
list_products = product_storage.list_all
```

#### Impact

- Reduces 4 modules (~800 lines) to 1 base class + 4 thin wrappers (~200 lines)
- Consistent behavior guaranteed across all entity types
- Easier to add new entity types
- Single place to fix bugs or add features (e.g., backup, validation)

---

### 4. `advisor/validation.py` - Too Many Responsibilities

**Location:** `src/sip_videogen/advisor/validation.py`
**Size:** 1,219 lines
**Severity:** 🔴 Critical

#### Current Responsibilities (5 Different Concerns)

1. **Metrics Collection** (Lines 40-164)
   - `ProductMetric`, `GenerationMetrics` classes
   - `_write_metrics()`, metrics file I/O

2. **Validation Models** (Lines 165-350)
   - `ReferenceValidationResult`
   - `ProductValidationResult`
   - `MultiProductValidationResult`

3. **Image Validation Logic** (Lines 351-570)
   - `validate_reference_identity()` (~130 lines)
   - `validate_multi_product_identity()` (~87 lines)

4. **Generation with Validation** (Lines 572-840)
   - `generate_with_validation()` (~216 lines)
   - Complex retry loop with prompt improvement

5. **Prompt Improvement** (Lines 841-1219)
   - `_improve_prompt_for_identity()` (~50 lines)
   - `generate_with_multi_validation()` (~328 lines)
   - `_improve_multi_product_prompt()` (~47 lines)
   - Prompt templates (`_VALIDATOR_PROMPT`, `_MULTI_PRODUCT_VALIDATOR_PROMPT`)

#### Recommended Structure

```
advisor/validation/
├── __init__.py              # Re-exports public API
├── metrics.py               # Metrics collection & persistence (~150 lines)
│   ├── ProductMetric
│   ├── GenerationMetrics
│   ├── write_metrics()
│   └── cleanup_attempt_files()
├── models.py                # Validation result models (~200 lines)
│   ├── ReferenceValidationResult
│   ├── ProductValidationResult
│   └── MultiProductValidationResult
├── validator.py             # Core validation logic (~250 lines)
│   ├── validate_reference_identity()
│   └── validate_multi_product_identity()
├── generator.py             # Generation with validation (~400 lines)
│   ├── generate_with_validation()
│   └── generate_with_multi_validation()
└── prompts.py               # Prompt templates & improvement (~200 lines)
    ├── VALIDATOR_PROMPT
    ├── MULTI_PRODUCT_VALIDATOR_PROMPT
    ├── improve_prompt_for_identity()
    └── improve_multi_product_prompt()
```

#### Long Function Decomposition

The `generate_with_validation()` function (216 lines) should be broken into:

```python
# advisor/validation/generator.py

async def generate_with_validation(...) -> GenerationWithValidationResult:
    """Main entry point for validated generation."""
    attempts = []

    for attempt_num in range(max_attempts):
        result = await _execute_generation_attempt(
            attempt_num, prompt, reference_image, ...
        )
        attempts.append(result)

        if _should_accept_result(result, min_score):
            break

        if attempt_num < max_attempts - 1:
            prompt = await _improve_prompt(prompt, result, ...)

    return _select_best_result(attempts)

async def _execute_generation_attempt(...) -> AttemptResult:
    """Execute a single generation + validation attempt."""
    # ~50 lines

def _should_accept_result(result: AttemptResult, min_score: float) -> bool:
    """Determine if result meets acceptance criteria."""
    # ~10 lines

async def _improve_prompt(...) -> str:
    """Improve prompt based on validation feedback."""
    # ~30 lines

def _select_best_result(attempts: list[AttemptResult]) -> GenerationWithValidationResult:
    """Select the best result from all attempts."""
    # ~30 lines
```

#### Impact

- Each module under 300 lines with clear single purpose
- Easier to test individual components
- Clearer dependency graph
- Easier onboarding for new developers

---

## Medium Priority - Structural Improvements

### 5. Agent Architecture Duplication

**Duplicated Lines:** ~600+
**Severity:** 🟡 Medium

#### Issue A: Prompt Loading Pattern

**Files Affected:** 10+ agent files

Every agent file duplicates this pattern:

```python
# Repeated in: screenwriter.py, music_director.py, brand_strategist.py,
# brand_voice.py, visual_designer.py, brand_guardian.py, production_designer.py,
# continuity_supervisor.py, image_reviewer.py, prompt_repair.py

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_SCREENWRITER_PROMPT_PATH = _PROMPTS_DIR / "screenwriter.md"

def _load_prompt() -> str:
    if _SCREENWRITER_PROMPT_PATH.exists():
        return _SCREENWRITER_PROMPT_PATH.read_text()
    return """Fallback inline prompt..."""
```

**Recommended Fix:**

```python
# agents/prompt_loader.py (new file)
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"

def load_agent_prompt(agent_name: str, fallback: str = "") -> str:
    """Load agent prompt from markdown file.

    Args:
        agent_name: Name of the agent (e.g., "screenwriter")
        fallback: Fallback prompt if file doesn't exist

    Returns:
        Prompt text from file or fallback
    """
    prompt_path = _PROMPTS_DIR / f"{agent_name}.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    if fallback:
        return fallback
    raise FileNotFoundError(f"No prompt file found for agent: {agent_name}")
```

**Usage:**

```python
# agents/screenwriter.py (simplified)
from .prompt_loader import load_agent_prompt

_FALLBACK_PROMPT = """You are a screenwriter..."""

screenwriter_agent = Agent(
    name="Screenwriter",
    instructions=load_agent_prompt("screenwriter", _FALLBACK_PROMPT),
    output_type=ScreenwriterOutput,
)
```

#### Issue B: Progress Tracking Hooks

**Files Affected:**
- `agents/brand_director.py` (BrandProgressTrackingHooks)
- `agents/showrunner.py` (ProgressTrackingHooks)
- `advisor/hooks.py` (AdvisorHooks)

All three implement nearly identical:
- `__init__` with callback
- `_report()` method
- `_tool_descriptions` dict
- Hook methods: `on_tool_start`, `on_tool_end`, `on_llm_start`

**Recommended Fix:**

```python
# agents/progress.py (new file)
from agents import RunHooks

class BaseProgressTracker(RunHooks):
    """Base class for progress tracking hooks."""

    def __init__(
        self,
        callback: Callable[[ProgressEvent], None] | None = None,
        tool_descriptions: dict[str, str] | None = None,
    ):
        self.callback = callback
        self._tool_descriptions = tool_descriptions or {}

    def _report(self, event: ProgressEvent) -> None:
        if self.callback:
            self.callback(event)

    async def on_tool_start(self, context, agent, tool) -> None:
        desc = self._tool_descriptions.get(tool.name, f"Running {tool.name}")
        self._report(ProgressEvent(type="tool_start", message=desc))

    async def on_tool_end(self, context, agent, tool, result) -> None:
        self._report(ProgressEvent(type="tool_end", tool=tool.name))

    async def on_llm_start(self, context, agent) -> None:
        self._report(ProgressEvent(type="thinking", agent=agent.name))
```

#### Issue C: Brand Context Building

**Files Affected:**
- `brand_strategist.py` (lines 64-85)
- `brand_voice.py` (lines 65-86)
- `visual_designer.py` (lines 64-85)
- `brand_guardian.py` (lines 76-99)

All repeat:

```python
if existing_brand_slug:
    set_active_brand(existing_brand_slug)
    brand_context = build_brand_context(existing_brand_slug)
    context_section = f"## Existing Brand Context\n\n{brand_context}\n\n---\n\n"
else:
    context_section = "## New Brand Creation\n\n...\n\n---\n\n"
```

**Recommended Fix:**

```python
# brands/context_helpers.py (new file)
def get_brand_context_section(existing_brand_slug: str | None = None) -> str:
    """Get formatted brand context section for agent prompts."""
    if existing_brand_slug:
        set_active_brand(existing_brand_slug)
        context = build_brand_context(existing_brand_slug)
        return f"## Existing Brand Context\n\n{context}\n\n---\n\n"
    return (
        "## New Brand Creation\n\n"
        "No existing brand context. Creating from scratch based on concept.\n\n"
        "---\n\n"
    )
```

---

### 6. Context Builder Consolidation

**Location:** `src/sip_videogen/brands/context.py`
**Size:** 734 lines
**Severity:** 🟡 Medium

#### Problem

5 different context builder classes in one file:
- `BrandContextBuilder`
- `ProductContextBuilder`
- `ProjectContextBuilder`
- `HierarchicalContextBuilder`
- `StyleReferenceContextBuilder`

#### Recommended Structure

```
brands/context/
├── __init__.py                    # Re-exports all builders
├── base.py                        # Shared utilities
├── brand_context.py               # BrandContextBuilder
├── product_context.py             # ProductContextBuilder
├── project_context.py             # ProjectContextBuilder
├── hierarchical_context.py        # HierarchicalContextBuilder
└── style_reference_context.py     # StyleReferenceContextBuilder
```

---

### 7. Inconsistent Error Handling

**Severity:** 🟡 Medium

#### Issues Found

1. **Broad Exception Catches** (14 occurrences in storage modules)
   ```python
   # BAD: Loses specific error context
   except Exception as e:
       logger.warning(f"Failed to load: {e}")
       return None
   ```

2. **Inconsistent Retry Decorators**
   - Some agents have `@retry` decorator
   - Most agents have no retry logic

3. **Missing Input Validation**
   - `brand_director.py`, `showrunner.py` validate inputs
   - Other agents skip validation entirely

#### Recommended Standards

```python
# Create standard retry decorator
# config/retry.py
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

def agent_retry(max_attempts: int = 3):
    """Standard retry decorator for agent functions."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((AgentsException, TimeoutError, ConnectionError)),
        reraise=True,
    )

# Usage:
@agent_retry(max_attempts=3)
async def develop_brand(...):
    ...
```

---

### 8. Path Safety Vulnerabilities

**Severity:** 🟡 Medium (Security)

#### Issues Found

Image upload functions don't validate filenames for path traversal:

- `product_storage.py` lines 197-228: `add_product_image()`
- `style_reference_storage.py` lines 211-246: `add_style_reference_image()`

```python
# VULNERABLE: No validation of filename
(imd / filename).write_bytes(data)
```

#### Recommended Fix

```python
# Use existing safe_resolve_path from base.py
from .base import safe_resolve_path

def add_product_image(brand_slug: str, product_slug: str, filename: str, data: bytes) -> str:
    # Validate filename
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError(f"Invalid filename: {filename}")

    # Sanitize filename
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")

    imd = get_product_images_dir(brand_slug, product_slug)
    imd.mkdir(parents=True, exist_ok=True)

    # Use safe path resolution
    target_path = safe_resolve_path(imd, safe_filename)
    target_path.write_bytes(data)

    return f"products/{product_slug}/images/{safe_filename}"
```

---

## Low Priority - Quick Wins

### 9. Consolidate Constants Files

**Severity:** 🟢 Low

#### Current State

Two separate constants files:

```
sip_videogen/constants.py
├── ASSET_CATEGORIES
├── ALLOWED_IMAGE_EXTS
├── ALLOWED_VIDEO_EXTS
└── MIME_TYPES

sip_videogen/config/constants.py
├── RESOLUTIONS
├── Timeouts (class)
└── Limits (class)
```

#### Recommendation

Merge into single `config/constants.py` organized by domain:

```python
# config/constants.py

# === File Types ===
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_VIDEO_EXTS = {".mp4", ".mov", ".webm"}
MIME_TYPES = {...}

# === Asset Categories ===
ASSET_CATEGORIES = ["logo", "packaging", "lifestyle", ...]

# === Resolutions ===
RESOLUTIONS = {...}

# === Timeouts ===
class Timeouts:
    HTTP_REQUEST = 30
    VIDEO_GENERATION = 300
    ...

# === Limits ===
class Limits:
    MAX_CONCURRENT_GENERATIONS = 5
    MAX_REFERENCE_IMAGES = 4
    ...
```

---

### 10. Remove Deprecated Shim

**Location:** `src/sip_videogen/brands/tools.py`
**Size:** 58 lines

```python
# DEPRECATED: This module is a backwards-compatibility shim
```

#### Recommendation

1. Search for imports of `brands.tools`
2. Update to import from `advisor.tools` directly
3. Remove `brands/tools.py` in next minor version
4. Add deprecation warning in current version:

```python
# brands/tools.py
import warnings
warnings.warn(
    "sip_videogen.brands.tools is deprecated. "
    "Import from sip_videogen.advisor.tools instead.",
    DeprecationWarning,
    stacklevel=2
)
```

---

### 11. Misplaced Utility

**Location:** `src/sip_videogen/brands/text_utils.py`
**Size:** 15 lines

Contains single function `escape_text_for_prompt()` which is not brand-specific.

#### Recommendation

Move to `utils/text_utils.py`:

```python
# utils/text_utils.py
def escape_text_for_prompt(text: str) -> str:
    """Escape special characters in text for use in prompts."""
    ...
```

Update imports in affected files.

---

### 12. Address Circular Dependencies

**Severity:** 🟢 Low

#### Problem

Multiple `__init__.py` files use `__getattr__` for lazy loading to avoid circular imports:

- `brands/__init__.py` (lines 138-149)
- `advisor/__init__.py` (lines 9-15)
- `studio/services/__init__.py` (lines 35-72)

#### Root Cause

Circular dependencies between:
- `brands.tools` → `advisor.tools` → `brands`
- `advisor` → `brands` → `advisor`

#### Long-term Fix

1. Identify circular import chains
2. Extract shared types to separate modules
3. Use dependency injection where appropriate
4. Remove lazy loading hacks once dependencies are clean

---

## Frontend Improvements

### 13. Duplicated PyWebView Readiness Checks

**Severity:** 🟡 Medium

#### Problem

Pattern repeated 50+ times across contexts and hooks:

```typescript
const ready = await waitForPyWebViewReady()
if (!ready) throw new Error('Not running in PyWebView')
```

#### Recommendation

```typescript
// hooks/useBridgeCall.ts
export function useBridgeCall<T>(
  bridgeFn: () => Promise<T>,
  options?: { onError?: (e: Error) => void }
) {
  return useCallback(async () => {
    const ready = await waitForPyWebViewReady();
    if (!ready) {
      const error = new Error('Not running in PyWebView');
      options?.onError?.(error);
      throw error;
    }
    return bridgeFn();
  }, [bridgeFn, options?.onError]);
}
```

---

### 14. Context Pattern Duplication

**Severity:** 🟡 Medium

#### Problem

`ProductContext`, `ProjectContext`, `StyleReferenceContext` duplicate:
- Identical state structure
- Identical refresh logic
- Identical CRUD wrappers

#### Recommendation

```typescript
// hooks/useEntityManager.ts
export function useEntityManager<T extends { slug: string }>(
  entityName: string,
  loadFn: () => Promise<T[]>,
  deps: unknown[]
) {
  const [items, setItems] = useState<T[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const ready = await waitForPyWebViewReady();
      if (!ready) {
        setItems([]);
        return;
      }
      const result = await loadFn();
      setItems(result);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setIsLoading(false);
    }
  }, deps);

  return { items, isLoading, error, refresh, setItems };
}
```

---

### 15. File Utils Not Used Consistently

**Severity:** 🟢 Low

#### Problem

`file-utils.ts` exports utilities but several components manually implement FileReader:
- `useChat.ts`
- `BrandBrainCard.tsx`
- `useAssets.ts`

#### Recommendation

Refactor to use `processImageFiles()` and `processDocumentFiles()` from `file-utils.ts`.

---

## Execution Plan

### Phase 1: Foundation (Week 1-2)

**Goal:** Split god modules for cleaner imports

| Task | Files | Risk | Effort |
|------|-------|------|--------|
| Split `brands/models.py` | 1 → 5 | Low | Medium |
| Update imports (automated) | ~30 | Low | Low |
| Run tests, fix breakages | - | Low | Low |

### Phase 2: Generators (Week 2-3)

**Goal:** Eliminate generator duplication

| Task | Files | Risk | Effort |
|------|-------|------|--------|
| Create `GenerationResult` in `result.py` | 1 new | Low | Low |
| Add common methods to `base.py` | 1 | Low | Medium |
| Refactor VEO generator | 1 | Medium | Medium |
| Refactor Kling generator | 1 | Medium | Medium |
| Refactor Sora generator | 1 | Medium | Medium |

### Phase 3: Storage (Week 3-4)

**Goal:** Create generic entity storage

| Task | Files | Risk | Effort |
|------|-------|------|--------|
| Create `EntityStorage` base | 1 new | Medium | High |
| Migrate product_storage | 1 | Medium | Medium |
| Migrate project_storage | 1 | Medium | Medium |
| Migrate style_reference_storage | 1 | Medium | Medium |
| Add path safety validation | 2 | Low | Low |

### Phase 4: Agents (Week 4-5)

**Goal:** Consolidate agent patterns

| Task | Files | Risk | Effort |
|------|-------|------|--------|
| Create `prompt_loader.py` | 1 new | Low | Low |
| Create `progress.py` base | 1 new | Low | Low |
| Refactor agent files | 10 | Low | Medium |
| Standardize error handling | 10 | Low | Medium |

### Phase 5: Validation (Week 5-6)

**Goal:** Split validation.py

| Task | Files | Risk | Effort |
|------|-------|------|--------|
| Create `validation/` directory | 5 new | Low | Medium |
| Split and migrate code | 1 → 5 | Medium | Medium |
| Update imports | ~10 | Low | Low |

### Phase 6: Frontend (Week 6-7)

**Goal:** Create reusable hooks

| Task | Files | Risk | Effort |
|------|-------|------|--------|
| Create `useBridgeCall` hook | 1 new | Low | Low |
| Create `useEntityManager` hook | 1 new | Low | Medium |
| Refactor contexts | 4 | Medium | Medium |
| Adopt file-utils everywhere | 4 | Low | Low |

### Phase 7: Cleanup (Week 7-8)

**Goal:** Final housekeeping

| Task | Files | Risk | Effort |
|------|-------|------|--------|
| Consolidate constants | 2 → 1 | Low | Low |
| Remove deprecated shim | 1 | Low | Low |
| Move misplaced utilities | 1 | Low | Low |
| Address circular deps | Multiple | Medium | Medium |
| Update documentation | - | Low | Low |

---

## Appendix: Detailed File References

### Files with Highest Refactoring Priority

| File | Lines | Issue | Priority |
|------|-------|-------|----------|
| `brands/models.py` | 1,106 | God module (43 classes) | 🔴 Critical |
| `advisor/validation.py` | 1,219 | Mixed responsibilities | 🔴 Critical |
| `generators/video_generator.py` | 1,152 | Duplication with siblings | 🔴 Critical |
| `generators/kling_generator.py` | 696 | Duplication with siblings | 🔴 Critical |
| `generators/sora_generator.py` | 511 | Duplication with siblings | 🔴 Critical |
| `brands/context.py` | 734 | Multiple builders | 🟡 Medium |
| `advisor/tools/image_tools.py` | 709 | Large tool module | 🟡 Medium |
| `advisor/tools/product_tools.py` | 654 | Large tool module | 🟡 Medium |
| `advisor/product_specs.py` | 669 | Misplaced module | 🟡 Medium |

### Duplication Summary

| Category | Duplicated Lines | Files Affected |
|----------|-----------------|----------------|
| Generator methods | ~400+ | 3 |
| Storage CRUD | ~300+ | 4 |
| Agent prompt loading | ~150+ | 10 |
| Progress hooks | ~100+ | 3 |
| Brand context building | ~80+ | 4 |
| Frontend context patterns | ~200+ | 5 |
| **Total** | **~1,230+** | **29** |

---

## Notes

- All refactoring should maintain backward compatibility
- Run full test suite after each phase
- Update any affected documentation
- Consider feature flags for gradual rollout of storage changes
