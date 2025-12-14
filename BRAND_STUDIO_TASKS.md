# Brand Studio - Development Task List

> **Version**: 1.3 (Implementation-ready)
> **Last Updated**: 2025-12-14

---

## Introduction

### Why We're Building This

The Brand Advisor is currently a powerful CLI-based AI agent that helps users create brand identities, generate logos, mascots, and marketing materials. However, **a terminal interface is not ideal for visual-heavy workflows**—users can't easily preview generated images, manage brand assets, or have a natural conversation with the agent.

We're building **Brand Studio**, a native macOS desktop application that wraps the existing Brand Advisor agent in a beautiful, intuitive GUI. This gives users:

1. **Brand file management** - Manage brand documents + images with drag-and-drop
2. **Conversational AI interface** - Chat with the Brand Advisor agent, see generated images inline
3. **Native macOS experience** - Glassmorphism styling, dark/light mode, drag-and-drop

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Brand Studio App                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              PyWebView (Native Window)                 │  │
│  │                                                        │  │
│  │  ┌─────────────┐  ┌─────────────────────────────────┐  │  │
│  │  │  Sidebar    │  │        Chat Panel               │  │  │
│  │  │  (React)    │  │        (React)                  │  │  │
│  │  │             │  │                                 │  │  │
│  │  │  - Brand    │  │  Messages from user and AI      │  │  │
│  │  │    selector │  │  Generated images inline        │  │  │
│  │  │  - Files    │  │  Progress indicators            │  │  │
│  │  │    tree     │  │                                 │  │  │
│  │  └─────────────┘  └─────────────────────────────────┘  │  │
│  │                                                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↕                                  │
│                   Python Bridge (bridge.py)                  │
│                           ↕                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           Existing Brand Advisor Agent                 │  │
│  │  - src/sip_videogen/advisor/agent.py                  │  │
│  │  - src/sip_videogen/advisor/tools.py                  │  │
│  │  - src/sip_videogen/brands/storage.py                 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. User types message in React chat UI
2. JavaScript calls Python function via PyWebView bridge
3. Python `StudioBridge` class invokes `BrandAdvisor.chat()`
4. Agent processes request, may call tools (generate_image, etc.)
5. Response returns through bridge to JavaScript
6. React UI updates with message and any generated images

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Window | PyWebView | Native macOS window with WebKit |
| Frontend | React + TypeScript | UI components |
| Build | Vite | Fast dev server and bundling |
| Components | shadcn/ui + Radix | Accessible, customizable UI |
| Styling | Tailwind CSS | Utility-first CSS |
| Backend | Python (existing) | Brand Advisor agent |
| Packaging | py2app | Create .app bundle |

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Brand file location | `~/.sip-videogen/brands/` | Consistency with existing CLI |
| **Supported file types (MVP)** | **Text** (md, txt, json, yaml/yml) + **Images** (png, jpg, jpeg, gif, webp, svg) | Keep scope small and predictable |
| Asset URL strategy | Base64 data URLs (thumbnails + inline chat images) | Avoids CORS issues between Vite dev server and file:// URLs |
| **Progress approach** | Blocking call + polling | **Caveat**: PyWebView may not allow concurrent JS→Python calls; test during implementation. If polling fails, fall back to no progress (just "Thinking...") |
| **API key persistence** | Session only (MVP) | Keys stored in `os.environ` for current session. **Future**: Use macOS Keychain via `keyring` library |
| State management | React Context | Shared brand state between Sidebar and ChatPanel |

### Actual Brand Models

> **CRITICAL**: Use correct field paths when accessing brand data.

```python
# BrandIdentityFull structure
identity = load_brand(slug)
name = identity.core.name                    # str
tagline = identity.core.tagline              # str
category = identity.positioning.market_category  # str

# BrandSummary (compact version) - has direct fields
summary = load_brand_summary(slug)
name = summary.name      # str
tagline = summary.tagline  # str
category = summary.category  # str
```

### Actual Brand Storage API

```python
# From src/sip_videogen/brands/storage.py
def get_brands_dir() -> Path           # ~/.sip-videogen/brands
def get_brand_dir(slug: str) -> Path   # ~/.sip-videogen/brands/{slug}
def list_brands() -> list[BrandIndexEntry]  # NOT list[str]!
def load_brand(slug: str) -> BrandIdentityFull | None
def load_brand_summary(slug: str) -> BrandSummary | None  # Faster, compact
def get_active_brand() -> str | None
def set_active_brand(slug: str | None) -> None

# BrandIndexEntry fields: slug, name, category, created_at, updated_at, last_accessed

# From src/sip_videogen/brands/memory.py
def list_brand_assets(slug: str, category: str | None = None) -> list[dict]
# Returns: [{"path": str, "category": str, "name": str, "filename": str}, ...]
# NOTE: Only returns image files, not text files

# For MVP document storage, Brand Studio will use:
# ~/.sip-videogen/brands/{slug}/docs/
# and will list/read/write documents directly via the Python bridge
# (restricted to allowed text extensions).
```

### Actual Asset Folder Structure

```
~/.sip-videogen/brands/{slug}/
├── assets/
│   ├── logo/           # Brand logos (images only)
│   ├── packaging/      # Packaging images
│   ├── lifestyle/      # Lifestyle photography
│   ├── mascot/         # Mascot images
│   ├── marketing/      # Marketing materials
│   └── generated/      # AI-generated assets
├── docs/               # User-provided brand documents (text only)
├── history/
├── identity.json       # L0 summary (BrandSummary)
└── identity_full.json  # L1 full identity (BrandIdentityFull)
```

### Directory Structure (Final)

```
src/sip_videogen/studio/
├── __init__.py
├── __main__.py            # Entry: python -m sip_videogen.studio
├── app.py                 # PyWebView window setup
├── bridge.py              # Python ↔ JS API
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── context/
        │   └── BrandContext.tsx   # Shared brand state
        ├── lib/
        │   ├── bridge.ts
        │   └── utils.ts
        ├── hooks/
        │   ├── useChat.ts
        │   ├── useAssets.ts
        │   ├── useDocuments.ts
        │   └── useTheme.ts
        └── components/
            ├── ui/
            ├── Sidebar/
            │   ├── index.tsx
            │   ├── BrandSelector.tsx
            │   ├── DocumentsList.tsx
            │   └── AssetTree.tsx
            ├── ChatPanel/
            │   ├── index.tsx
            │   ├── MessageList.tsx
            │   ├── MessageInput.tsx
            │   └── ImageMessage.tsx
            └── Setup/
                └── ApiKeySetup.tsx
```

