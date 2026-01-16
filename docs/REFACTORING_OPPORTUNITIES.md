# Deep Code Review: Refactoring Opportunities

**Date:** January 16, 2026
**Codebase:** SIP Studio (sip-videogen)
**Version:** v0.9.8

---

## Executive Summary

After analyzing the codebase thoroughly, I've identified **50+ refactoring opportunities** across 6 major areas. The codebase has a solid foundation but shows signs of rapid feature development with accumulated technical debt. The key themes are:

1. **Significant code duplication** (~1,500+ lines could be consolidated)
2. **Inconsistent patterns** across similar modules
3. **Missing abstractions** that would simplify maintenance
4. **Scattered configuration** that should be centralized

---

## Table of Contents

- [High Priority Issues](#-high-priority-high-impact-foundation-issues)
- [Medium Priority Issues](#-medium-priority-code-quality--maintainability)
- [Lower Priority Issues](#-lower-priority-nice-to-have)
- [Summary Table](#summary-table)
- [Recommended Refactoring Order](#recommended-refactoring-order)

---

## 🔴 HIGH PRIORITY (High Impact, Foundation Issues)

### 1. Storage Layer: Create Base Classes

**Estimated Savings:** ~400 lines of code

**Problem:** `product_storage.py`, `project_storage.py`, and `style_reference_storage.py` have nearly identical CRUD patterns with copy-pasted code.

**Files affected:**
- `src/sip_studio/brands/storage/product_storage.py`
- `src/sip_studio/brands/storage/project_storage.py`
- `src/sip_studio/brands/storage/style_reference_storage.py`

**Current Pattern (repeated in each file):**
```python
def create(self, brand_slug: str, entity: EntityFull) -> EntitySummary:
    brand_dir = get_brand_dir(brand_slug)
    if not brand_dir:
        raise BrandNotFoundError(brand_slug)

    entities_dir = brand_dir / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)

    entity_dir = entities_dir / entity.slug
    entity_dir.mkdir(parents=True, exist_ok=True)

    # Save full entity
    full_path = entity_dir / "entity_full.json"
    full_path.write_text(entity.model_dump_json(indent=2))

    # Update index
    # ... same pattern repeated
```

**Solution:** Create `BaseEntityStorage` and `BaseImageStorage` classes:

```python
# New file: src/sip_studio/brands/storage/base_entity.py
from typing import Generic, TypeVar
from pathlib import Path
from abc import ABC, abstractmethod

TSummary = TypeVar("TSummary")
TFull = TypeVar("TFull")

class BaseEntityStorage(ABC, Generic[TSummary, TFull]):
    """Generic CRUD for entities with slug, timestamps, summary/full pattern."""

    @property
    @abstractmethod
    def entity_dir_name(self) -> str:
        """Directory name for this entity type (e.g., 'products', 'projects')."""
        ...

    @property
    @abstractmethod
    def index_filename(self) -> str:
        """Index file name (e.g., 'products_index.json')."""
        ...

    @abstractmethod
    def _to_summary(self, entity: TFull) -> TSummary:
        """Convert full entity to summary."""
        ...

    def create(self, brand_slug: str, entity: TFull) -> TSummary:
        """Create a new entity. Raises if already exists."""
        ...

    def load(self, brand_slug: str, slug: str) -> TFull | None:
        """Load full entity by slug."""
        ...

    def save(self, brand_slug: str, entity: TFull) -> TSummary:
        """Save/update an entity."""
        ...

    def delete(self, brand_slug: str, slug: str) -> bool:
        """Delete entity and return success status."""
        ...

    def list_all(self, brand_slug: str) -> list[TSummary]:
        """List all entity summaries for a brand."""
        ...


class BaseImageEntityStorage(BaseEntityStorage[TSummary, TFull]):
    """Extended storage with image/reference management."""

    def add_image(self, brand_slug: str, entity_slug: str, image_data: bytes, filename: str) -> str:
        """Add image to entity, return relative path."""
        ...

    def remove_image(self, brand_slug: str, entity_slug: str, image_path: str) -> bool:
        """Remove image from entity."""
        ...

    def list_images(self, brand_slug: str, entity_slug: str) -> list[str]:
        """List all image paths for entity."""
        ...
```

**Implementation for ProductStorage:**
```python
# src/sip_studio/brands/storage/product_storage.py
class ProductStorage(BaseImageEntityStorage[ProductSummary, Product]):
    entity_dir_name = "products"
    index_filename = "products_index.json"

    def _to_summary(self, product: Product) -> ProductSummary:
        return ProductSummary(
            slug=product.slug,
            name=product.name,
            # ...
        )
```

---

### 2. Advisor Tools: Extract Common Utilities

**Estimated Savings:** ~200 lines of code

**Problem:** `_resolve_brand_path()` is duplicated in 3 files. Error messages are inconsistent across tools.

**Files affected:**
- `src/sip_studio/advisor/tools/file_tools.py`
- `src/sip_studio/advisor/tools/product_tools.py`
- `src/sip_studio/advisor/tools/image_tools.py`
- `src/sip_studio/advisor/tools/style_reference_tools.py`

**Current Duplication:**
```python
# In file_tools.py (lines 33-48)
def _resolve_brand_path(relative_path: str) -> Path | None:
    slug = get_active_brand_slug()
    if not slug:
        return None
    brand_dir = get_brand_dir(slug)
    if not brand_dir:
        return None
    return brand_dir / relative_path

# Same function in product_tools.py (lines 28-43)
# Same function in image_tools.py (lines 45-60)
```

**Solution:** Create shared utilities module:

```python
# New file: src/sip_studio/advisor/tools/utils.py
from pathlib import Path
from sip_studio.advisor.tools._common import get_active_brand_slug
from sip_studio.brands.storage.base import get_brand_dir

class ToolError:
    """Standardized error messages for advisor tools."""
    NO_ACTIVE_BRAND = "No active brand selected. Please select a brand first."
    BRAND_NOT_FOUND = "Brand '{slug}' not found."
    INVALID_SLUG = "Invalid slug '{slug}'. Slugs must be lowercase with hyphens only."
    FILE_NOT_FOUND = "File not found: {path}"
    PERMISSION_DENIED = "Permission denied: {path}"

def resolve_brand_path(relative_path: str) -> Path | None:
    """Resolve a relative path within the active brand directory."""
    slug = get_active_brand_slug()
    if not slug:
        return None
    brand_dir = get_brand_dir(slug)
    if not brand_dir:
        return None
    return brand_dir / relative_path

def require_active_brand() -> tuple[str, str | None]:
    """
    Get active brand slug or error message.

    Returns:
        tuple of (slug, error_message) - error_message is None if successful
    """
    slug = get_active_brand_slug()
    if not slug:
        return "", ToolError.NO_ACTIVE_BRAND
    return slug, None

def validate_slug(slug: str) -> str | None:
    """
    Validate a slug format.

    Returns:
        Error message if invalid, None if valid
    """
    import re
    if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug):
        return ToolError.INVALID_SLUG.format(slug=slug)
    return None

def format_file_list(files: list[Path], base_dir: Path) -> str:
    """Format a list of files for display in tool output."""
    if not files:
        return "No files found."

    lines = []
    for f in sorted(files):
        rel_path = f.relative_to(base_dir) if f.is_relative_to(base_dir) else f
        size = f.stat().st_size if f.exists() else 0
        lines.append(f"  - {rel_path} ({_format_size(size)})")

    return "\n".join(lines)

def _format_size(size: int) -> str:
    """Format file size for display."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
```

---

### 3. Services Layer: Standardize Path Resolution & Validation

**Estimated Savings:** ~150 lines of code

**Problem:** Each service duplicates brand validation and path resolution logic differently.

**Files affected:**
- `src/sip_studio/studio/services/asset_service.py`
- `src/sip_studio/studio/services/document_service.py`
- `src/sip_studio/studio/services/product_service.py`
- `src/sip_studio/studio/services/style_reference_service.py`

**Current Duplication:**
```python
# In asset_service.py
def get_asset(self, relative_path: str) -> dict:
    slug = self._state.active_brand_slug
    if not slug:
        return bridge_error("No active brand")

    brand_dir = get_brand_dir(slug)
    if not brand_dir:
        return bridge_error(f"Brand not found: {slug}")

    full_path = brand_dir / relative_path
    if not full_path.exists():
        return bridge_error(f"Asset not found: {relative_path}")
    # ...

# Same pattern in document_service.py, product_service.py, etc.
```

**Solution:** Create `BrandAwareService` base class:

```python
# New file: src/sip_studio/studio/services/base_service.py
from pathlib import Path
from typing import TypeVar, Generic
from sip_studio.studio.state import BridgeState
from sip_studio.studio.utils.bridge_types import bridge_error, bridge_success
from sip_studio.brands.storage.base import get_brand_dir

T = TypeVar("T")

class BrandAwareService:
    """Base class for services that operate on brand data."""

    def __init__(self, state: BridgeState):
        self._state = state

    def _ensure_active_brand(self) -> tuple[str | None, dict | None]:
        """
        Ensure there's an active brand selected.

        Returns:
            tuple of (brand_slug, error_response)
            - If successful: (slug, None)
            - If failed: (None, error_dict)
        """
        slug = self._state.active_brand_slug
        if not slug:
            return None, bridge_error("No active brand selected")
        return slug, None

    def _get_brand_dir(self) -> tuple[Path | None, dict | None]:
        """
        Get the active brand's directory.

        Returns:
            tuple of (brand_dir, error_response)
        """
        slug, error = self._ensure_active_brand()
        if error:
            return None, error

        brand_dir = get_brand_dir(slug)
        if not brand_dir:
            return None, bridge_error(f"Brand directory not found: {slug}")

        return brand_dir, None

    def _resolve_asset_path(
        self,
        relative_path: str,
        allowed_extensions: set[str] | None = None,
        must_exist: bool = True
    ) -> tuple[Path | None, dict | None]:
        """
        Resolve and validate an asset path within the brand directory.

        Args:
            relative_path: Path relative to brand directory
            allowed_extensions: Set of allowed file extensions (e.g., {'.png', '.jpg'})
            must_exist: Whether the file must exist

        Returns:
            tuple of (full_path, error_response)
        """
        brand_dir, error = self._get_brand_dir()
        if error:
            return None, error

        full_path = brand_dir / relative_path

        # Security: ensure path is within brand directory
        try:
            full_path.resolve().relative_to(brand_dir.resolve())
        except ValueError:
            return None, bridge_error("Invalid path: access denied")

        # Check extension if specified
        if allowed_extensions and full_path.suffix.lower() not in allowed_extensions:
            return None, bridge_error(
                f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Check existence if required
        if must_exist and not full_path.exists():
            return None, bridge_error(f"File not found: {relative_path}")

        return full_path, None
```

**Updated AssetService:**
```python
# src/sip_studio/studio/services/asset_service.py
class AssetService(BrandAwareService):
    ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm'}

    def get_asset(self, relative_path: str) -> dict:
        full_path, error = self._resolve_asset_path(
            relative_path,
            allowed_extensions=self.ALLOWED_IMAGE_EXTENSIONS | self.ALLOWED_VIDEO_EXTENSIONS
        )
        if error:
            return error

        # Now proceed with validated path
        # ...
```

---

### 4. Video Generators: Extract Shared Logic

**Estimated Savings:** ~300 lines of code

**Problem:** VEO, Sora, and Kling generators duplicate significant logic:
- `_build_flow_context()` method (95% identical across generators)
- `_build_scene_reference_map()` method (nearly identical)
- Polling loop patterns
- Progress bar setup and management

**Files affected:**
- `src/sip_studio/generators/video_generator.py` (1200+ lines)
- `src/sip_studio/generators/sora_generator.py`
- `src/sip_studio/generators/kling_generator.py`

**Current Duplication in `_build_flow_context()`:**
```python
# In video_generator.py (VEO)
def _build_flow_context(self, scene: SceneAction, total_scenes: int) -> str | None:
    parts = []
    if scene.scene_number == 1:
        parts.append("This is the opening scene...")
    elif scene.scene_number == total_scenes:
        parts.append("This is the final scene...")
    # ... 40+ lines of identical logic

# In sora_generator.py - nearly identical
# In kling_generator.py - nearly identical
```

**Solution:** Move shared logic to `BaseVideoGenerator`:

```python
# Updated: src/sip_studio/generators/base.py
from abc import ABC, abstractmethod
from typing import Any
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from sip_studio.models.script import SceneAction
from sip_studio.models.assets import GeneratedAsset

class BaseVideoGenerator(ABC):
    """Base class for all video generators with shared utilities."""

    # Provider-specific settings (override in subclasses)
    PROVIDER_NAME: str = "base"
    VALID_DURATIONS: list[int] = [5]
    MAX_REFERENCE_IMAGES: int = 1
    SUPPORTS_FLOW_CONTEXT: bool = False

    def __init__(self, settings: Any):
        self.settings = settings

    @abstractmethod
    async def generate(
        self,
        scene: SceneAction,
        reference_image: GeneratedAsset | None = None,
        **kwargs
    ) -> GeneratedAsset:
        """Generate video for a scene. Must be implemented by subclasses."""
        ...

    def _build_flow_context(
        self,
        scene: SceneAction,
        total_scenes: int,
        previous_scene: SceneAction | None = None,
        next_scene: SceneAction | None = None
    ) -> str | None:
        """
        Build narrative flow context for the scene.

        This helps generators understand the scene's position in the story
        for better visual continuity.
        """
        if not self.SUPPORTS_FLOW_CONTEXT:
            return None

        parts = []

        # Opening scene
        if scene.scene_number == 1:
            parts.append(
                "This is the opening scene that establishes the video's tone and setting. "
                "Start with a strong visual hook."
            )
        # Final scene
        elif scene.scene_number == total_scenes:
            parts.append(
                "This is the final scene. Provide visual closure and reinforce the main message."
            )
        # Middle scenes
        else:
            parts.append(
                f"This is scene {scene.scene_number} of {total_scenes}. "
                "Maintain visual continuity with surrounding scenes."
            )

        # Previous scene context
        if previous_scene:
            parts.append(f"Previous scene: {previous_scene.description[:100]}...")

        # Next scene context
        if next_scene:
            parts.append(f"Next scene: {next_scene.description[:100]}...")

        return " ".join(parts) if parts else None

    def _build_scene_reference_map(
        self,
        scenes: list[SceneAction],
        assets: list[GeneratedAsset]
    ) -> dict[int, GeneratedAsset | None]:
        """
        Map scene numbers to their reference images.

        Returns:
            Dict mapping scene_number -> reference asset (or None)
        """
        asset_by_scene = {
            asset.scene_number: asset
            for asset in assets
            if asset.scene_number is not None
        }

        return {
            scene.scene_number: asset_by_scene.get(scene.scene_number)
            for scene in scenes
        }

    def _create_progress_bar(self, description: str) -> Progress:
        """Create a standardized progress bar for generation tracking."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )

    def _normalize_duration(self, requested_duration: int) -> int:
        """Normalize duration to nearest valid value for this provider."""
        if requested_duration in self.VALID_DURATIONS:
            return requested_duration

        # Find closest valid duration
        return min(
            self.VALID_DURATIONS,
            key=lambda d: abs(d - requested_duration)
        )

    async def _poll_with_progress(
        self,
        check_status: callable,
        description: str,
        timeout_seconds: int = 300,
        poll_interval: float = 5.0
    ) -> Any:
        """
        Generic polling loop with progress display.

        Args:
            check_status: Async callable that returns (is_complete, result_or_none)
            description: Description for progress bar
            timeout_seconds: Maximum time to wait
            poll_interval: Seconds between checks

        Returns:
            Final result from check_status

        Raises:
            TimeoutError: If timeout exceeded
        """
        import asyncio
        import time

        start_time = time.time()

        with self._create_progress_bar(description) as progress:
            task = progress.add_task(description, total=100)

            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    raise TimeoutError(f"{self.PROVIDER_NAME} generation timed out")

                is_complete, result = await check_status()

                if is_complete:
                    progress.update(task, completed=100)
                    return result

                # Update progress estimate
                progress_pct = min(95, (elapsed / timeout_seconds) * 100)
                progress.update(task, completed=progress_pct)

                await asyncio.sleep(poll_interval)
```

---

### 5. Pydantic Models: Create Generic Index Base

**Estimated Savings:** ~100 lines of code

**Problem:** `BrandIndex`, `ProductIndex`, `ProjectIndex`, `StyleReferenceIndex` have identical `get_*()`, `add_*()`, `remove_*()` methods.

**Files affected:**
- `src/sip_studio/brands/models/brand.py`
- `src/sip_studio/brands/models/product.py`
- `src/sip_studio/brands/models/project.py`
- `src/sip_studio/brands/models/style_reference.py`

**Current Duplication:**
```python
# In brand.py
class BrandIndex(BaseModel):
    version: str = "1.0"
    brands: list[BrandSummary] = Field(default_factory=list)

    def get_brand(self, slug: str) -> BrandSummary | None:
        for brand in self.brands:
            if brand.slug == slug:
                return brand
        return None

    def add_brand(self, brand: BrandSummary) -> None:
        existing = self.get_brand(brand.slug)
        if existing:
            self.brands.remove(existing)
        self.brands.append(brand)

    def remove_brand(self, slug: str) -> bool:
        existing = self.get_brand(slug)
        if existing:
            self.brands.remove(existing)
            return True
        return False

# Nearly identical in ProductIndex, ProjectIndex, StyleReferenceIndex
```

**Solution:** Create generic base class:

```python
# New file: src/sip_studio/brands/models/base_index.py
from typing import Generic, TypeVar, Protocol
from pydantic import BaseModel, Field

class HasSlug(Protocol):
    """Protocol for items that have a slug identifier."""
    slug: str

T = TypeVar("T", bound=HasSlug)

class BaseIndex(BaseModel, Generic[T]):
    """
    Generic index for entities with slug-based identification.

    Subclasses should define:
    - items field with appropriate type annotation
    - version field if needed
    """
    version: str = "1.0"

    @property
    def items(self) -> list[T]:
        """Override in subclass to return the items list."""
        raise NotImplementedError

    @items.setter
    def items(self, value: list[T]) -> None:
        """Override in subclass to set the items list."""
        raise NotImplementedError

    def get_item(self, slug: str) -> T | None:
        """Get item by slug."""
        for item in self.items:
            if item.slug == slug:
                return item
        return None

    def add_item(self, item: T) -> None:
        """Add or update item (replaces existing with same slug)."""
        existing = self.get_item(item.slug)
        if existing:
            self.items.remove(existing)
        self.items.append(item)

    def remove_item(self, slug: str) -> bool:
        """Remove item by slug. Returns True if item was found and removed."""
        existing = self.get_item(slug)
        if existing:
            self.items.remove(existing)
            return True
        return False

    def has_item(self, slug: str) -> bool:
        """Check if item exists."""
        return self.get_item(slug) is not None

    def count(self) -> int:
        """Return number of items."""
        return len(self.items)


# Usage in brand.py:
class BrandIndex(BaseModel):
    version: str = "1.0"
    brands: list[BrandSummary] = Field(default_factory=list)

    @property
    def items(self) -> list[BrandSummary]:
        return self.brands

    @items.setter
    def items(self, value: list[BrandSummary]) -> None:
        self.brands = value

    # Convenience aliases for backward compatibility
    def get_brand(self, slug: str) -> BrandSummary | None:
        return self.get_item(slug)

    def add_brand(self, brand: BrandSummary) -> None:
        self.add_item(brand)

    def remove_brand(self, slug: str) -> bool:
        return self.remove_item(slug)
```

---

### 6. Bridge Layer: Fix Async Event Loop Pattern

**Priority:** Critical (potential runtime errors)

**Problem:** `asyncio.run()` called directly in sync bridge methods - will crash if called from async context. This is a bug waiting to happen.

**File:** `src/sip_studio/studio/bridge.py`

**Current Problematic Pattern:**
```python
# Lines 288-290
def chat(self, message: str, attachments: list) -> dict:
    return asyncio.run(self._chat_service.chat(...))

# Lines 309-316
def generate_quick_images(self, prompt: str, ...) -> dict:
    return asyncio.run(self._quick_generator_service.generate_images(...))
```

**Problem:** If any code path calls these methods from within an async context, it will raise:
```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

**Solution:** Use ThreadPoolExecutor pattern consistently:

```python
# src/sip_studio/studio/bridge.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import TypeVar, Coroutine, Any

T = TypeVar("T")

class Bridge:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bridge-async")
        # ... rest of init

    def _run_async(self, coro: Coroutine[Any, Any, T]) -> T:
        """
        Run async coroutine safely, works whether called from sync or async context.

        Creates a new event loop in a separate thread to avoid conflicts
        with any existing event loop.
        """
        def runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        return self._executor.submit(runner).result()

    def __del__(self):
        """Clean up executor on destruction."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

    # Updated methods:
    def chat(self, message: str, attachments: list) -> dict:
        return self._run_async(self._chat_service.chat(...))

    def generate_quick_images(self, prompt: str, ...) -> dict:
        return self._run_async(self._quick_generator_service.generate_images(...))
```

**Alternative: Decorator approach:**
```python
def run_async_safely(func):
    """Decorator to run async methods safely from sync context."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        coro = func(self, *args, **kwargs)
        return self._run_async(coro)
    return wrapper

class Bridge:
    @run_async_safely
    async def chat(self, message: str, attachments: list) -> dict:
        return await self._chat_service.chat(...)
```

---

## 🟡 MEDIUM PRIORITY (Code Quality & Maintainability)

### 7. Configuration: Centralize Scattered Constants

**Problem:** 15+ hardcoded LLM model names, duplicate retry constants, scattered polling intervals across the codebase.

**Duplicates found:**
- `MAX_RETRIES = 2` in 2 files
- `MAX_STEP_LEN = 100` / `MAX_DETAIL_LEN = 500` in 2 files
- `temperature=0.1` hardcoded in 3 files
- Model names like `"gpt-4o"` in 5+ files
- Polling intervals (5s, 10s, etc.) scattered throughout

**Files affected:**
- `src/sip_studio/advisor/validation/*.py`
- `src/sip_studio/generators/*.py`
- `src/sip_studio/agents/*.py`
- `src/sip_studio/studio/services/*.py`

**Solution:** Create comprehensive config modules:

```python
# src/sip_studio/config/models.py
"""LLM model configuration - single source of truth."""

class OpenAIModels:
    """OpenAI model identifiers."""
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    O1 = "o1"
    O1_MINI = "o1-mini"

class GeminiModels:
    """Google Gemini model identifiers."""
    GEMINI_PRO = "gemini-1.5-pro"
    GEMINI_FLASH = "gemini-1.5-flash"
    GEMINI_IMAGE = "gemini-2.0-flash-preview-image-generation"

# Default assignments
ADVISOR_MODEL = OpenAIModels.GPT4O
REVIEWER_MODEL = OpenAIModels.GPT4O
SCREENWRITER_MODEL = OpenAIModels.GPT4O_MINI
IMAGE_GENERATOR_MODEL = GeminiModels.GEMINI_IMAGE
```

```python
# src/sip_studio/config/constants.py - expand existing
"""Application-wide constants."""

class RetryPolicy:
    """Retry configuration for API calls."""
    MAX_RETRIES = 2
    WAIT_MULTIPLIER = 1
    WAIT_MIN = 1
    WAIT_MAX = 10

class LLMParameters:
    """Default LLM parameters."""
    ANALYSIS_TEMPERATURE = 0.1  # For structured analysis
    GENERATION_TEMPERATURE = 0.3  # For creative generation
    MAX_TOKENS_DEFAULT = 4096

class ProgressDisplay:
    """Progress tracking display constants."""
    MAX_STEP_LENGTH = 100
    MAX_DETAIL_LENGTH = 500
    TRUNCATION_SUFFIX = "..."

class PollingIntervals:
    """Polling intervals for async operations (seconds)."""
    VIDEO_GENERATION = 5.0
    IMAGE_GENERATION = 2.0
    MUSIC_GENERATION = 3.0
    DEFAULT = 5.0

class Timeouts:
    """Operation timeouts (seconds)."""
    VIDEO_GENERATION = 600
    IMAGE_GENERATION = 120
    MUSIC_GENERATION = 300
    API_REQUEST = 30

# Provider-specific capabilities
PROVIDER_CAPABILITIES = {
    "veo": {
        "valid_durations": [4, 6, 8],
        "max_reference_images": 3,
        "supports_flow_context": True,
        "supports_audio": False,
    },
    "sora": {
        "valid_durations": [4, 8, 12, 16, 20],
        "max_reference_images": 1,
        "supports_flow_context": True,
        "supports_audio": False,
    },
    "kling": {
        "valid_durations": [5, 10],
        "max_reference_images": 1,
        "supports_flow_context": False,
        "supports_audio": False,
    },
}
```

---

### 8. Frontend: Extract Common Hooks

**Estimated Savings:** ~300 lines of code

**Problem:** Duplicated patterns across React components:
- `waitForPyWebViewReady()` check in 30+ locations
- Deep copy pattern in all BrandMemory sections
- Save/error/success state pattern in 6+ files
- File upload to base64 conversion in 5+ places

**Files affected:**
- `src/sip_studio/studio/frontend/src/hooks/useChat.ts` (668 lines - too large)
- `src/sip_studio/studio/frontend/src/components/BrandMemory/sections/*.tsx`
- `src/sip_studio/studio/frontend/src/context/*.tsx`

**Solution:** Create reusable hooks:

```typescript
// New file: src/hooks/useBridgeCall.ts
import { useCallback } from 'react'
import { waitForPyWebViewReady } from '@/lib/pywebview'
import { useAsyncAction } from './useAsyncAction'

interface BridgeCallOptions<T> {
  onSuccess?: (result: T) => void
  onError?: (error: Error) => void
  fallbackData?: T
}

export function useBridgeCall<T>(
  action: () => Promise<T>,
  options: BridgeCallOptions<T> = {}
) {
  const { onSuccess, onError, fallbackData } = options

  return useAsyncAction(async () => {
    const ready = await waitForPyWebViewReady()

    if (!ready) {
      if (fallbackData !== undefined) {
        return fallbackData
      }
      throw new Error('PyWebView not available')
    }

    return action()
  }, { onSuccess, onError })
}

// Usage:
const { execute, isLoading, error } = useBridgeCall(
  () => window.pywebview.api.getBrands(),
  { fallbackData: [] }
)
```

```typescript
// New file: src/hooks/useEditableData.ts
import { useState, useCallback } from 'react'

interface UseEditableDataOptions<T> {
  onSave: (data: T) => Promise<void>
  deepCopy?: (data: T) => T
}

export function useEditableData<T>(
  initialData: T,
  options: UseEditableDataOptions<T>
) {
  const { onSave, deepCopy = (d) => JSON.parse(JSON.stringify(d)) } = options

  const [editData, setEditData] = useState<T | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const startEditing = useCallback(() => {
    setEditData(deepCopy(initialData))
    setIsEditing(true)
    setSaveError(null)
    setSaveSuccess(false)
  }, [initialData, deepCopy])

  const cancelEditing = useCallback(() => {
    setEditData(null)
    setIsEditing(false)
    setSaveError(null)
  }, [])

  const saveChanges = useCallback(async () => {
    if (!editData) return

    setIsSaving(true)
    setSaveError(null)

    try {
      await onSave(editData)
      setSaveSuccess(true)
      setIsEditing(false)
      setEditData(null)

      // Clear success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setIsSaving(false)
    }
  }, [editData, onSave])

  return {
    data: isEditing ? editData : initialData,
    isEditing,
    isSaving,
    saveError,
    saveSuccess,
    setEditData,
    startEditing,
    cancelEditing,
    saveChanges,
  }
}
```

```typescript
// New file: src/hooks/useFormState.ts
import { useState, useCallback } from 'react'

export function useFormState() {
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const reset = useCallback(() => {
    setSaveError(null)
    setSaveSuccess(false)
  }, [])

  const withSaveState = useCallback(async <T>(
    action: () => Promise<T>
  ): Promise<T | null> => {
    setIsSaving(true)
    setSaveError(null)
    setSaveSuccess(false)

    try {
      const result = await action()
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
      return result
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Operation failed')
      return null
    } finally {
      setIsSaving(false)
    }
  }, [])

  return {
    isSaving,
    saveError,
    saveSuccess,
    reset,
    withSaveState,
  }
}
```

```typescript
// New file: src/lib/fileUtils.ts
export async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = () => {
      const result = reader.result as string
      // Remove data URL prefix (e.g., "data:image/png;base64,")
      const base64 = result.includes(',') ? result.split(',')[1] : result
      resolve(base64)
    }

    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

export async function filesToBase64(files: File[]): Promise<string[]> {
  return Promise.all(files.map(fileToBase64))
}

export function formatFileSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`
}

export function getFileExtension(filename: string): string {
  return filename.slice(filename.lastIndexOf('.')).toLowerCase()
}

export function isImageFile(filename: string): boolean {
  const imageExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']
  return imageExtensions.includes(getFileExtension(filename))
}

export function isVideoFile(filename: string): boolean {
  const videoExtensions = ['.mp4', '.mov', '.webm', '.avi']
  return videoExtensions.includes(getFileExtension(filename))
}
```

---

### 9. ChatService: Break Down Complex Method

**Problem:** `ChatService.chat()` is ~290 lines with multiple responsibilities mixed together.

**File:** `src/sip_studio/studio/services/chat_service.py`

**Current Structure:**
```python
async def chat(self, message: str, attachments: list[dict], ...) -> dict:
    # 1. Message preparation (~30 lines)
    # 2. Snapshot state before (~40 lines)
    # 3. Batch request handling (~50 lines)
    # 4. Regular chat handling (~60 lines)
    # 5. Asset collection after (~50 lines)
    # 6. Response building (~30 lines)
    # Total: ~290 lines in one method
```

**Solution:** Extract into focused methods:

```python
class ChatService(BrandAwareService):
    """Service for handling chat interactions with the advisor."""

    async def chat(
        self,
        message: str,
        attachments: list[dict],
        session_id: str | None = None,
        idea_count: int | None = None,
    ) -> dict:
        """
        Main chat endpoint. Delegates to specialized handlers.
        """
        # Validate brand
        brand_slug, error = self._ensure_active_brand()
        if error:
            return error

        # Prepare message with attachments
        prepared_message = self._prepare_message(message, attachments)

        # Snapshot assets before generation
        before_snapshot = self._snapshot_generated_assets(brand_slug)

        # Route to appropriate handler
        if idea_count and idea_count > 1:
            response = await self._handle_batch_request(
                prepared_message, idea_count, session_id
            )
        else:
            response = await self._handle_single_request(
                prepared_message, session_id
            )

        if not response.get("success"):
            return response

        # Collect newly generated assets
        new_assets = self._collect_new_assets(brand_slug, before_snapshot)

        # Build final response
        return self._build_response(response, new_assets)

    def _prepare_message(
        self,
        message: str,
        attachments: list[dict]
    ) -> str:
        """Prepare message with attachment context."""
        if not attachments:
            return message

        attachment_context = []
        for att in attachments:
            att_type = att.get("type", "file")
            att_path = att.get("path", "")
            att_name = att.get("name", "attachment")

            if att_type == "image":
                attachment_context.append(f"[Attached image: {att_name}]")
            elif att_type == "document":
                attachment_context.append(f"[Attached document: {att_name}]")
            else:
                attachment_context.append(f"[Attached file: {att_name}]")

        context_str = "\n".join(attachment_context)
        return f"{message}\n\n{context_str}"

    def _snapshot_generated_assets(self, brand_slug: str) -> dict:
        """Capture current state of generated assets for diff tracking."""
        brand_dir = get_brand_dir(brand_slug)
        if not brand_dir:
            return {"images": set(), "videos": set()}

        assets_dir = brand_dir / "assets"

        return {
            "images": set(assets_dir.glob("**/*.png")) | set(assets_dir.glob("**/*.jpg")),
            "videos": set(assets_dir.glob("**/*.mp4")) | set(assets_dir.glob("**/*.webm")),
        }

    async def _handle_batch_request(
        self,
        message: str,
        idea_count: int,
        session_id: str | None
    ) -> dict:
        """Handle batch image generation requests."""
        # ... batch-specific logic
        pass

    async def _handle_single_request(
        self,
        message: str,
        session_id: str | None
    ) -> dict:
        """Handle single chat message."""
        # ... single message logic
        pass

    def _collect_new_assets(
        self,
        brand_slug: str,
        before_snapshot: dict
    ) -> dict:
        """Find assets created during this chat turn."""
        after_snapshot = self._snapshot_generated_assets(brand_slug)

        new_images = after_snapshot["images"] - before_snapshot["images"]
        new_videos = after_snapshot["videos"] - before_snapshot["videos"]

        return {
            "images": [self._asset_to_dict(p) for p in sorted(new_images)],
            "videos": [self._asset_to_dict(p) for p in sorted(new_videos)],
        }

    def _asset_to_dict(self, path: Path) -> dict:
        """Convert asset path to response dict."""
        return {
            "path": str(path),
            "name": path.name,
            "type": "image" if path.suffix in {".png", ".jpg", ".jpeg"} else "video",
        }

    def _build_response(
        self,
        chat_response: dict,
        new_assets: dict
    ) -> dict:
        """Build final response with message and assets."""
        return bridge_success({
            "message": chat_response.get("message", ""),
            "session_id": chat_response.get("session_id"),
            "new_images": new_assets["images"],
            "new_videos": new_assets["videos"],
            "thinking_steps": chat_response.get("thinking_steps", []),
        })
```

---

### 10. Image Tools: Refactor 900+ Line Function

**Problem:** `_impl_generate_image()` is 900+ lines with deeply nested logic, making it very hard to understand and maintain.

**File:** `src/sip_studio/advisor/tools/image_tools.py` (lines 107-783+)

**Current Structure:**
```python
async def _impl_generate_image(...) -> str:
    # 1. Parameter validation (~50 lines)
    # 2. Product reference loading (~100 lines)
    # 3. Style reference loading (~100 lines)
    # 4. Brand context building (~80 lines)
    # 5. Prompt preparation (~150 lines)
    # 6. Image generation (~100 lines)
    # 7. Quality validation (~100 lines)
    # 8. Retry logic (~100 lines)
    # 9. Asset storage (~80 lines)
    # 10. Response formatting (~40 lines)
    # Total: 900+ lines with deep nesting
```

**Solution:** Break into smaller, focused functions:

```python
# src/sip_studio/advisor/tools/image_tools.py

async def _impl_generate_image(
    prompt: str,
    product_slugs: list[str] | None = None,
    style_reference_slug: str | None = None,
    aspect_ratio: str = "1:1",
    save_to: str | None = None,
) -> str:
    """
    Generate an image with optional product and style references.

    This is the main entry point that coordinates the generation pipeline.
    """
    # Validate inputs
    validation_error = _validate_generation_inputs(
        prompt, product_slugs, style_reference_slug, aspect_ratio
    )
    if validation_error:
        return validation_error

    # Load references
    product_refs = await _load_product_references(product_slugs or [])
    style_refs = await _load_style_references(style_reference_slug)

    # Build generation context
    context = _build_generation_context(
        prompt=prompt,
        product_refs=product_refs,
        style_refs=style_refs,
    )

    # Execute generation with retries
    result = await _execute_with_validation(
        context=context,
        aspect_ratio=aspect_ratio,
        max_attempts=3,
    )

    if not result.success:
        return f"Image generation failed: {result.error}"

    # Save and return
    saved_path = await _save_generated_image(
        image=result.image,
        save_to=save_to,
        context=context,
    )

    return _format_success_response(saved_path, result.metadata)


def _validate_generation_inputs(
    prompt: str,
    product_slugs: list[str] | None,
    style_reference_slug: str | None,
    aspect_ratio: str,
) -> str | None:
    """Validate all inputs before generation. Returns error message or None."""
    if not prompt or not prompt.strip():
        return "Prompt cannot be empty"

    valid_ratios = {"1:1", "16:9", "9:16", "4:3", "3:4"}
    if aspect_ratio not in valid_ratios:
        return f"Invalid aspect ratio. Must be one of: {', '.join(valid_ratios)}"

    # Validate slugs exist
    if product_slugs:
        for slug in product_slugs:
            if not _product_exists(slug):
                return f"Product not found: {slug}"

    if style_reference_slug and not _style_reference_exists(style_reference_slug):
        return f"Style reference not found: {style_reference_slug}"

    return None


async def _load_product_references(
    product_slugs: list[str]
) -> list[ProductReference]:
    """Load product data and images for reference."""
    references = []

    for slug in product_slugs:
        product = _load_product(slug)
        if not product:
            continue

        images = _load_product_images(slug)
        references.append(ProductReference(
            product=product,
            images=images[:3],  # Max 3 images per product
        ))

    return references


async def _load_style_references(
    style_ref_slug: str | None
) -> list[StyleReference]:
    """Load style reference images and guidelines."""
    if not style_ref_slug:
        return []

    style_ref = _load_style_reference(style_ref_slug)
    if not style_ref:
        return []

    return [StyleReference(
        style=style_ref,
        images=_load_style_images(style_ref_slug),
    )]


@dataclass
class GenerationContext:
    """Context for image generation."""
    prompt: str
    enhanced_prompt: str
    product_refs: list[ProductReference]
    style_refs: list[StyleReference]
    brand_guidelines: str | None


def _build_generation_context(
    prompt: str,
    product_refs: list[ProductReference],
    style_refs: list[StyleReference],
) -> GenerationContext:
    """Build complete context for generation."""
    # Get brand guidelines
    brand_slug = get_active_brand_slug()
    brand_guidelines = _get_brand_visual_guidelines(brand_slug) if brand_slug else None

    # Enhance prompt with context
    enhanced_prompt = _enhance_prompt(
        base_prompt=prompt,
        product_refs=product_refs,
        style_refs=style_refs,
        guidelines=brand_guidelines,
    )

    return GenerationContext(
        prompt=prompt,
        enhanced_prompt=enhanced_prompt,
        product_refs=product_refs,
        style_refs=style_refs,
        brand_guidelines=brand_guidelines,
    )


@dataclass
class GenerationResult:
    """Result of image generation attempt."""
    success: bool
    image: bytes | None = None
    error: str | None = None
    metadata: dict | None = None


async def _execute_with_validation(
    context: GenerationContext,
    aspect_ratio: str,
    max_attempts: int = 3,
) -> GenerationResult:
    """Execute generation with quality validation and retries."""
    last_error = None

    for attempt in range(max_attempts):
        try:
            # Generate image
            image_bytes = await _generate_image_raw(
                prompt=context.enhanced_prompt,
                references=_collect_reference_images(context),
                aspect_ratio=aspect_ratio,
            )

            # Validate quality
            validation = await _validate_image_quality(
                image_bytes=image_bytes,
                context=context,
            )

            if validation.passed:
                return GenerationResult(
                    success=True,
                    image=image_bytes,
                    metadata={
                        "attempt": attempt + 1,
                        "validation_score": validation.score,
                    },
                )

            # Adjust prompt for retry based on validation feedback
            context = _adjust_context_for_retry(context, validation.feedback)
            last_error = validation.feedback

        except Exception as e:
            last_error = str(e)
            if attempt == max_attempts - 1:
                break

    return GenerationResult(
        success=False,
        error=last_error or "Generation failed after max attempts",
    )
```

---

### 11. Error Handling: Standardize Bridge Responses

**Problem:** Inconsistent error formats between Python and JavaScript:
- Some use `bridge_error(str(e))`
- Some have nested `success` fields
- No error codes for programmatic handling
- Stack traces never sent (hard to debug)

**Current Inconsistencies:**
```python
# Style 1: Simple string
return bridge_error("Something went wrong")

# Style 2: With details
return {"success": False, "error": {"message": "...", "details": {...}}}

# Style 3: Nested success
return {"success": True, "data": {"success": False, "error": "..."}}
```

**Solution:** Create standardized error response system:

```python
# New file: src/sip_studio/studio/utils/errors.py
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any
import traceback

class ErrorCode(str, Enum):
    """Standard error codes for bridge responses."""
    # Brand errors
    NO_ACTIVE_BRAND = "NO_ACTIVE_BRAND"
    BRAND_NOT_FOUND = "BRAND_NOT_FOUND"

    # File errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"

    # Validation errors
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"

    # API errors
    API_ERROR = "API_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"

    # Generic
    UNKNOWN = "UNKNOWN"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class BridgeError:
    """Standardized error response for bridge calls."""
    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None
    stack: str | None = None  # Only in dev mode

    def to_dict(self, include_stack: bool = False) -> dict:
        result = {
            "success": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
            }
        }

        if self.details:
            result["error"]["details"] = self.details

        if include_stack and self.stack:
            result["error"]["stack"] = self.stack

        return result


def bridge_error(
    message: str,
    code: ErrorCode = ErrorCode.UNKNOWN,
    details: dict[str, Any] | None = None,
    exception: Exception | None = None,
) -> dict:
    """
    Create a standardized error response.

    Args:
        message: Human-readable error message
        code: Error code for programmatic handling
        details: Additional context
        exception: Original exception (for stack trace in dev)

    Returns:
        Standardized error dict
    """
    import os
    is_dev = os.getenv("STUDIO_DEV", "").lower() in ("1", "true")

    stack = None
    if exception and is_dev:
        stack = traceback.format_exception(type(exception), exception, exception.__traceback__)
        stack = "".join(stack)

    error = BridgeError(
        code=code,
        message=message,
        details=details,
        stack=stack,
    )

    return error.to_dict(include_stack=is_dev)


def bridge_success(data: Any = None) -> dict:
    """Create a standardized success response."""
    result = {"success": True}
    if data is not None:
        result["data"] = data
    return result


# Convenience functions for common errors
def error_no_active_brand() -> dict:
    return bridge_error(
        "No active brand selected. Please select a brand first.",
        code=ErrorCode.NO_ACTIVE_BRAND,
    )

def error_brand_not_found(slug: str) -> dict:
    return bridge_error(
        f"Brand not found: {slug}",
        code=ErrorCode.BRAND_NOT_FOUND,
        details={"slug": slug},
    )

def error_file_not_found(path: str) -> dict:
    return bridge_error(
        f"File not found: {path}",
        code=ErrorCode.FILE_NOT_FOUND,
        details={"path": path},
    )

def error_invalid_input(message: str, field: str | None = None) -> dict:
    details = {"field": field} if field else None
    return bridge_error(
        message,
        code=ErrorCode.INVALID_INPUT,
        details=details,
    )
```

**Frontend TypeScript types:**
```typescript
// src/types/bridge.ts
export enum ErrorCode {
  NO_ACTIVE_BRAND = 'NO_ACTIVE_BRAND',
  BRAND_NOT_FOUND = 'BRAND_NOT_FOUND',
  FILE_NOT_FOUND = 'FILE_NOT_FOUND',
  PERMISSION_DENIED = 'PERMISSION_DENIED',
  INVALID_FILE_TYPE = 'INVALID_FILE_TYPE',
  INVALID_INPUT = 'INVALID_INPUT',
  MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD',
  API_ERROR = 'API_ERROR',
  RATE_LIMITED = 'RATE_LIMITED',
  TIMEOUT = 'TIMEOUT',
  UNKNOWN = 'UNKNOWN',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
}

export interface BridgeErrorDetail {
  code: ErrorCode
  message: string
  details?: Record<string, unknown>
  stack?: string
}

export interface BridgeResponse<T = unknown> {
  success: boolean
  data?: T
  error?: BridgeErrorDetail
}

// Helper function
export function isErrorCode(response: BridgeResponse, code: ErrorCode): boolean {
  return !response.success && response.error?.code === code
}
```

---

### 12. Test Organization: Consolidate Fixtures

**Problem:**
- `state` fixture duplicated in 4 test files (already in conftest.py)
- 10+ variations of brand directory fixtures with inconsistent naming
- `test_advisor_tools.py` is 3,073 lines (should be split)

**Files affected:**
- `tests/conftest.py`
- `tests/test_asset_service.py`
- `tests/test_brand_service.py`
- `tests/test_document_service.py`
- `tests/test_other_services.py`
- `tests/test_advisor_tools.py`

**Current Duplication:**
```python
# In test_asset_service.py (line 15)
@pytest.fixture
def state():
    return BridgeState()

# Same fixture in test_brand_service.py (line 18)
# Same fixture in test_document_service.py (line 12)
# Same fixture in test_other_services.py (line 20)
# Already exists in conftest.py!
```

**Brand directory fixtures (inconsistent naming):**
```python
# test_asset_service.py
@pytest.fixture
def mock_brand_dir(tmp_path):
    ...

# test_brands_storage.py
@pytest.fixture
def temp_brands_dir(tmp_path):
    ...

# test_session_manager.py
@pytest.fixture
def tmp_brand_dir(tmp_path):
    ...
```

**Solution:**

```python
# tests/conftest.py - consolidated fixtures

import pytest
from pathlib import Path
from sip_studio.studio.state import BridgeState

# ============================================================
# State Fixtures
# ============================================================

@pytest.fixture
def bridge_state():
    """Create a fresh BridgeState for testing."""
    return BridgeState()

# Alias for backward compatibility
@pytest.fixture
def state(bridge_state):
    """Alias for bridge_state (deprecated, use bridge_state)."""
    return bridge_state


# ============================================================
# Brand Directory Fixtures
# ============================================================

@pytest.fixture
def brands_root(tmp_path, monkeypatch) -> Path:
    """
    Create and patch the brands root directory.

    All brand operations will use this temporary directory.
    """
    brands_dir = tmp_path / ".sip-studio" / "brands"
    brands_dir.mkdir(parents=True)

    # Patch the get_brands_dir function
    monkeypatch.setattr(
        "sip_studio.brands.storage.base.get_brands_dir",
        lambda: brands_dir
    )

    # Create empty index
    (brands_dir / "index.json").write_text('{"version": "1.0", "brands": []}')

    return brands_dir


@pytest.fixture
def brand_dir(brands_root) -> Path:
    """
    Create a test brand directory with standard structure.

    Creates: test-brand/ with assets/, docs/, products/, projects/
    """
    brand_path = brands_root / "test-brand"
    brand_path.mkdir()

    # Create standard subdirectories
    (brand_path / "assets").mkdir()
    (brand_path / "docs").mkdir()
    (brand_path / "products").mkdir()
    (brand_path / "projects").mkdir()
    (brand_path / "style_references").mkdir()

    # Create minimal identity
    identity = {
        "slug": "test-brand",
        "name": "Test Brand",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    (brand_path / "identity.json").write_text(json.dumps(identity))

    return brand_path


@pytest.fixture
def brand_dir_with_assets(brand_dir) -> Path:
    """Brand directory with sample assets."""
    assets_dir = brand_dir / "assets"

    # Create sample image (1x1 white PNG)
    sample_png = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        # ... minimal valid PNG data
    ])
    (assets_dir / "sample.png").write_bytes(sample_png)
    (assets_dir / "logo.png").write_bytes(sample_png)

    return brand_dir


# ============================================================
# Service Fixtures
# ============================================================

@pytest.fixture
def asset_service(bridge_state):
    """Create AssetService with fresh state."""
    from sip_studio.studio.services.asset_service import AssetService
    return AssetService(bridge_state)


@pytest.fixture
def brand_service(bridge_state):
    """Create BrandService with fresh state."""
    from sip_studio.studio.services.brand_service import BrandService
    return BrandService(bridge_state)


@pytest.fixture
def document_service(bridge_state):
    """Create DocumentService with fresh state."""
    from sip_studio.studio.services.document_service import DocumentService
    return DocumentService(bridge_state)


# ============================================================
# Test Utilities
# ============================================================

@pytest.fixture
def set_active_brand(bridge_state):
    """Factory fixture to set active brand on state."""
    def _set_brand(slug: str):
        bridge_state.active_brand_slug = slug
    return _set_brand
```

**Split test_advisor_tools.py:**
```
tests/advisor/tools/
├── __init__.py
├── test_file_tools.py      # File read/write/list tests
├── test_image_tools.py     # Image generation tests
├── test_product_tools.py   # Product CRUD tests
├── test_project_tools.py   # Project CRUD tests
├── test_brand_tools.py     # Brand management tests
├── test_style_tools.py     # Style reference tests
├── test_session_tools.py   # Session management tests
└── conftest.py             # Shared fixtures for advisor tools
```

---

## 🟢 LOWER PRIORITY (Nice to Have)

### 13. Type Hints Standardization

**Problem:** Mix of legacy and modern type hint syntax across model files.

**Examples:**
```python
# Legacy (pre-3.9)
from typing import List, Dict, Optional
def get_items() -> List[str]: ...

# Modern (3.9+)
def get_items() -> list[str]: ...
```

**Solution:** Add `from __future__ import annotations` to all files and use modern syntax:

```python
# At top of each model file
from __future__ import annotations

# Then use modern syntax
def get_items() -> list[str]: ...
def get_config() -> dict[str, Any]: ...
def find_item(slug: str) -> Item | None: ...
```

---

### 14. Field Naming Consistency

**Problem:** Inconsistent naming for similar fields across models.

**Examples:**
- Datetime fields: `created_at` vs `generated_at` vs `last_confirmed` vs `timestamp`
- ID fields: `slug` vs `id` used inconsistently
- Name fields: `name` vs `title` vs `label`

**Recommendation:** Create a naming convention guide:

```python
# Naming Conventions for Pydantic Models

# Identifiers
slug: str          # URL-safe unique identifier (kebab-case)
id: str            # UUID or external ID (only for external systems)

# Timestamps (always use _at suffix)
created_at: datetime
updated_at: datetime
deleted_at: datetime | None
generated_at: datetime  # For generated content
expires_at: datetime | None

# Human-readable names
name: str          # Primary display name
title: str         # Only for titled content (articles, projects)
label: str         # Only for UI labels

# Descriptions
description: str   # Short description (1-2 sentences)
summary: str       # Longer summary (paragraph)
content: str       # Full content (unlimited)
```

---

### 15. Style Reference Models: Extract Validator Mixin

**Problem:** 40+ field validators with identical patterns in `style_reference.py`.

**Current Pattern:**
```python
class StyleReferenceFull(BaseModel):
    # ... many fields ...

    @field_validator("primary_colors", mode="before")
    @classmethod
    def normalize_primary_colors(cls, v):
        if v is None:
            return []
        return [c.strip().lower() for c in v if c and c.strip()]

    @field_validator("secondary_colors", mode="before")
    @classmethod
    def normalize_secondary_colors(cls, v):
        if v is None:
            return []
        return [c.strip().lower() for c in v if c and c.strip()]

    # ... 38 more nearly identical validators
```

**Solution:** Create reusable validators:

```python
# src/sip_studio/brands/models/validators.py
from typing import Any
from pydantic import field_validator

def normalize_string_list(v: Any) -> list[str]:
    """Normalize a list of strings: strip, lowercase, remove empty."""
    if v is None:
        return []
    if isinstance(v, str):
        return [v.strip().lower()] if v.strip() else []
    return [s.strip().lower() for s in v if s and s.strip()]

def normalize_string(v: Any) -> str:
    """Normalize a single string: strip whitespace."""
    if v is None:
        return ""
    return str(v).strip()

def normalize_color_list(v: Any) -> list[str]:
    """Normalize color values: strip, lowercase, validate format."""
    colors = normalize_string_list(v)
    # Could add hex color validation here
    return colors


# Usage in model:
class StyleReferenceFull(BaseModel):
    primary_colors: list[str] = Field(default_factory=list)
    secondary_colors: list[str] = Field(default_factory=list)

    # Single validator for all color fields
    @field_validator(
        "primary_colors", "secondary_colors", "accent_colors", "background_colors",
        mode="before"
    )
    @classmethod
    def normalize_colors(cls, v):
        return normalize_color_list(v)

    # Single validator for all string list fields
    @field_validator(
        "typography_fonts", "keywords", "tags", "themes",
        mode="before"
    )
    @classmethod
    def normalize_string_lists(cls, v):
        return normalize_string_list(v)
```

---

### 16. Frontend: Split useChat Hook

**Problem:** `useChat.ts` is 668 lines handling multiple concerns:
- Message management
- Attachment handling
- Generation state (todos, progress, thinking steps)
- Session management
- Image batch handling

**Solution:** Split into focused hooks:

```typescript
// src/hooks/chat/useChatMessages.ts
export function useChatMessages(sessionId: string | null) {
  // Message CRUD, history loading
  return { messages, addMessage, clearMessages, loadHistory }
}

// src/hooks/chat/useChatAttachments.ts
export function useChatAttachments() {
  // Attachment management
  return { attachments, addAttachment, removeAttachment, clearAttachments }
}

// src/hooks/chat/useChatGeneration.ts
export function useChatGeneration() {
  // Generation state: thinking steps, todos, progress
  return { thinkingSteps, todos, isGenerating, progress }
}

// src/hooks/chat/useChat.ts - Composition hook
export function useChat() {
  const messages = useChatMessages(sessionId)
  const attachments = useChatAttachments()
  const generation = useChatGeneration()

  // Combine and add send functionality
  const sendMessage = async (content: string) => {
    // Coordinate between sub-hooks
  }

  return {
    ...messages,
    ...attachments,
    ...generation,
    sendMessage,
  }
}
```

---

### 17. Add Missing Service Tests

**Problem:** Only 4 of 12 services have dedicated test files.

**Current Coverage:**
| Service | Has Tests |
|---------|-----------|
| asset_service | ✅ |
| brand_service | ✅ |
| document_service | ✅ |
| image_status | ✅ |
| chat_service | ❌ |
| product_service | ❌ |
| project_service | ❌ |
| quick_generator_service | ❌ |
| session_service | ❌ |
| style_reference_service | ❌ |
| update_service | ❌ |
| sample_brand_service | ❌ |

**Recommendation:** Add test files for all services following the existing pattern:

```python
# tests/studio/test_chat_service.py
import pytest
from sip_studio.studio.services.chat_service import ChatService

class TestChatService:
    @pytest.fixture
    def service(self, bridge_state, brand_dir):
        return ChatService(bridge_state)

    async def test_chat_requires_active_brand(self, service):
        result = await service.chat("Hello", [])
        assert not result["success"]
        assert "No active brand" in result["error"]

    async def test_chat_with_message(self, service, set_active_brand):
        set_active_brand("test-brand")
        result = await service.chat("Generate a logo", [])
        assert result["success"]

    # ... more tests
```

---

## Summary Table

| Area | Issues Found | Est. LOC Savings | Priority |
|------|-------------|------------------|----------|
| Storage Layer | Duplicate CRUD patterns | ~400 | 🔴 High |
| Advisor Tools | Duplicate utilities | ~200 | 🔴 High |
| Services Layer | Duplicate validation | ~150 | 🔴 High |
| Video Generators | Duplicate logic | ~300 | 🔴 High |
| Pydantic Models | Duplicate index patterns | ~100 | 🔴 High |
| Bridge/Async | Event loop issues | - (bug fix) | 🔴 High |
| Configuration | Scattered constants | ~50 | 🟡 Medium |
| Frontend Hooks | Duplicate patterns | ~300 | 🟡 Medium |
| ChatService | Complex method | ~100 | 🟡 Medium |
| Image Tools | 900-line function | ~200 | 🟡 Medium |
| Error Handling | Inconsistent formats | - (quality) | 🟡 Medium |
| Tests | Duplicate fixtures | ~100 | 🟡 Medium |
| Type Hints | Legacy syntax | - (quality) | 🟢 Low |
| Field Naming | Inconsistent | - (quality) | 🟢 Low |
| Validators | Duplicate patterns | ~50 | 🟢 Low |
| useChat Hook | Too large | ~100 | 🟢 Low |
| Test Coverage | Missing services | - (quality) | 🟢 Low |
| **Total** | | **~2,050** | |

---

## Recommended Refactoring Order

### Phase 1: Foundation (Highest Impact)
1. Create `BaseEntityStorage` for storage layer
2. Extract advisor tool utilities to shared module
3. Create `BrandAwareService` base class
4. Fix async event loop pattern in bridge

### Phase 2: Code Quality
5. Extract shared video generator logic to base class
6. Create generic `BaseIndex` for Pydantic models
7. Centralize configuration constants
8. Standardize error handling with `BridgeError`

### Phase 3: Frontend
9. Create reusable React hooks (`useBridgeCall`, `useEditableData`, `useFormState`)
10. Extract file utilities to shared module
11. Split `useChat` into focused sub-hooks

### Phase 4: Testing & Cleanup
12. Consolidate test fixtures in conftest.py
13. Split large test files
14. Add missing service tests
15. Standardize type hints and field naming

---

## Getting Started

To begin refactoring, I recommend starting with the highest-impact items that have clear, isolated changes:

1. **Start with #2 (Advisor Tools utilities)** - Small, self-contained change
2. **Then #6 (Pydantic BaseIndex)** - Also self-contained, improves all index classes
3. **Then #3 (BrandAwareService)** - Reduces service boilerplate

These changes can be made incrementally without breaking existing functionality, and each one provides immediate benefits.

---

*Document generated by Claude Code review on January 16, 2026*
