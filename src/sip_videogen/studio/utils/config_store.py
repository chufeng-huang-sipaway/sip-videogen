"""API key configuration storage."""

import json
import os
from pathlib import Path

from sip_videogen.utils.file_utils import write_atomically

# Config file for persistent settings (API keys, preferences)
CONFIG_PATH = Path.home() / ".sip-videogen" / "config.json"


def _load_config() -> dict:
    """Load config from disk."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(config: dict) -> None:
    """Save config to disk atomically with restrictive permissions (contains API keys)."""
    write_atomically(CONFIG_PATH, json.dumps(config, indent=2), mode=0o600)


def load_api_keys_from_config() -> None:
    """Load API keys from config into environment (called on startup)."""
    c = _load_config()
    keys = c.get("api_keys", {})
    if keys.get("openai") and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = keys["openai"]
    if keys.get("gemini") and not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = keys["gemini"]
    if keys.get("firecrawl") and not os.environ.get("FIRECRAWL_API_KEY"):
        os.environ["FIRECRAWL_API_KEY"] = keys["firecrawl"]


def save_api_keys(openai_key: str, gemini_key: str, firecrawl_key: str = "") -> None:
    """Save API keys to environment and persist to config file.
    Use '__KEEP__' as sentinel to keep existing value."""
    c = _load_config()
    ak = c.get("api_keys", {})
    # Resolve values (keep existing if __KEEP__ or empty)
    o = ak.get("openai", "") if openai_key in ("__KEEP__", "") else openai_key
    g = ak.get("gemini", "") if gemini_key in ("__KEEP__", "") else gemini_key
    f = ak.get("firecrawl", "") if firecrawl_key in ("__KEEP__", "") else firecrawl_key
    # Update environment
    if o:
        os.environ["OPENAI_API_KEY"] = o
    if g:
        os.environ["GEMINI_API_KEY"] = g
    if f:
        os.environ["FIRECRAWL_API_KEY"] = f
    c["api_keys"] = {"openai": o, "gemini": g, "firecrawl": f}
    _save_config(c)


def check_api_keys() -> dict[str, bool]:
    """Check if required API keys are configured."""
    o = bool(os.environ.get("OPENAI_API_KEY"))
    g = bool(os.environ.get("GEMINI_API_KEY"))
    f = bool(os.environ.get("FIRECRAWL_API_KEY"))
    return {"openai": o, "gemini": g, "firecrawl": f, "all_configured": o and g}
