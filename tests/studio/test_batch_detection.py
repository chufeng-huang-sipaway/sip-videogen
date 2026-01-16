from __future__ import annotations

from sip_studio.studio.services.batch_executor import BatchDetector
from sip_studio.studio.services.chat_service import ChatService
from sip_studio.studio.state import BridgeState


def test_batch_detector_accepts_bullet_list():
    history = [
        {
            "role": "assistant",
            "content": "- Idea A\n- Idea B\n- Idea C\n",
        }
    ]
    assert BatchDetector.is_batch_request("generate all of them", history) is True


def test_detect_idea_batch_request_parses_count():
    svc = ChatService(BridgeState())
    assert svc._detect_idea_batch_request("Give me 5 ideas and generate images for each") == 5
    assert svc._detect_idea_batch_request("Give me five ideas and generate images for each") == 5


def test_detect_idea_batch_request_requires_generate_and_images():
    svc = ChatService(BridgeState())
    assert svc._detect_idea_batch_request("Give me five ideas about a product") is None
    assert svc._detect_idea_batch_request("Generate an image of the product") is None
    assert svc._detect_idea_batch_request("I uploaded 5 images of the product") is None
    assert svc._detect_idea_batch_request("Generate 5 images of the product") == 5
    assert svc._detect_idea_batch_request("Give me 5 images of the product") == 5
    assert svc._detect_idea_batch_request("Show me some images of the product") == 5