---

## Task List

### Legend

- **Priority**: P0 (critical path), P1 (important), P2 (nice-to-have)
- **Depends On**: Tasks that must be completed first
- **Estimated Effort**: S (< 2 hours), M (2-4 hours), L (4-8 hours)

---

## Phase 1: Project Scaffolding

### Task 1.1: Create Studio Python Package Structure

**Priority**: P0
**Depends On**: None
**Estimated Effort**: S

#### What To Do

Create the basic Python package structure for the studio module.

#### Files to Create

**`src/sip_videogen/studio/__init__.py`**:
```python
"""Brand Studio - Native macOS app for Brand Advisor."""

__version__ = "0.1.0"
```

**`src/sip_videogen/studio/__main__.py`**:
```python
"""Entry point for: python -m sip_videogen.studio"""

from .app import main

if __name__ == "__main__":
    main()
```

**`src/sip_videogen/studio/app.py`**:
```python
"""PyWebView application setup."""

def main():
    print("Brand Studio - Coming soon!")

if __name__ == "__main__":
    main()
```

**`src/sip_videogen/studio/bridge.py`**:
```python
"""Python bridge exposed to JavaScript."""

class StudioBridge:
    """API exposed to the frontend via PyWebView."""
    pass
```

#### How to Verify

```bash
python -m sip_videogen.studio
# Output: Brand Studio - Coming soon!
```

---

### Task 1.2: Initialize React + Vite + TypeScript Frontend

**Priority**: P0
**Depends On**: Task 1.1
**Estimated Effort**: M

#### What To Do

Set up a React frontend using Vite.

#### Steps

```bash
cd src/sip_videogen/studio
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

#### Post-Setup

**Update `frontend/vite.config.ts`**:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
})
```

**Update `frontend/tsconfig.json`**:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

#### How to Verify

```bash
npm run dev    # Opens http://localhost:5173
npm run build  # Creates dist/
```

---

### Task 1.3: Add PyWebView and Create Window

**Priority**: P0
**Depends On**: Task 1.2
**Estimated Effort**: M

#### What To Do

Install PyWebView and create a native window.

#### Steps

```bash
pip install pywebview>=5.0
```

**`src/sip_videogen/studio/app.py`**:
```python
"""PyWebView application setup."""

import webview
import os
import sys
from pathlib import Path


def is_dev_mode() -> bool:
    return os.environ.get("STUDIO_DEV", "0") == "1"


def get_frontend_url() -> str:
    studio_dir = Path(__file__).parent
    if is_dev_mode():
        return "http://localhost:5173"
    else:
        dist_path = studio_dir / "frontend" / "dist" / "index.html"
        if not dist_path.exists():
            print("ERROR: Frontend not built.")
            print("Run: cd src/sip_videogen/studio/frontend && npm run build")
            sys.exit(1)
        return str(dist_path)


def main():
    from .bridge import StudioBridge

    api = StudioBridge()
    frontend = get_frontend_url()

    window = webview.create_window(
        title="Brand Studio",
        url=frontend,
        js_api=api,
        width=1400,
        height=900,
        min_size=(900, 600),
        resizable=True,
        frameless=False,
        text_select=True,
    )

    api._window = window
    webview.start(debug=is_dev_mode())


if __name__ == "__main__":
    main()
```

#### How to Verify

```bash
# Terminal 1
cd src/sip_videogen/studio/frontend && npm run dev

# Terminal 2
STUDIO_DEV=1 python -m sip_videogen.studio
```

---

### Task 1.4: Add Tailwind CSS

**Priority**: P0
**Depends On**: Task 1.2
**Estimated Effort**: S

#### Steps

```bash
cd src/sip_videogen/studio/frontend
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**`frontend/tailwind.config.js`**:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        sidebar: {
          light: 'rgba(246, 246, 246, 0.8)',
          dark: 'rgba(30, 30, 30, 0.8)',
        },
      },
    },
  },
  plugins: [],
}
```

**`frontend/src/index.css`**:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.2); border-radius: 4px; }
.dark ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); }

.glass {
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
```

---

### Task 1.5: Install and Configure shadcn/ui

**Priority**: P0
**Depends On**: Task 1.4
**Estimated Effort**: M

#### Steps

```bash
cd src/sip_videogen/studio/frontend
npx shadcn@latest init
# Choose: TypeScript=Yes, Style=Default, Base=Slate, CSS vars=Yes, RSC=No, Dir=src/components, Alias=@/

npx shadcn@latest add button input scroll-area dropdown-menu context-menu dialog tooltip separator alert

npm install lucide-react
```

---

### Task 1.6: Create Basic Two-Panel Layout

**Priority**: P0
**Depends On**: Task 1.5
**Estimated Effort**: M

#### What To Do

Create placeholder components for the layout.

**`src/components/Sidebar/index.tsx`**:
```tsx
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { BrandSelector } from './BrandSelector'
import { DocumentsList } from './DocumentsList'
import { AssetTree } from './AssetTree'

export function Sidebar() {
  return (
    <aside className="w-72 h-screen flex flex-col glass bg-sidebar-light dark:bg-sidebar-dark border-r border-gray-200/50 dark:border-gray-700/50">
      <div className="p-4 flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
          <span className="text-white text-sm font-bold">B</span>
        </div>
        <h1 className="text-lg font-semibold">Brand Studio</h1>
      </div>
      <Separator />
      <div className="p-4">
        <BrandSelector />
      </div>
      <Separator />
      <ScrollArea className="flex-1">
        <div className="p-4">
          <DocumentsList />
          <Separator className="my-4" />
          <AssetTree />
        </div>
      </ScrollArea>
    </aside>
  )
}
```

**`src/components/Sidebar/BrandSelector.tsx`** (placeholder):
```tsx
import { Button } from '@/components/ui/button'
import { ChevronDown } from 'lucide-react'

export function BrandSelector() {
  return (
    <Button variant="outline" className="w-full justify-between">
      <span>Select Brand...</span>
      <ChevronDown className="h-4 w-4" />
    </Button>
  )
}
```

**`src/components/Sidebar/AssetTree.tsx`** (placeholder):
```tsx
export function AssetTree() {
  return <div className="text-sm text-gray-500">No brand selected</div>
}
```

**`src/components/Sidebar/DocumentsList.tsx`** (placeholder):
```tsx
export function DocumentsList() {
  return <div className="text-sm text-gray-500">No documents</div>
}
```

**`src/components/ChatPanel/index.tsx`** (placeholder):
```tsx
import { ScrollArea } from '@/components/ui/scroll-area'

export function ChatPanel() {
  return (
    <main className="flex-1 flex flex-col h-screen bg-white dark:bg-gray-900">
      <ScrollArea className="flex-1">
        <div className="flex items-center justify-center h-full text-gray-500">
          Select a brand to start
        </div>
      </ScrollArea>
    </main>
  )
}
```

**`src/App.tsx`**:
```tsx
import { Sidebar } from '@/components/Sidebar'
import { ChatPanel } from '@/components/ChatPanel'

function App() {
  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Sidebar />
      <ChatPanel />
    </div>
  )
}

