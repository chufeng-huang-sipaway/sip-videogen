"""Tests for UserPreferences config.json merge behavior.

Brand Studio stores API keys and update settings in ~/.sip-videogen/config.json.
Video infra stores user preferences in the same file. Saving video preferences
must not overwrite Brand Studio keys.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from sip_videogen.config.user_preferences import UserPreferences
from sip_videogen.generators.base import VideoProvider


def test_user_preferences_save_merges_existing_config(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "api_keys": {"openai": "sk-test", "gemini": "gm-test"},
                "update_check_on_startup": True,
                "last_update_check": 123,
            }
        )
    )

    prefs = UserPreferences(default_video_provider=VideoProvider.SORA)

    with patch.object(UserPreferences, "get_config_path", return_value=cfg):
        prefs.save()

    merged = json.loads(cfg.read_text())
    assert merged["api_keys"]["openai"] == "sk-test"
    assert merged["api_keys"]["gemini"] == "gm-test"
    assert merged["update_check_on_startup"] is True
    assert merged["last_update_check"] == 123
    assert merged["default_video_provider"] == "sora"


def test_user_preferences_load_ignores_extra_keys(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "api_keys": {"openai": "sk-test", "gemini": "gm-test"},
                "default_video_provider": "kling",
                "kling": {"model_version": "2.6", "mode": "pro"},
                "unknown_future_key": {"foo": "bar"},
            }
        )
    )

    with patch.object(UserPreferences, "get_config_path", return_value=cfg):
        loaded = UserPreferences.load()

    assert loaded.default_video_provider == VideoProvider.KLING
    assert loaded.kling.model_version == "2.6"
    assert loaded.kling.mode == "pro"
