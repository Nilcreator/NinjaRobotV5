from ninja_core.contracts import (
    PROTOCOL_VERSION,
    build_error_event,
    build_execution_log_event,
    build_execution_manifest,
    build_execute_received_event,
    ensure_request_id,
)


def test_build_execution_manifest_defaults_and_overrides():
    manifest = build_execution_manifest({"generator_version": "web-blockly-v2"})

    assert manifest == {
        "protocol_version": PROTOCOL_VERSION,
        "generator_version": "web-blockly-v2",
        "workspace_format": "blockly-json",
    }


def test_ensure_request_id_reuses_existing_value():
    request_id = ensure_request_id({"type": "execute", "request_id": "req-123"})

    assert request_id == "req-123"


def test_build_execute_received_event_uses_preview_and_workspace_flag():
    code = 'print("hello")\n' * 20
    event = build_execute_received_event("req-123", code, {"blocks": []})

    assert event["type"] == "execute_received"
    assert event["protocol_version"] == PROTOCOL_VERSION
    assert event["request_id"] == "req-123"
    assert event["code_length"] == len(code)
    assert event["code_preview"] == code[:120]
    assert event["workspace_received"] is True
    assert event["full_code"] == code


def test_build_error_event_can_include_structured_details():
    event = build_error_event(
        "syntax_error",
        "Syntax error on line 3",
        request_id="exec-123",
        details={"line": 3, "offset": 2},
    )

    assert event["code"] == "syntax_error"
    assert event["details"] == {"line": 3, "offset": 2}


def test_build_execution_log_event_keeps_request_context():
    event = build_execution_log_event("req-456", "Hello from executor", stream="stderr")

    assert event == {
        "type": "execution_log",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": "req-456",
        "stream": "stderr",
        "content": "Hello from executor",
    }
