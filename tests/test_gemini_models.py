from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from ninja_core.gemini_models import (
    GeminiModelDiscoveryError,
    list_available_gemini_models,
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


def test_lists_paginated_generate_content_gemini_models_without_key_in_url():
    pages = iter(
        [
            {
                "models": [
                    {
                        "name": "models/gemini-zeta-001",
                        "baseModelId": "gemini-zeta",
                        "displayName": "Zeta Model",
                        "description": "  A capable   Gemini model. ",
                        "inputTokenLimit": 1000,
                        "outputTokenLimit": 200,
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemini-embedding-001",
                        "baseModelId": "gemini-embedding-001",
                        "displayName": "Embedding",
                        "supportedGenerationMethods": ["embedContent"],
                    },
                    {
                        "name": "models/chat-bison-001",
                        "baseModelId": "chat-bison",
                        "displayName": "Not Gemini",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                ],
                "nextPageToken": "page two",
            },
            {
                "models": [
                    {
                        "name": "models/gemini-alpha-002",
                        "displayName": "Alpha Model",
                        "supportedGenerationMethods": [
                            "countTokens",
                            "generateContent",
                        ],
                    },
                    {
                        "name": "models/gemini-zeta-002",
                        "baseModelId": "gemini-zeta",
                        "displayName": "Duplicate Zeta",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                ]
            },
        ]
    )
    calls = []

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return FakeResponse(next(pages))

    models = list_available_gemini_models(
        "super-secret-key",
        timeout=3.5,
        opener=opener,
    )

    assert [model.model_id for model in models] == [
        "gemini-alpha-002",
        "gemini-zeta",
    ]
    assert models[1].description == "A capable Gemini model."
    assert models[1].input_token_limit == 1000
    assert models[1].output_token_limit == 200
    assert len(calls) == 2
    assert calls[0][1] == 3.5
    assert "super-secret-key" not in calls[0][0].full_url
    assert dict(calls[0][0].header_items())["X-goog-api-key"] == "super-secret-key"
    assert "pageToken=page+two" in calls[1][0].full_url


@pytest.mark.parametrize(
    ("status_code", "message"),
    [
        (400, "rejected"),
        (403, "rejected"),
        (429, "rate limited"),
        (503, "temporarily unavailable"),
    ],
)
def test_http_errors_are_safe_and_actionable(status_code, message):
    def opener(request, *, timeout):
        raise HTTPError(
            request.full_url,
            status_code,
            "failure",
            hdrs=None,
            fp=BytesIO(),
        )

    with pytest.raises(GeminiModelDiscoveryError, match=message) as exc_info:
        list_available_gemini_models("super-secret-key", opener=opener)

    assert "super-secret-key" not in str(exc_info.value)


@pytest.mark.parametrize("error", [TimeoutError(), URLError("offline"), OSError()])
def test_network_failures_do_not_expose_the_key(error):
    def opener(request, *, timeout):
        raise error

    with pytest.raises(GeminiModelDiscoveryError) as exc_info:
        list_available_gemini_models("super-secret-key", opener=opener)

    assert "super-secret-key" not in str(exc_info.value)


def test_rejects_invalid_model_payload():
    def opener(request, *, timeout):
        return FakeResponse({"models": "not-a-list"})

    with pytest.raises(GeminiModelDiscoveryError, match="invalid"):
        list_available_gemini_models("key", opener=opener)


def test_rejects_repeated_pagination_token():
    def opener(request, *, timeout):
        return FakeResponse({"models": [], "nextPageToken": "same-token"})

    with pytest.raises(GeminiModelDiscoveryError, match="invalid"):
        list_available_gemini_models("key", opener=opener)


def test_rejects_empty_eligible_model_list():
    def opener(request, *, timeout):
        return FakeResponse(
            {
                "models": [
                    {
                        "name": "models/gemini-embedding-001",
                        "supportedGenerationMethods": ["embedContent"],
                    }
                ]
            }
        )

    with pytest.raises(GeminiModelDiscoveryError, match="No Gemini models"):
        list_available_gemini_models("key", opener=opener)


def test_rejects_blank_key_before_calling_google():
    called = False

    def opener(request, *, timeout):
        nonlocal called
        called = True

    with pytest.raises(ValueError, match="cannot be empty"):
        list_available_gemini_models("   ", opener=opener)

    assert called is False
