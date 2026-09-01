from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock
from unittest.mock import Mock

from ninja_core.config import NinjaConfig
from ninja_core.ninja_agent import NinjaAgent


def test_agent_and_capability_refresh_use_configured_model(monkeypatch):
    configured_keys = []
    created_models = []

    monkeypatch.setattr(
        "ninja_core.ninja_agent.genai.configure",
        lambda *, api_key: configured_keys.append(api_key),
    )

    def create_model(**kwargs):
        created_models.append(kwargs)
        return Mock()

    monkeypatch.setattr(
        "ninja_core.ninja_agent.genai.GenerativeModel",
        create_model,
    )
    monkeypatch.setattr(
        NinjaAgent,
        "_load_robot_capabilities",
        lambda self, config: {
            "movements": [],
            "actions": [],
            "faces": [],
            "sounds": [],
        },
    )

    config = NinjaConfig(
        api_keys={"gemini": "secret-key"},
        gemini={"model": "gemini-selected"},
    )
    agent = NinjaAgent(config, action_library=Mock())
    agent.refresh_capabilities()

    assert configured_keys == ["secret-key"]
    assert [call["model_name"] for call in created_models] == [
        "gemini-selected",
        "gemini-selected",
    ]
    assert created_models[0]["system_instruction"] == agent.system_prompt


def test_agent_uses_legacy_default_when_model_is_not_in_config(monkeypatch):
    created_models = []
    monkeypatch.setattr("ninja_core.ninja_agent.genai.configure", lambda **kwargs: None)
    monkeypatch.setattr(
        "ninja_core.ninja_agent.genai.GenerativeModel",
        lambda **kwargs: created_models.append(kwargs) or Mock(),
    )
    monkeypatch.setattr(
        NinjaAgent,
        "_load_robot_capabilities",
        lambda self, config: {
            "movements": [],
            "actions": [],
            "faces": [],
            "sounds": [],
        },
    )

    NinjaAgent(NinjaConfig(api_keys={"gemini": "secret-key"}), action_library=Mock())

    assert created_models[0]["model_name"] == "gemini-3-flash-preview"


def test_gemini_3_command_uses_bounded_thinking_compatible_runtime(monkeypatch):
    generate = AsyncMock(
        return_value='{"response": "Hello", "face_chain": [], "sound_chain": []}'
    )
    monkeypatch.setattr("ninja_core.ninja_agent.generate_content_text", generate)
    monkeypatch.setattr("ninja_core.ninja_agent.genai.configure", lambda **kwargs: None)
    monkeypatch.setattr(
        "ninja_core.ninja_agent.genai.GenerativeModel",
        lambda **kwargs: Mock(),
    )
    monkeypatch.setattr(
        NinjaAgent,
        "_load_robot_capabilities",
        lambda self, config: {
            "movements": [],
            "actions": [],
            "faces": [],
            "sounds": [],
        },
    )
    config = NinjaConfig(
        api_keys={"gemini": "secret-key"},
        gemini={"model": "gemini-3.7-flash"},
    )
    agent = NinjaAgent(config, action_library=Mock())

    result = asyncio.run(agent.process_command("hello"))

    assert result["response"] == "Hello"
    assert generate.await_count == 1
    assert generate.await_args.args[:3] == (
        "secret-key",
        "gemini-3.7-flash",
        [{"text": "hello"}],
    )
    assert generate.await_args.kwargs["system_instruction"] == agent.system_prompt


def test_gemini_3_failure_returns_visible_model_specific_message(monkeypatch):
    generate = AsyncMock(side_effect=TimeoutError("timed out"))
    monkeypatch.setattr("ninja_core.ninja_agent.generate_content_text", generate)
    monkeypatch.setattr("ninja_core.ninja_agent.genai.configure", lambda **kwargs: None)
    monkeypatch.setattr(
        "ninja_core.ninja_agent.genai.GenerativeModel",
        lambda **kwargs: Mock(),
    )
    monkeypatch.setattr(
        NinjaAgent,
        "_load_robot_capabilities",
        lambda self, config: {
            "movements": [],
            "actions": [],
            "faces": [],
            "sounds": [],
        },
    )
    config = NinjaConfig(
        api_keys={"gemini": "secret-key"},
        gemini={"model": "gemini-3.7-flash"},
    )
    agent = NinjaAgent(config, action_library=Mock())

    result = asyncio.run(agent.process_command("hello"))

    assert result["action_plan"] == {}
    assert "gemini-3.7-flash" in result["response"]
    assert "secret-key" not in result["response"]
    assert "TimeoutError" in result["log"]
