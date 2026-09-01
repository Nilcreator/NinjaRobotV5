---
type: Entity
title: ninja_core Package
description: Core application package containing HAL, dispatcher, web server, safe
  executor, and AI agent.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-readme-3
  resource: urn:llmwiki:source:src-20260822-readme-3
  title: ninja_core Readme
  content_hash: sha256:c13dcf9055a532fefb03664983e9b5bafcb384e7ff16b65feca801cdbff23ba5
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:26272dce2ec7dcab9f3181e1ce0621448ef12547ff26f3b7a0ac4fc50cef9b4d
- id: src-20260822-developmentlog
  resource: urn:llmwiki:source:src-20260822-developmentlog
  title: NinjaRobot V5 Development Log
  content_hash: sha256:503fe3ddfad6f04902d9b3a707a8be9d9da7c24eb9eae5b1dc5ea739225c5bc3
semantic_review:
  version: 1
  performed_by: agent:codex
  performed_at: '2026-09-01T07:28:37Z'
  target_hash: sha256:e2e7988a4be337247684bd1c51c4dddc394e02003ceb9857c06c38c488198b5b
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Core orchestration, configuration, web, AI, and runtime responsibilities align with current project
    documentation, including selected Gemini model behavior.
---

# ninja_core Package

`ninja_core` is the central orchestration package of NinjaRobot V5, binding hardware drivers, communication protocols, AI services, and web APIs into a cohesive runtime.[^src-20260822-readme-3] [^src-20260822-developmentguide]

## Module Inventory

| Module | Purpose |
|--------|---------|
| **`hal.py`** | Hardware Abstraction Layer with dynamic driver loading via `DRIVER_REGISTRY`.[^src-20260822-readme-3] |
| **`config.py`** | `NinjaConfig` manager for master `config.json`, robot naming, robot types, Gemini keys, and the selected agent model.[^src-20260822-readme-3] [^src-20260822-developmentguide] [^src-20260822-developmentlog] |
| **`dispatcher.py`** | `CommandDispatcher` central message router bridging Web, BLE, and AI inputs.[^src-20260822-readme-3] [^src-20260822-developmentguide] |
| **`safe_executor.py`** | Sandboxed Python code executor with AST import filters and syntax preflight.[^src-20260822-readme-3] [^src-20260822-developmentlog] |
| **`runtime_pipeline.py`** | Coordinator managing native robot idle state vs uploaded Blockly execution ownership.[^src-20260822-developmentlog] |
| **`action_library.py`** | Storage and retrieval engine for saved Blockly actions in `ninja_actions/*.json`.[^src-20260822-developmentlog] |
| **`api_wrappers.py`** | High-level `RobotWrapper`, `ServoArrayWrapper`, `DisplayWrapper`, `BuzzerWrapper`, and `DistanceWrapper`.[^src-20260822-readme-3] [^src-20260822-developmentlog] |
| **`gemini_models.py`** | Paginated API-key-specific Gemini model discovery filtered to `generateContent` models.[^src-20260822-developmentguide] [^src-20260822-developmentlog] |
| **`gemini_runtime.py`** | Bounded Gemini 3 REST generation with low thinking, safe errors, and non-blocking thread offload.[^src-20260822-developmentguide] [^src-20260822-developmentlog] |
| **`ninja_agent.py`** | Gemini AI integration using the configured model for natural language understanding and multi-modal action planning.[^src-20260822-readme-3] [^src-20260822-developmentguide] |
| **`movement_controller.py`** | Motion sequence playback engine with position-aware cubic easing.[^src-20260822-readme-3] [^src-20260822-developmentguide] |
| **`web_server.py`** | FastAPI web server serving REST endpoints, WebSockets (`/ws/events`), and SPA static assets.[^src-20260822-readme-3] [^src-20260822-developmentguide] |
| **`init_tool.py`** | Interactive setup wizard for validated Gemini key/model selection, tokens, robot naming, robot type, and hardware import.[^src-20260822-developmentguide] [^src-20260822-developmentlog] |

## CLI Entrypoints

* `uv run ninja_core server [--autostart]`: Launches the web server and BLE GATT service.[^src-20260822-readme-3]
* `uv run ninja_core chat`: Starts an interactive terminal chat session with the robot's AI agent.[^src-20260822-readme-3]
* `uv run ninja_core movement-tool`: Launches the interactive servo calibration and motion recording TUI.[^src-20260822-readme-3]
* `uv run ninja_core init-tool`: Launches the guided initial configuration wizard.[^src-20260822-developmentlog]
* `uv run ninja_core config import-all`: Merges individual subsystem configs into `config.json`.[^src-20260822-readme-3]

[^src-20260822-readme-3]: ninja_core Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-developmentlog]: NinjaRobot V5 Development Log.
