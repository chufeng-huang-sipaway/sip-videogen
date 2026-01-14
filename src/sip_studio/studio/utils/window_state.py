"""Window state persistence for Sip Studio."""

import json
from pathlib import Path

from platformdirs import user_config_dir

from sip_studio.config.logging import get_logger

logger = get_logger(__name__)
_STATE_VERSION = 1
_DEFAULT_BOUNDS = {"x": 100, "y": 100, "width": 1400, "height": 900}
_DEFAULT_PANELS = {"sidebar": 240, "chat": 400}


def _get_state_path() -> Path:
    """Get path to window state file."""
    d = Path(user_config_dir("sip-studio", ensure_exists=True))
    return d / "window-state.json"


def _get_default_state() -> dict:
    """Return default window state."""
    return {
        "version": _STATE_VERSION,
        "bounds": _DEFAULT_BOUNDS.copy(),
        "isMaximized": False,
        "isFullscreen": False,
        "panelWidths": _DEFAULT_PANELS.copy(),
    }


def _clamp_to_visible(bounds: dict) -> dict:
    """Ensure window is visible on at least one monitor."""
    try:
        from screeninfo import get_monitors

        monitors = list(get_monitors())
    except Exception as e:
        logger.debug(f"screeninfo unavailable: {e}")
        return bounds
    if not monitors:
        return bounds
    x, y, w, h = (
        bounds.get("x", 0),
        bounds.get("y", 0),
        bounds.get("width", 800),
        bounds.get("height", 600),
    )
    # Check if window overlaps any monitor
    for m in monitors:
        if x < m.x + m.width and x + w > m.x and y < m.y + m.height and y + h > m.y:
            return bounds  # Visible, OK
    # Not visible on any monitor - center on primary
    primary = monitors[0]
    return {
        "x": primary.x + (primary.width - w) // 2,
        "y": primary.y + (primary.height - h) // 2,
        "width": w,
        "height": h,
    }


def load_window_state() -> dict:
    """Load and validate window state, return defaults on any error."""
    try:
        p = _get_state_path()
        if not p.exists():
            return _get_default_state()
        with open(p, "r") as f:
            state = json.load(f)
        if state.get("version") != _STATE_VERSION:
            logger.info("Window state version mismatch, using defaults")
            return _get_default_state()
        # Validate bounds
        bounds = state.get("bounds", {})
        if not all(k in bounds for k in ("x", "y", "width", "height")):
            bounds = _DEFAULT_BOUNDS.copy()
        state["bounds"] = _clamp_to_visible(bounds)
        # Ensure panelWidths exists
        if "panelWidths" not in state:
            state["panelWidths"] = _DEFAULT_PANELS.copy()
        return state
    except (json.JSONDecodeError, IOError, OSError) as e:
        logger.debug(f"Failed to load window state: {e}")
        return _get_default_state()


def save_window_state(state: dict) -> None:
    """Atomically save window state."""
    p = _get_state_path()
    tmp = p.with_suffix(".tmp")
    try:
        state["version"] = _STATE_VERSION
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        tmp.replace(p)  # Atomic rename
    except (IOError, OSError) as e:
        logger.debug(f"Failed to save window state: {e}")


def update_window_bounds(bounds: dict) -> None:
    """Update just the bounds in window state."""
    state = load_window_state()
    state["bounds"] = bounds
    save_window_state(state)


def update_panel_widths(widths: dict) -> None:
    """Update panel widths in window state."""
    state = load_window_state()
    state.setdefault("panelWidths", {}).update(widths)
    save_window_state(state)


def get_initial_window_config() -> tuple[int, int, int, int]:
    """Get initial window position and size. Returns (x, y, width, height)."""
    state = load_window_state()
    b = state.get("bounds", _DEFAULT_BOUNDS)
    return (b.get("x", 100), b.get("y", 100), b.get("width", 1400), b.get("height", 900))
