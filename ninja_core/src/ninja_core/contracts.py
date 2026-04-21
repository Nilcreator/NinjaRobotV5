from __future__ import annotations

import uuid
from typing import Any, Mapping

PROTOCOL_VERSION = "blockly-v1"
WORKSPACE_FORMAT = "blockly-json"
DEFAULT_GENERATOR_VERSION = "web-blockly-v1"
DEFAULT_CODE_PREVIEW_LENGTH = 120


def build_execution_manifest(
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "generator_version": DEFAULT_GENERATOR_VERSION,
        "workspace_format": WORKSPACE_FORMAT,
    }
    if manifest:
        payload.update({key: value for key, value in manifest.items() if value is not None})
    return payload


def ensure_request_id(command: Mapping[str, Any], prefix: str | None = None) -> str:
    request_id = command.get("request_id")
    if request_id:
        return str(request_id)

    resolved_prefix = prefix or str(command.get("type", "req"))
    return f"{resolved_prefix}-{uuid.uuid4().hex[:12]}"


def build_execute_received_event(
    request_id: str,
    code: str,
    workspace_state: Mapping[str, Any] | None = None,
    *,
    include_full_code: bool = True,
) -> dict[str, Any]:
    event = {
        "type": "execute_received",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "code_length": len(code),
        "code_preview": code[:DEFAULT_CODE_PREVIEW_LENGTH],
        "workspace_received": workspace_state is not None,
    }
    if include_full_code:
        event["full_code"] = code
    return event


def build_execution_status_event(
    request_id: str,
    status: str,
    message: str = "",
) -> dict[str, Any]:
    return {
        "type": "execution_status",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "status": status,
        "message": message,
    }


def build_execution_log_event(
    request_id: str | None,
    content: str,
    stream: str = "stdout",
) -> dict[str, Any]:
    return {
        "type": "execution_log",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "stream": stream,
        "content": content,
    }


def build_chat_event(
    text: str,
    *,
    sender: str,
    request_id: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    return {
        "type": "chat",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "sender": sender,
        "text": text,
        "category": category,
    }


def build_error_event(
    code: str,
    message: str,
    *,
    request_id: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "type": "error",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "code": code,
        "message": message,
    }
    if details:
        event["details"] = dict(details)
    return event
