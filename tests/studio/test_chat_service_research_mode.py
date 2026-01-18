from __future__ import annotations

import pytest

from sip_studio.studio.services.chat_service import ChatService
from sip_studio.studio.state import BridgeState


class _DummyAdvisor:
    def __init__(self) -> None:
        self.called = False
        self.last_message: str | None = None
        self.last_kwargs: dict | None = None

    async def chat_with_metadata(self, message: str, **kwargs) -> dict:
        self.called = True
        self.last_message = message
        self.last_kwargs = kwargs
        return {"response": "ok", "interaction": None, "memory_update": None}


class _DummyImagePool:
    def cancel_batch(self, batch_id: str) -> int:  # noqa: ARG002
        return 0

    def cleanup_batch(self, batch_id: str) -> None:  # noqa: ARG002
        return None


@pytest.mark.parametrize(
    ("flags", "expected_header"),
    [
        ({"web_search_enabled": True}, "## Research Mode: Web Search Enabled"),
        ({"deep_research_enabled": True}, "## Research Mode: Deep Research Enabled"),
    ],
)
def test_research_mode_skips_batch_shortcuts(
    isolated_home, monkeypatch, flags: dict, expected_header: str
):
    state = BridgeState()
    state._cached_slug = "test-brand"
    state._cache_valid = True
    svc = ChatService(state)

    advisor = _DummyAdvisor()
    monkeypatch.setattr(svc, "_ensure_advisor", lambda: (advisor, None))

    async def _fail_plan(*_args, **_kwargs):
        raise AssertionError("IdeaPlanner.plan should not be called when research mode is enabled")

    import sip_studio.studio.services.chat_service as chat_service_mod

    monkeypatch.setattr(chat_service_mod.IdeaPlanner, "plan", _fail_plan)
    monkeypatch.setattr(chat_service_mod, "get_image_pool", lambda: _DummyImagePool())

    msg = "Give me 5 ideas and generate images for each"
    result = svc.chat(msg, **flags)

    assert result["success"] is True
    assert advisor.called is True
    assert advisor.last_message is not None
    assert expected_header in advisor.last_message


def test_deep_research_clarification_suppresses_text_response(isolated_home, monkeypatch):
    state = BridgeState()
    state._cached_slug = "test-brand"
    state._cache_valid = True
    svc = ChatService(state)

    advisor = _DummyAdvisor()
    monkeypatch.setattr(svc, "_ensure_advisor", lambda: (advisor, None))

    import sip_studio.studio.services.chat_service as chat_service_mod

    monkeypatch.setattr(chat_service_mod, "get_image_pool", lambda: _DummyImagePool())
    monkeypatch.setattr(
        chat_service_mod,
        "get_pending_research_clarification",
        lambda: {
            "type": "deep_research_clarification",
            "query": "test query",
            "contextSummary": "test context",
            "questions": [],
            "estimatedDuration": "15-20 minutes",
        },
    )

    result = svc.chat("Do deep research on this", deep_research_enabled=True)

    assert result["success"] is True
    assert result["data"]["response"] == ""
    assert result["data"]["research_clarification"]["type"] == "deep_research_clarification"
