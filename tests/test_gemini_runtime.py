from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from ninja_core.gemini_runtime import (
    GeminiRuntimeError,
    generate_content_text_sync,
    requires_thinking_compatibility,
)


class FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self._body


def test_gemini_3_generation_uses_low_thinking_and_never_puts_key_in_url():
    calls = []

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return FakeResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"thought": True, "text": "internal"},
                                {"text": "  visible response  "},
                            ]
                        }
                    }
                ]
            }
        )

    text = generate_content_text_sync(
        "super-secret-key",
        "gemini-3.7-flash",
        [{"text": "hello"}],
        system_instruction="system prompt",
        timeout=12,
        opener=opener,
    )

    request, timeout = calls[0]
    body = json.loads(request.data)
    assert text == "visible response"
    assert timeout == 12
    assert body["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}
    assert body["systemInstruction"]["parts"][0]["text"] == "system prompt"
    assert "super-secret-key" not in request.full_url
    assert dict(request.header_items())["X-goog-api-key"] == "super-secret-key"


def test_older_gemini_model_preserves_generation_without_thinking_config():
    bodies = []

    def opener(request, *, timeout):
        bodies.append(json.loads(request.data))
        return FakeResponse({"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})

    assert requires_thinking_compatibility("gemini-2.5-flash") is False
    assert requires_thinking_compatibility("gemini-3-flash-preview") is True
    assert requires_thinking_compatibility("gemini-3.7-flash") is True

    assert (
        generate_content_text_sync(
            "key", "gemini-2.5-flash", [{"text": "hello"}], opener=opener
        )
        == "OK"
    )
    assert "thinkingConfig" not in bodies[0]["generationConfig"]


def test_generation_timeout_is_bounded_and_redacts_key():
    def opener(request, *, timeout):
        raise TimeoutError

    with pytest.raises(
        GeminiRuntimeError, match="did not respond within 4 seconds"
    ) as exc:
        generate_content_text_sync(
            "super-secret-key",
            "gemini-3.7-flash",
            [{"text": "hello"}],
            timeout=4,
            opener=opener,
        )

    assert "super-secret-key" not in str(exc.value)


def test_generation_http_error_is_safe():
    def opener(request, *, timeout):
        raise HTTPError(request.full_url, 403, "forbidden", None, None)

    with pytest.raises(GeminiRuntimeError, match="API key was rejected") as exc:
        generate_content_text_sync(
            "super-secret-key",
            "gemini-3.7-flash",
            [{"text": "hello"}],
            opener=opener,
        )

    assert "super-secret-key" not in str(exc.value)


def test_generation_rejects_response_without_visible_text():
    def opener(request, *, timeout):
        return FakeResponse(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"thought": True, "text": "hidden"}]},
                        "finishReason": "MAX_TOKENS",
                    }
                ]
            }
        )

    with pytest.raises(GeminiRuntimeError, match="MAX_TOKENS"):
        generate_content_text_sync(
            "key",
            "gemini-3.7-flash",
            [{"text": "hello"}],
            opener=opener,
        )
