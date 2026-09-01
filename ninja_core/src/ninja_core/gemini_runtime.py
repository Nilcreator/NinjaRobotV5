"""Bounded Gemini REST generation for models unsupported by the legacy SDK."""

from __future__ import annotations

import asyncio
import json
import socket
from json import JSONDecodeError
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


GEMINI_API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GENERATION_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_OUTPUT_TOKENS = 2048
MODEL_VALIDATION_TIMEOUT_SECONDS = DEFAULT_GENERATION_TIMEOUT_SECONDS


class GeminiRuntimeError(RuntimeError):
    """Raised when a bounded Gemini generation request cannot complete."""


def requires_thinking_compatibility(model_name: str) -> bool:
    """Return whether the model needs thinking controls absent from the old SDK."""
    normalized = model_name.removeprefix("models/")
    parts = normalized.split("-")
    if len(parts) < 2 or parts[0] != "gemini":
        return False
    try:
        return int(parts[1].split(".", maxsplit=1)[0]) >= 3
    except ValueError:
        return False


def _friendly_http_error(status_code: int) -> str:
    if status_code in {400, 404}:
        return "The selected Gemini model rejected the generation request."
    if status_code in {401, 403}:
        return "The Gemini API key was rejected or cannot use the selected model."
    if status_code == 429:
        return "Gemini generation was rate limited. Please try again later."
    if status_code >= 500:
        return "Google's Gemini generation service is temporarily unavailable."
    return f"Gemini generation failed with HTTP status {status_code}."


def _decode_generation_response(response: Any) -> str:
    try:
        payload = json.loads(response.read().decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, JSONDecodeError) as exc:
        raise GeminiRuntimeError(
            "Google returned an invalid Gemini generation response."
        ) from exc

    if not isinstance(payload, dict):
        raise GeminiRuntimeError(
            "Google returned an invalid Gemini generation response."
        )

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise GeminiRuntimeError(
            "Gemini returned no response candidate for this request."
        )

    candidate = candidates[0]
    content = candidate.get("content", {}) if isinstance(candidate, dict) else {}
    parts = content.get("parts", []) if isinstance(content, dict) else []
    text_parts = [
        part["text"]
        for part in parts
        if isinstance(part, dict)
        and isinstance(part.get("text"), str)
        and not part.get("thought", False)
    ]
    text = "".join(text_parts).strip()
    if text:
        return text

    finish_reason = (
        candidate.get("finishReason") if isinstance(candidate, dict) else None
    )
    suffix = f" (finish reason: {finish_reason})" if finish_reason else ""
    raise GeminiRuntimeError(f"Gemini returned no visible response text{suffix}.")


def generate_content_text_sync(
    api_key: str,
    model_name: str,
    parts: list[dict[str, Any]],
    *,
    system_instruction: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    timeout: float = DEFAULT_GENERATION_TIMEOUT_SECONDS,
    opener: Callable[..., Any] = urlopen,
) -> str:
    """Generate text through REST with bounded latency and safe errors."""
    normalized_key = api_key.strip()
    normalized_model = model_name.removeprefix("models/").strip()
    if not normalized_key:
        raise ValueError("Gemini API key cannot be empty.")
    if not normalized_model.startswith("gemini-"):
        raise ValueError("Gemini model name must start with 'gemini-'.")
    if timeout <= 0:
        raise ValueError("Gemini generation timeout must be greater than zero.")
    if max_output_tokens <= 0:
        raise ValueError("Gemini output token limit must be greater than zero.")
    if not parts:
        raise ValueError("Gemini generation content cannot be empty.")

    generation_config: dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    if requires_thinking_compatibility(normalized_model):
        generation_config["thinkingConfig"] = {"thinkingLevel": "low"}

    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": generation_config,
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    request = Request(
        f"{GEMINI_API_ROOT}/models/{quote(normalized_model, safe='-._')}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-goog-api-key": normalized_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with opener(request, timeout=timeout) as response:
            return _decode_generation_response(response)
    except HTTPError as exc:
        raise GeminiRuntimeError(_friendly_http_error(exc.code)) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise GeminiRuntimeError(
            f"Gemini model '{normalized_model}' did not respond within {timeout:g} seconds."
        ) from exc
    except URLError as exc:
        raise GeminiRuntimeError(
            "Could not reach Google's Gemini generation service. Check the network."
        ) from exc
    except OSError as exc:
        raise GeminiRuntimeError(
            "Could not reach Google's Gemini generation service. Check the network."
        ) from exc


async def generate_content_text(
    api_key: str,
    model_name: str,
    parts: list[dict[str, Any]],
    *,
    system_instruction: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    timeout: float = DEFAULT_GENERATION_TIMEOUT_SECONDS,
) -> str:
    """Run the blocking REST request off the asyncio event loop."""
    return await asyncio.to_thread(
        generate_content_text_sync,
        api_key,
        model_name,
        parts,
        system_instruction=system_instruction,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        timeout=timeout,
    )


def validate_gemini_model(api_key: str, model_name: str) -> None:
    """Verify that a selected model can complete a minimal generation request."""
    response = generate_content_text_sync(
        api_key,
        model_name,
        [{"text": "Reply with exactly: OK"}],
        temperature=0.0,
        max_output_tokens=128,
        timeout=MODEL_VALIDATION_TIMEOUT_SECONDS,
    )
    if not response:
        raise GeminiRuntimeError(
            f"Gemini model '{model_name}' returned an empty validation response."
        )


__all__ = [
    "GeminiRuntimeError",
    "generate_content_text",
    "generate_content_text_sync",
    "requires_thinking_compatibility",
    "validate_gemini_model",
]
