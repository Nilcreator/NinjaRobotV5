"""Google Gemini model discovery for interactive configuration flows."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GEMINI_MODELS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 15.0
MAX_MODEL_PAGES = 100


class GeminiModelDiscoveryError(RuntimeError):
    """Raised when available Gemini models cannot be retrieved safely."""


@dataclass(frozen=True)
class GeminiModelOption:
    """A Gemini model that can serve the NinjaRobot agent."""

    model_id: str
    display_name: str
    description: str
    input_token_limit: int | None = None
    output_token_limit: int | None = None


def _safe_optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _normalize_description(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _decode_response(response: Any) -> dict[str, Any]:
    try:
        payload = json.loads(response.read().decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, JSONDecodeError) as exc:
        raise GeminiModelDiscoveryError(
            "Google returned an invalid Gemini model response. Please try again."
        ) from exc

    if not isinstance(payload, dict):
        raise GeminiModelDiscoveryError(
            "Google returned an invalid Gemini model response. Please try again."
        )
    return payload


def _friendly_http_error(status_code: int) -> str:
    if status_code in {400, 401, 403}:
        return "The Gemini API key was rejected or is not authorized to list models."
    if status_code == 429:
        return "Gemini model lookup was rate limited. Please try again later."
    if status_code >= 500:
        return "Google's Gemini model service is temporarily unavailable."
    return f"Gemini model lookup failed with HTTP status {status_code}."


def _fetch_model_pages(
    api_key: str,
    *,
    timeout: float,
    opener: Callable[..., Any],
) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    page_token: str | None = None
    seen_tokens: set[str] = set()

    for _ in range(MAX_MODEL_PAGES):
        query = {"pageSize": "1000"}
        if page_token:
            query["pageToken"] = page_token
        request = Request(
            f"{GEMINI_MODELS_ENDPOINT}?{urlencode(query)}",
            headers={"x-goog-api-key": api_key, "Accept": "application/json"},
            method="GET",
        )

        try:
            with opener(request, timeout=timeout) as response:
                payload = _decode_response(response)
        except HTTPError as exc:
            raise GeminiModelDiscoveryError(_friendly_http_error(exc.code)) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise GeminiModelDiscoveryError(
                "Gemini model lookup timed out. Check the network and try again."
            ) from exc
        except URLError as exc:
            raise GeminiModelDiscoveryError(
                "Could not reach Google's Gemini model service. Check the network and try again."
            ) from exc
        except OSError as exc:
            raise GeminiModelDiscoveryError(
                "Could not reach Google's Gemini model service. Check the network and try again."
            ) from exc

        page_models = payload.get("models", [])
        if not isinstance(page_models, list):
            raise GeminiModelDiscoveryError(
                "Google returned an invalid Gemini model response. Please try again."
            )
        models.extend(model for model in page_models if isinstance(model, dict))

        next_page_token = payload.get("nextPageToken")
        if not next_page_token:
            return models
        if not isinstance(next_page_token, str) or next_page_token in seen_tokens:
            raise GeminiModelDiscoveryError(
                "Google returned an invalid Gemini model response. Please try again."
            )
        seen_tokens.add(next_page_token)
        page_token = next_page_token

    raise GeminiModelDiscoveryError(
        "Gemini model lookup returned too many pages. Please try again."
    )


def list_available_gemini_models(
    api_key: str,
    *,
    timeout: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    opener: Callable[..., Any] | None = None,
) -> list[GeminiModelOption]:
    """Return Gemini models available to the key that support generateContent."""
    normalized_key = api_key.strip()
    if not normalized_key:
        raise ValueError("Gemini API key cannot be empty.")
    if timeout <= 0:
        raise ValueError("Gemini model lookup timeout must be greater than zero.")

    raw_models = _fetch_model_pages(
        normalized_key,
        timeout=timeout,
        opener=opener or urlopen,
    )
    eligible: dict[str, GeminiModelOption] = {}

    for model in raw_models:
        resource_name = model.get("name")
        methods = model.get("supportedGenerationMethods", [])
        if (
            not isinstance(resource_name, str)
            or not resource_name.startswith("models/gemini-")
            or not isinstance(methods, list)
            or "generateContent" not in methods
        ):
            continue

        base_model_id = model.get("baseModelId")
        model_id = (
            base_model_id.strip()
            if isinstance(base_model_id, str) and base_model_id.strip()
            else resource_name.removeprefix("models/")
        )
        if not model_id.startswith("gemini-"):
            continue

        display_name = model.get("displayName")
        if not isinstance(display_name, str) or not display_name.strip():
            display_name = model_id

        eligible.setdefault(
            model_id,
            GeminiModelOption(
                model_id=model_id,
                display_name=" ".join(display_name.split()),
                description=_normalize_description(model.get("description")),
                input_token_limit=_safe_optional_int(model.get("inputTokenLimit")),
                output_token_limit=_safe_optional_int(model.get("outputTokenLimit")),
            ),
        )

    if not eligible:
        raise GeminiModelDiscoveryError(
            "No Gemini models supporting agent content generation were available for this key."
        )

    return sorted(
        eligible.values(),
        key=lambda model: (model.display_name.casefold(), model.model_id.casefold()),
    )


__all__ = [
    "GeminiModelDiscoveryError",
    "GeminiModelOption",
    "list_available_gemini_models",
]