export default App
```

---

## Phase 2: Core Functionality

### Task 2.1: Implement Python Bridge API

**Priority**: P0
**Depends On**: Task 1.6
**Estimated Effort**: L

#### What To Do

Implement the Python bridge with **correct field access** and **consistent path safety**.

**`src/sip_videogen/studio/bridge.py`**:

```python
"""Python bridge exposed to JavaScript."""

import asyncio
import base64
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from sip_videogen.advisor.agent import BrandAdvisor, AdvisorProgress
from sip_videogen.brands.storage import (
    list_brands,
    load_brand_summary,
    get_active_brand,
    set_active_brand,
    get_brand_dir,
)
from sip_videogen.brands.memory import list_brand_assets


ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
ALLOWED_TEXT_EXTS = {".md", ".txt", ".json", ".yaml", ".yml"}


@dataclass
class BridgeResponse:
    success: bool
    data: Any = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class StudioBridge:
    """API exposed to the frontend via PyWebView."""

    def __init__(self):
        self._advisor: BrandAdvisor | None = None
        self._current_brand: str | None = None
        self._current_progress: str = ""
        self._generated_images: list[str] = []
        self._window = None

    # =========================================================================
    # Path Safety Helper
    # =========================================================================

    def _get_active_slug(self) -> str | None:
        """Get the active brand slug (bridge-local, falling back to global)."""
        return self._current_brand or get_active_brand()

    def _get_brand_dir(self) -> tuple[Path | None, str | None]:
        """Get the active brand directory."""
        slug = self._get_active_slug()
        if not slug:
            return None, "No brand selected"
        return get_brand_dir(slug), None

    def _resolve_in_dir(self, base_dir: Path, relative_path: str) -> tuple[Path | None, str | None]:
        """Resolve a path safely within a base directory (prevents path traversal)."""
        try:
            resolved = (base_dir / relative_path).resolve()
            if not resolved.is_relative_to(base_dir.resolve()):
                return None, "Invalid path: outside allowed directory"
            return resolved, None
        except (ValueError, OSError) as e:
            return None, f"Invalid path: {e}"

    def _resolve_assets_path(self, relative_path: str) -> tuple[Path | None, str | None]:
        """Resolve a path inside the brand's assets directory."""
        brand_dir, err = self._get_brand_dir()
        if err:
            return None, err
        return self._resolve_in_dir(brand_dir / "assets", relative_path)

    def _resolve_docs_path(self, relative_path: str) -> tuple[Path | None, str | None]:
        """Resolve a path inside the brand's docs directory."""
        brand_dir, err = self._get_brand_dir()
        if err:
            return None, err
        return self._resolve_in_dir(brand_dir / "docs", relative_path)

    # =========================================================================
    # Configuration / Setup
    # =========================================================================

    def check_api_keys(self) -> dict:
        """Check if required API keys are configured."""
        openai_key = bool(os.environ.get("OPENAI_API_KEY"))
        gemini_key = bool(os.environ.get("GEMINI_API_KEY"))
        return BridgeResponse(
            success=True,
            data={
                "openai": openai_key,
                "gemini": gemini_key,
                "all_configured": openai_key and gemini_key,
            }
        ).to_dict()

    def save_api_keys(self, openai_key: str, gemini_key: str) -> dict:
        """Save API keys to environment (session only).

        NOTE: Keys are not persisted. For a production app, consider:
        - macOS Keychain via `keyring` library
        - Encrypted config file in ~/Library/Application Support/
        """
        try:
            if openai_key:
                os.environ["OPENAI_API_KEY"] = openai_key
            if gemini_key:
                os.environ["GEMINI_API_KEY"] = gemini_key
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    # =========================================================================
    # Brand Management
    # =========================================================================

    def get_brands(self) -> dict:
        """Get list of all available brands."""
        try:
            entries = list_brands()
            brands = [
                {"slug": e.slug, "name": e.name, "category": e.category}
                for e in entries
            ]
            active = get_active_brand()
            return BridgeResponse(
                success=True,
                data={"brands": brands, "active": active}
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def set_brand(self, slug: str) -> dict:
        """Set the active brand and initialize advisor."""
        try:
            entries = list_brands()
            if slug not in [e.slug for e in entries]:
                return BridgeResponse(success=False, error=f"Brand '{slug}' not found").to_dict()

            set_active_brand(slug)
            self._current_brand = slug

            if self._advisor is None:
                self._advisor = BrandAdvisor(
                    brand_slug=slug,
                    progress_callback=self._progress_callback
                )
            else:
                self._advisor.set_brand(slug, preserve_history=False)

            self._generated_images = []
            return BridgeResponse(success=True, data={"slug": slug}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def get_brand_info(self, slug: str | None = None) -> dict:
        """Get detailed brand information.

        Uses BrandSummary for faster loading and correct field access.
        """
        try:
            target_slug = slug or self._current_brand or get_active_brand()
            if not target_slug:
                return BridgeResponse(success=False, error="No brand selected").to_dict()

            # Use BrandSummary for direct field access
            summary = load_brand_summary(target_slug)
            if not summary:
                return BridgeResponse(success=False, error=f"Brand '{target_slug}' not found").to_dict()

            return BridgeResponse(
                success=True,
                data={
                    "slug": target_slug,
                    "name": summary.name,
                    "tagline": summary.tagline,
                    "category": summary.category,
                }
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    # =========================================================================
    # Document Management (Text Files)
    # =========================================================================

    def get_documents(self, slug: str | None = None) -> dict:
        """List brand documents (text files) under docs/.

        Returns:
            {"success": True, "data": {"documents": [{"name": "...", "path": "...", "size": 123}, ...]}}
        """
        try:
            target_slug = slug or self._current_brand or get_active_brand()
            if not target_slug:
                return BridgeResponse(success=False, error="No brand selected").to_dict()

            docs_dir = get_brand_dir(target_slug) / "docs"
            if not docs_dir.exists():
                return BridgeResponse(success=True, data={"documents": []}).to_dict()

            documents: list[dict] = []
            for path in sorted(docs_dir.rglob("*")):
                if not path.is_file():
                    continue
                if path.name.startswith("."):
                    continue
                if path.suffix.lower() not in ALLOWED_TEXT_EXTS:
                    continue

                rel = str(path.relative_to(docs_dir))
                documents.append(
                    {
                        "name": path.name,
                        "path": rel,
                        "size": path.stat().st_size,
                    }
                )

            return BridgeResponse(success=True, data={"documents": documents}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def read_document(self, relative_path: str) -> dict:
        """Read a document's text content (read-only preview)."""
        try:
            resolved, error = self._resolve_docs_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Document not found").to_dict()

            if resolved.suffix.lower() not in ALLOWED_TEXT_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            # Basic safety limit to avoid returning huge files to the UI
            max_bytes = 512 * 1024  # 512 KB
            if resolved.stat().st_size > max_bytes:
                return BridgeResponse(
                    success=False,
                    error="Document too large to preview (limit: 512KB)",
                ).to_dict()

            content = resolved.read_text(encoding="utf-8", errors="replace")
            return BridgeResponse(
                success=True,
                data={"content": content},
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def open_document_in_finder(self, relative_path: str) -> dict:
        """Reveal a document in Finder."""
        import subprocess

        try:
            resolved, error = self._resolve_docs_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Document not found").to_dict()

            subprocess.run(["open", "-R", str(resolved)], check=True)
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def delete_document(self, relative_path: str) -> dict:
        """Delete a document file."""
        try:
            resolved, error = self._resolve_docs_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Document not found").to_dict()

            if resolved.is_dir():
                return BridgeResponse(success=False, error="Cannot delete folders").to_dict()

            resolved.unlink()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def rename_document(self, relative_path: str, new_name: str) -> dict:
        """Rename a document file."""
        try:
            resolved, error = self._resolve_docs_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Document not found").to_dict()

            if "/" in new_name or "\\" in new_name:
                return BridgeResponse(success=False, error="Invalid filename").to_dict()

            if Path(new_name).suffix.lower() not in ALLOWED_TEXT_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            new_path = resolved.parent / new_name
            if new_path.exists():
                return BridgeResponse(success=False, error=f"File already exists: {new_name}").to_dict()

            resolved.rename(new_path)
            brand_dir, err = self._get_brand_dir()
            if err:
                return BridgeResponse(success=False, error=err).to_dict()
            rel = str(new_path.relative_to(brand_dir / "docs"))
            return BridgeResponse(success=True, data={"newPath": rel}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def upload_document(self, filename: str, data_base64: str) -> dict:
        """Upload a document into docs/ (text-only)."""
        try:
            brand_dir, err = self._get_brand_dir()
            if err:
                return BridgeResponse(success=False, error=err).to_dict()

            if "/" in filename or "\\" in filename:
                return BridgeResponse(success=False, error="Invalid filename").to_dict()

            if Path(filename).suffix.lower() not in ALLOWED_TEXT_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            docs_dir = brand_dir / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            target_path = docs_dir / filename
            if target_path.exists():
                return BridgeResponse(success=False, error=f"File already exists: {filename}").to_dict()

            content = base64.b64decode(data_base64)
            target_path.write_bytes(content)

            return BridgeResponse(success=True, data={"path": filename}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    # =========================================================================
    # Asset Management (Images)
    # =========================================================================

    def get_assets(self, slug: str | None = None) -> dict:
        """Get asset tree for a brand.

        NOTE: Images are listed via list_brand_assets(). Documents are handled by get_documents().
        """
        try:
            target_slug = slug or self._current_brand or get_active_brand()
            if not target_slug:
                return BridgeResponse(success=False, error="No brand selected").to_dict()

            categories = ["logo", "packaging", "lifestyle", "mascot", "marketing", "generated"]
            tree = []

            for category in categories:
                assets = list_brand_assets(target_slug, category=category)
                children = []

                for asset in assets:
                    filename = asset["filename"]
                    file_path = Path(asset["path"])
                    size = file_path.stat().st_size if file_path.exists() else 0

                    children.append({
                        "name": filename,
                        "type": "image",
                        "path": f"{category}/{filename}",
                        "size": size,
                    })

                tree.append({
                    "name": category,
                    "type": "folder",
                    "path": category,
                    "children": children,
                })

            return BridgeResponse(success=True, data={"tree": tree}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def get_asset_thumbnail(self, relative_path: str) -> dict:
        """Get base64-encoded thumbnail for an asset."""
        try:
            resolved, error = self._resolve_assets_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            suffix = resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:
                return BridgeResponse(success=False, error="Unsupported file type").to_dict()

            # SVG: return as-is (thumbnailing SVG is non-trivial without extra deps)
            if suffix == ".svg":
                content = resolved.read_bytes()
                encoded = base64.b64encode(content).decode("utf-8")
                return BridgeResponse(
                    success=True,
                    data={"dataUrl": f"data:image/svg+xml;base64,{encoded}"},
                ).to_dict()

            # Raster images: generate a real thumbnail to reduce payload size
            import io
            from PIL import Image

            with Image.open(resolved) as img:
                img = img.convert("RGBA")
                img.thumbnail((256, 256))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode("utf-8")

            return BridgeResponse(
                success=True,
                data={"dataUrl": f"data:image/png;base64,{encoded}"},
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def open_asset_in_finder(self, relative_path: str) -> dict:
        """Open an asset in Finder."""
        import subprocess
        try:
            resolved, error = self._resolve_assets_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            subprocess.run(["open", "-R", str(resolved)], check=True)
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def delete_asset(self, relative_path: str) -> dict:
        """Delete an asset file."""
        try:
            resolved, error = self._resolve_assets_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            if resolved.is_dir():
                return BridgeResponse(success=False, error="Cannot delete folders").to_dict()

            resolved.unlink()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def rename_asset(self, relative_path: str, new_name: str) -> dict:
        """Rename an asset file."""
        try:
            resolved, error = self._resolve_assets_path(relative_path)
            if error:
                return BridgeResponse(success=False, error=error).to_dict()

            if not resolved.exists():
                return BridgeResponse(success=False, error="Asset not found").to_dict()

            if '/' in new_name or '\\' in new_name:
                return BridgeResponse(success=False, error="Invalid filename").to_dict()

            new_path = resolved.parent / new_name
            if new_path.exists():
                return BridgeResponse(success=False, error=f"File already exists: {new_name}").to_dict()

            resolved.rename(new_path)
            return BridgeResponse(
                success=True,
                data={"newPath": f"{resolved.parent.name}/{new_name}"}
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def upload_asset(self, filename: str, data_base64: str, category: str = "generated") -> dict:
        """Upload a file to brand's assets directory."""
        try:
            slug = self._current_brand or get_active_brand()
            if not slug:
                return BridgeResponse(success=False, error="No brand selected").to_dict()

            valid_categories = ["logo", "packaging", "lifestyle", "mascot", "marketing", "generated"]
            if category not in valid_categories:
                return BridgeResponse(success=False, error=f"Invalid category").to_dict()

            if '/' in filename or '\\' in filename:
                return BridgeResponse(success=False, error="Invalid filename").to_dict()

            brand_dir = get_brand_dir(slug)
            target_dir = brand_dir / "assets" / category
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / filename
            content = base64.b64decode(data_base64)
            target_path.write_bytes(content)

            return BridgeResponse(success=True, data={"path": f"{category}/{filename}"}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    # =========================================================================
    # Chat
    # =========================================================================

    def _progress_callback(self, progress: AdvisorProgress) -> None:
        """Called by BrandAdvisor during execution."""
        if progress.event_type == "thinking":
            self._current_progress = "Thinking..."
        elif progress.event_type == "tool_start":
            if "generate_image" in progress.message.lower():
                self._current_progress = "Generating image..."
            else:
                self._current_progress = progress.message
        elif progress.event_type == "tool_end":
            if progress.detail and progress.detail.endswith(('.png', '.jpg', '.jpeg')):
                self._generated_images.append(progress.detail)
            self._current_progress = ""

    def get_progress(self) -> dict:
        """Get current operation progress.

        NOTE: Polling may not work if PyWebView blocks concurrent calls.
        Test during implementation; fall back to static "Thinking..." if needed.
        """
        return BridgeResponse(success=True, data={"status": self._current_progress}).to_dict()

    def chat(self, message: str) -> dict:
        """Send a message to the Brand Advisor."""
        try:
            if self._advisor is None:
                active = get_active_brand()
                if active:
                    self._advisor = BrandAdvisor(
                        brand_slug=active,
                        progress_callback=self._progress_callback
                    )
                    self._current_brand = active
                else:
                    return BridgeResponse(success=False, error="No brand selected").to_dict()

            self._generated_images = []
            response = asyncio.run(self._advisor.chat(message))

            # Convert generated images to base64
            image_data_urls = []
            for img_path in self._generated_images:
                try:
                    path = Path(img_path)
                    if path.exists():
                        content = path.read_bytes()
                        encoded = base64.b64encode(content).decode('utf-8')
                        mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}.get(
                            path.suffix.lower().lstrip('.'), 'image/png'
                        )
                        image_data_urls.append(f"data:{mime};base64,{encoded}")
                except Exception:
                    pass

            return BridgeResponse(
                success=True,
                data={"response": response, "images": image_data_urls}
            ).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def clear_chat(self) -> dict:
        """Clear conversation history."""
        try:
            if self._advisor:
                self._advisor.clear_history()
            self._generated_images = []
            return BridgeResponse(success=True).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()

    def refresh_brand_memory(self) -> dict:
        """Refresh the agent's brand context."""
        try:
            slug = self._current_brand or get_active_brand()
            if not slug:
                return BridgeResponse(success=False, error="No brand selected").to_dict()

            if self._advisor is None:
                self._advisor = BrandAdvisor(
                    brand_slug=slug,
                    progress_callback=self._progress_callback
                )
            else:
                self._advisor.set_brand(slug, preserve_history=True)

            return BridgeResponse(success=True, data={"message": "Brand context refreshed"}).to_dict()
        except Exception as e:
            return BridgeResponse(success=False, error=str(e)).to_dict()
```

---

### Task 2.2: Create JavaScript Bridge Wrapper

**Priority**: P0
**Depends On**: Task 2.1
**Estimated Effort**: M

#### What To Do

Create typed TypeScript wrapper for the Python bridge.

**`src/lib/bridge.ts`**:

```typescript
interface BridgeResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export interface BrandEntry {
  slug: string
  name: string
  category: string
}

export interface AssetNode {
  name: string
  path: string
  type: 'folder' | 'image'
  children?: AssetNode[]
  size?: number
}

interface ApiKeyStatus {
  openai: boolean
  gemini: boolean
  all_configured: boolean
}

interface ChatResponse {
  response: string
  images: string[]
}

interface PyWebViewAPI {
  check_api_keys(): Promise<BridgeResponse<ApiKeyStatus>>
  save_api_keys(openai: string, gemini: string): Promise<BridgeResponse<void>>
  get_brands(): Promise<BridgeResponse<{ brands: BrandEntry[]; active: string | null }>>
  set_brand(slug: string): Promise<BridgeResponse<{ slug: string }>>
  get_brand_info(slug?: string): Promise<BridgeResponse<{ slug: string; name: string; tagline: string; category: string }>>
  get_assets(slug?: string): Promise<BridgeResponse<{ tree: AssetNode[] }>>
  get_asset_thumbnail(path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  open_asset_in_finder(path: string): Promise<BridgeResponse<void>>
  delete_asset(path: string): Promise<BridgeResponse<void>>
  rename_asset(path: string, newName: string): Promise<BridgeResponse<{ newPath: string }>>
  upload_asset(filename: string, data: string, category: string): Promise<BridgeResponse<{ path: string }>>
  get_progress(): Promise<BridgeResponse<{ status: string }>>
  chat(message: string): Promise<BridgeResponse<ChatResponse>>
  clear_chat(): Promise<BridgeResponse<void>>
  refresh_brand_memory(): Promise<BridgeResponse<{ message: string }>>
}

declare global {
  interface Window {
    pywebview?: { api: PyWebViewAPI }
  }
}

export function isPyWebView(): boolean {
  return typeof window !== 'undefined' && window.pywebview !== undefined
}

export function waitForPyWebView(): Promise<void> {
  return new Promise((resolve) => {
    if (isPyWebView()) return resolve()
    window.addEventListener('pywebviewready', () => resolve(), { once: true })
  })
}

async function callBridge<T>(method: () => Promise<BridgeResponse<T>>): Promise<T> {
  if (!isPyWebView()) throw new Error('Not running in PyWebView')
  const response = await method()
  if (!response.success) throw new Error(response.error || 'Unknown error')
  return response.data as T
}

export const bridge = {
  checkApiKeys: () => callBridge(() => window.pywebview!.api.check_api_keys()),
  saveApiKeys: (o: string, g: string) => callBridge(() => window.pywebview!.api.save_api_keys(o, g)),
  getBrands: () => callBridge(() => window.pywebview!.api.get_brands()),
  setBrand: (s: string) => callBridge(() => window.pywebview!.api.set_brand(s)),
  getBrandInfo: (s?: string) => callBridge(() => window.pywebview!.api.get_brand_info(s)),
  getAssets: async (s?: string) => (await callBridge(() => window.pywebview!.api.get_assets(s))).tree,
  getAssetThumbnail: async (p: string) => (await callBridge(() => window.pywebview!.api.get_asset_thumbnail(p))).dataUrl,
  openAssetInFinder: (p: string) => callBridge(() => window.pywebview!.api.open_asset_in_finder(p)),
  deleteAsset: (p: string) => callBridge(() => window.pywebview!.api.delete_asset(p)),
  renameAsset: async (p: string, n: string) => (await callBridge(() => window.pywebview!.api.rename_asset(p, n))).newPath,
  uploadAsset: async (f: string, d: string, c: string) => (await callBridge(() => window.pywebview!.api.upload_asset(f, d, c))).path,
  getProgress: async () => (await callBridge(() => window.pywebview!.api.get_progress())).status,
  chat: (m: string) => callBridge(() => window.pywebview!.api.chat(m)),
  clearChat: () => callBridge(() => window.pywebview!.api.clear_chat()),
  refreshBrandMemory: () => callBridge(() => window.pywebview!.api.refresh_brand_memory()),
}
```

---

### Task 2.3: Create BrandContext Provider

**Priority**: P0
**Depends On**: Task 2.2
**Estimated Effort**: M

#### What To Do

Create a React Context to share brand state between Sidebar and ChatPanel. This fixes the issue where `useBrands()` was instantiated twice with separate state.

**`src/context/BrandContext.tsx`**:

```tsx
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { bridge, isPyWebView, type BrandEntry } from '@/lib/bridge'

interface BrandContextType {
  brands: BrandEntry[]
  activeBrand: string | null
  isLoading: boolean
  error: string | null
  selectBrand: (slug: string) => Promise<void>
  refresh: () => Promise<void>
}

const BrandContext = createContext<BrandContextType | null>(null)

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brands, setBrands] = useState<BrandEntry[]>([])
  const [activeBrand, setActiveBrand] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      if (!isPyWebView()) {
        // Mock data for dev
        setBrands([
          { slug: 'summit-coffee', name: 'Summit Coffee', category: 'Coffee' },
          { slug: 'acme-corp', name: 'Acme Corp', category: 'Technology' },
        ])
        setActiveBrand('summit-coffee')
        return
      }
      const result = await bridge.getBrands()
      setBrands(result.brands)
      setActiveBrand(result.active)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load brands')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const selectBrand = useCallback(async (slug: string) => {
    setError(null)
    try {
      if (isPyWebView()) {
        await bridge.setBrand(slug)
      }
      setActiveBrand(slug)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select brand')
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <BrandContext.Provider value={{ brands, activeBrand, isLoading, error, selectBrand, refresh }}>
      {children}
    </BrandContext.Provider>
  )
}

export function useBrand() {
  const context = useContext(BrandContext)
  if (!context) {
    throw new Error('useBrand must be used within a BrandProvider')
  }
  return context
}
```

**Update `src/main.tsx`**:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { BrandProvider } from '@/context/BrandContext'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrandProvider>
      <App />
    </BrandProvider>
  </React.StrictMode>,
)
```

**Update `src/components/Sidebar/BrandSelector.tsx`**:

```tsx
import { ChevronDown, Plus, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useBrand } from '@/context/BrandContext'

export function BrandSelector() {
  const { brands, activeBrand, isLoading, selectBrand } = useBrand()
  const currentBrand = brands.find(b => b.slug === activeBrand)

  if (isLoading) {
    return (
      <Button variant="outline" className="w-full justify-between" disabled>
        Loading...
        <ChevronDown className="h-4 w-4" />
      </Button>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="w-full justify-between">
          <span className="truncate">{currentBrand?.name || 'Select Brand...'}</span>
          <ChevronDown className="h-4 w-4 ml-2" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56">
        {brands.length === 0 ? (
          <DropdownMenuItem disabled>No brands found</DropdownMenuItem>
        ) : (
          brands.map((brand) => (
            <DropdownMenuItem key={brand.slug} onClick={() => selectBrand(brand.slug)}>
              <span className="flex-1">{brand.name}</span>
              {brand.slug === activeBrand && <Check className="h-4 w-4 text-green-500" />}
            </DropdownMenuItem>
          ))
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled>
          <Plus className="h-4 w-4 mr-2" />
          Create New Brand
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
```

**Update `src/App.tsx`**:

```tsx
import { Sidebar } from '@/components/Sidebar'
import { ChatPanel } from '@/components/ChatPanel'
import { useBrand } from '@/context/BrandContext'

function App() {
  const { activeBrand } = useBrand()

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Sidebar />
      <ChatPanel brandSlug={activeBrand} />
    </div>
  )
}

export default App
```

---

### Task 2.4: Create useChat Hook

**Priority**: P0
**Depends On**: Task 2.2
**Estimated Effort**: M

#### What To Do

Create chat state management hook.

**`src/hooks/useChat.ts`**:

```typescript
import { useState, useCallback, useRef, useEffect } from 'react'
import { bridge, isPyWebView } from '@/lib/bridge'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  images: string[]
  timestamp: Date
  status: 'sending' | 'sent' | 'error'
  error?: string
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

export function useChat(brandSlug: string | null) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [error, setError] = useState<string | null>(null)
  const progressInterval = useRef<NodeJS.Timeout | null>(null)

  // Clear messages when brand changes
  useEffect(() => {
    setMessages([])
    setError(null)
  }, [brandSlug])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading || !brandSlug) return

    setError(null)
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: content.trim(),
      images: [],
      timestamp: new Date(),
      status: 'sent',
    }

    const assistantId = generateId()
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      images: [],
      timestamp: new Date(),
      status: 'sending',
    }

    setMessages(prev => [...prev, userMessage, assistantMessage])
    setIsLoading(true)

    // Try polling for progress (may not work due to PyWebView concurrency)
    if (isPyWebView()) {
      progressInterval.current = setInterval(async () => {
        try {
          const status = await bridge.getProgress()
          if (status) {
            setProgress(status)
            setMessages(prev => prev.map(m =>
              m.id === assistantId && m.status === 'sending'
                ? { ...m, content: status }
                : m
            ))
          }
        } catch {
          // Polling failed - this is expected if PyWebView blocks concurrent calls
          // Fall back to static "Thinking..."
          if (progressInterval.current) {
            clearInterval(progressInterval.current)
            progressInterval.current = null
          }
        }
      }, 500)
    }

    try {
      if (!isPyWebView()) {
        await new Promise(r => setTimeout(r, 1500))
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, content: `[Dev] Echo: ${content}`, status: 'sent' }
            : m
        ))
        return
      }

      const result = await bridge.chat(content)
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: result.response, images: result.images, status: 'sent' }
          : m
      ))
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(msg)
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: 'Sorry, something went wrong.', status: 'error', error: msg }
          : m
      ))
    } finally {
      if (progressInterval.current) {
        clearInterval(progressInterval.current)
        progressInterval.current = null
      }
      setProgress('')
      setIsLoading(false)
    }
  }, [isLoading, brandSlug])

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
    if (isPyWebView()) bridge.clearChat().catch(() => {})
  }, [])

  return { messages, isLoading, progress, error, sendMessage, clearMessages }
}
```

---

### Task 2.5: Implement ChatPanel Components

**Priority**: P0
**Depends On**: Task 2.4
**Estimated Effort**: M

*(Full implementation of ChatPanel/index.tsx, MessageList.tsx, MessageInput.tsx with image display and lightbox)*

---

### Task 2.6: Add First-Run Setup Screen

**Priority**: P1
**Depends On**: Task 2.2
**Estimated Effort**: M

*(Implementation of ApiKeySetup.tsx with session-only storage note)*

---

## Phase 3: Asset Manager

### Task 3.1: Create useAssets Hook

**Priority**: P0
**Depends On**: Task 2.2, Task 2.3
**Estimated Effort**: M

#### What To Do

Create a hook for managing asset tree state.

**`src/hooks/useAssets.ts`**:

```typescript
import { useState, useCallback, useEffect } from 'react'
import { bridge, isPyWebView, type AssetNode } from '@/lib/bridge'

export function useAssets(brandSlug: string | null) {
  const [tree, setTree] = useState<AssetNode[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!brandSlug) {
      setTree([])
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      if (!isPyWebView()) {
        // Mock data for dev
        setTree([
          {
            name: 'logo',
            type: 'folder',
            path: 'logo',
            children: [
              { name: 'primary.png', type: 'image', path: 'logo/primary.png', size: 24000 },
            ],
          },
          { name: 'mascot', type: 'folder', path: 'mascot', children: [] },
          { name: 'marketing', type: 'folder', path: 'marketing', children: [] },
          { name: 'lifestyle', type: 'folder', path: 'lifestyle', children: [] },
          { name: 'packaging', type: 'folder', path: 'packaging', children: [] },
          { name: 'generated', type: 'folder', path: 'generated', children: [] },
        ])
        return
      }

      const assets = await bridge.getAssets(brandSlug)
      setTree(assets)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assets')
    } finally {
      setIsLoading(false)
    }
  }, [brandSlug])

  const deleteAsset = useCallback(async (path: string) => {
    if (!isPyWebView()) return
    await bridge.deleteAsset(path)
    await refresh()
  }, [refresh])

  const renameAsset = useCallback(async (path: string, newName: string) => {
    if (!isPyWebView()) return
    await bridge.renameAsset(path, newName)
    await refresh()
  }, [refresh])

  const uploadAsset = useCallback(async (file: File, category: string) => {
    if (!isPyWebView()) return

    const reader = new FileReader()
    return new Promise<void>((resolve, reject) => {
      reader.onload = async () => {
        try {
          const base64 = (reader.result as string).split(',')[1]
          await bridge.uploadAsset(file.name, base64, category)
          await refresh()
          resolve()
        } catch (err) {
          reject(err)
        }
      }
      reader.onerror = () => reject(reader.error)
      reader.readAsDataURL(file)
    })
  }, [refresh])

  const refreshMemory = useCallback(async () => {
    if (!isPyWebView()) return
    await bridge.refreshBrandMemory()
  }, [])

  // Load on mount and when brand changes
  useEffect(() => {
    refresh()
  }, [refresh])

  return { tree, isLoading, error, refresh, deleteAsset, renameAsset, uploadAsset, refreshMemory }
}
```

---

### Task 3.2: Implement AssetTree Component

**Priority**: P0
**Depends On**: Task 3.1
**Estimated Effort**: M

#### What To Do

Implement the full AssetTree with folder expansion, thumbnails, and context menu.

**`src/components/Sidebar/AssetTree.tsx`**:

```tsx
import { useState, useCallback } from 'react'
import { ChevronRight, ChevronDown, Folder, Image, RefreshCw, Brain } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { useBrand } from '@/context/BrandContext'
import { useAssets } from '@/hooks/useAssets'
import { bridge, isPyWebView, type AssetNode } from '@/lib/bridge'

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface TreeItemProps {
  node: AssetNode
  depth?: number
  onDelete: (path: string) => void
  onRename: (path: string) => void
  onOpen: (path: string) => void
}

function TreeItem({ node, depth = 0, onDelete, onRename, onOpen }: TreeItemProps) {
  const [isOpen, setIsOpen] = useState(depth === 0)
  const hasChildren = node.type === 'folder' && node.children && node.children.length > 0

  const handleClick = () => {
    if (node.type === 'folder') {
      setIsOpen(!isOpen)
    }
  }

  const handleDoubleClick = () => {
    if (node.type === 'image') {
      onOpen(node.path)
    }
  }

  return (
    <div>
      <ContextMenu>
        <ContextMenuTrigger>
          <div
            className="flex items-center gap-1 py-1 px-2 rounded hover:bg-gray-200/50 dark:hover:bg-gray-700/50 cursor-pointer group"
            style={{ paddingLeft: `${depth * 12 + 8}px` }}
            onClick={handleClick}
            onDoubleClick={handleDoubleClick}
          >
            {node.type === 'folder' ? (
              isOpen ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />
            ) : (
              <span className="w-4" />
            )}
            {node.type === 'folder' ? (
              <Folder className="h-4 w-4 text-gray-500 shrink-0" />
            ) : (
              <Image className="h-4 w-4 text-gray-500 shrink-0" />
            )}
            <span className="text-sm truncate flex-1">{node.name}</span>
            {node.size && (
              <span className="text-xs text-gray-400 opacity-0 group-hover:opacity-100">
                {formatSize(node.size)}
              </span>
            )}
          </div>
        </ContextMenuTrigger>
        <ContextMenuContent>
          {node.type === 'image' && (
            <>
              <ContextMenuItem onClick={() => onOpen(node.path)}>
                Open in Finder
              </ContextMenuItem>
              <ContextMenuSeparator />
            </>
          )}
          {node.type === 'image' && (
            <>
              <ContextMenuItem onClick={() => onRename(node.path)}>
                Rename
              </ContextMenuItem>
              <ContextMenuItem onClick={() => onDelete(node.path)} className="text-red-600">
                Delete
              </ContextMenuItem>
            </>
          )}
        </ContextMenuContent>
      </ContextMenu>

      {isOpen && node.children?.map((child) => (
        <TreeItem
          key={child.path}
          node={child}
          depth={depth + 1}
          onDelete={onDelete}
          onRename={onRename}
          onOpen={onOpen}
        />
      ))}
    </div>
  )
}

export function AssetTree() {
  const { activeBrand } = useBrand()
  const { tree, isLoading, error, refresh, deleteAsset, refreshMemory } = useAssets(activeBrand)
  const [isDragging, setIsDragging] = useState(false)

  const handleOpen = useCallback(async (path: string) => {
    if (isPyWebView()) {
      await bridge.openAssetInFinder(path)
    }
  }, [])

  const handleDelete = useCallback(async (path: string) => {
    if (confirm(`Delete ${path}?`)) {
      await deleteAsset(path)
    }
  }, [deleteAsset])

  const handleRename = useCallback((path: string) => {
    const newName = prompt('New name:', path.split('/').pop())
    if (newName) {
      bridge.renameAsset(path, newName).then(refresh)
    }
  }, [refresh])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    if (!isPyWebView()) return

    const files = Array.from(e.dataTransfer.files)
    for (const file of files) {
      if (!file.type.startsWith('image/')) continue

      const reader = new FileReader()
      reader.onload = async () => {
        const base64 = (reader.result as string).split(',')[1]
        await bridge.uploadAsset(file.name, base64, 'generated')
        refresh()
      }
      reader.readAsDataURL(file)
    }
  }, [refresh])

  if (!activeBrand) {
    return <div className="text-sm text-gray-500">Select a brand</div>
  }

  if (error) {
    return (
      <div className="text-sm text-red-500">
        Error: {error}
        <Button variant="ghost" size="sm" onClick={refresh}>Retry</Button>
      </div>
    )
  }

  return (
    <div
      className={`space-y-2 ${isDragging ? 'bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-500 rounded' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Assets
        </h3>
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={refresh}
            disabled={isLoading}
            title="Refresh"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={refreshMemory}
            title="Refresh AI Memory"
          >
            <Brain className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {tree.length === 0 ? (
        <p className="text-sm text-gray-400 italic">
          {isLoading ? 'Loading...' : 'No assets yet. Drag images here to upload.'}
        </p>
      ) : (
        <div className="space-y-1">
          {tree.map((node) => (
            <TreeItem
              key={node.path}
              node={node}
              onDelete={handleDelete}
              onRename={handleRename}
              onOpen={handleOpen}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

---

### Task 3.3: Add Drag-and-Drop Upload

**Priority**: P1
**Depends On**: Task 3.2
**Estimated Effort**: S

#### What To Do

The drag-and-drop is already implemented in Task 3.2. This task is to add a visual drop zone indicator and category selection.

**Enhancements**:
1. Add a more prominent drop zone when dragging
2. When dropping on a specific folder, upload to that category
3. Show upload progress

*(Already mostly covered in 3.2 implementation)*

---

## Phase 4: Polish & Packaging

### Task 4.1: Implement Dark Mode

**Priority**: P1
**Estimated Effort**: S

Create `useTheme` hook that follows system preference.

---

### Task 4.2: Add Glassmorphism Styling

**Priority**: P2
**Estimated Effort**: M

Enhance sidebar with proper backdrop-filter blur.

---

### Task 4.3: Create py2app Configuration

**Priority**: P1
**Estimated Effort**: L

#### Important Notes

1. **Code signing** required for Gatekeeper ($99/year Apple Developer account)
2. **Notarization** required for macOS Catalina+
3. Frontend must be built and bundled correctly

---

### Task 4.4: Create DMG Installer

**Priority**: P2
**Depends On**: Task 4.3
**Estimated Effort**: M

---

## Appendix

### A. Testing Checklist

- [ ] App launches without errors
- [ ] Brand selector shows brands and switching works
- [ ] Chat sends messages and receives responses
- [ ] Generated images appear inline
- [ ] Asset tree shows folders and images
- [ ] Drag-and-drop upload works
- [ ] Delete/rename context menu works
- [ ] "Refresh Memory" button works
- [ ] Dark mode follows system

### B. File Types Supported (MVP)

**Images only**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`

Text file support (`md`, `txt`, `json`, `yaml`) is **out of scope** for MVP because `list_brand_assets()` only returns images.

### C. Known Limitations

1. **Progress polling**: May not work if PyWebView blocks concurrent calls. Falls back to static "Thinking..."
2. **API keys**: Session-only. Not persisted between app restarts.
3. **No text file management**: Only images are shown in the asset tree.

### D. Resources

- [PyWebView Documentation](https://pywebview.flowrl.com/)
- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [Apple Code Signing](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
