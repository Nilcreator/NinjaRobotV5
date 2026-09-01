---
type: Concept
title: Action Library and AI Agent
description: Google Gemini-powered agentic AI, saved Blockly action library, action
  chaining, and cooperative interruption.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:26272dce2ec7dcab9f3181e1ce0621448ef12547ff26f3b7a0ac4fc50cef9b4d
- id: src-20260822-readme-3
  resource: urn:llmwiki:source:src-20260822-readme-3
  title: ninja_core Readme
  content_hash: sha256:c13dcf9055a532fefb03664983e9b5bafcb384e7ff16b65feca801cdbff23ba5
- id: src-20260822-developmentlog
  resource: urn:llmwiki:source:src-20260822-developmentlog
  title: NinjaRobot V5 Development Log
  content_hash: sha256:503fe3ddfad6f04902d9b3a707a8be9d9da7c24eb9eae5b1dc5ea739225c5bc3
semantic_review:
  version: 1
  performed_by: agent:codex
  performed_at: '2026-09-01T07:28:37Z'
  target_hash: sha256:a62aae3f67ac1cf28bc85f9bde6a87aac6825d52f0e2f124b3cf5ca5963d97e9
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Selected-model discovery, bounded probing, and Gemini 3 low-thinking compatibility are supported;
    setup validation is explicitly limited to a point-in-time check.
---

# Action Library and AI Agent

NinjaRobot V5 combines large language model intelligence with an extensible on-robot action library, allowing natural language commands to trigger complex multi-modal behaviors.[^src-20260822-readme-3] [^src-20260822-developmentguide]

## Google Gemini Agent (`ninja_core.ninja_agent`)

The AI agent uses the Gemini model selected and validated during API-key setup; legacy configurations without a saved model retain `gemini-3-flash-preview` as their compatibility default.[^src-20260822-readme-3] [^src-20260822-developmentguide] [^src-20260822-developmentlog]

* **Validated Model Selection**: `config set-key gemini` and the guided initializer retrieve models available to the supplied key, require `generateContent`, and save the key/model pair only after a bounded generation probe succeeds.[^src-20260822-developmentguide] [^src-20260822-developmentlog]
* **Gemini 3 Compatibility**: Gemini 3 requests use the REST compatibility path with low thinking and a 60-second bound because the installed legacy SDK cannot express current thinking controls; older models retain the bounded SDK path.[^src-20260822-developmentguide] [^src-20260822-developmentlog]
* **Point-in-Time Validation**: A successful setup probe confirms that the selected model responded during configuration; later quota, network, permission, latency, or model-availability changes can still cause runtime failures.[^src-20260822-developmentguide] [^src-20260822-developmentlog]

* **Natural Language Understanding**: Supports conversational chat in English, Japanese, and Traditional/Simplified Chinese.[^src-20260822-readme-3]
* **Semantic Action Planning**: Maps user intent to structured action plans containing:
  * **Movement**: Pre-recorded sequence or saved Blockly action.[^src-20260822-developmentlog]
  * **Expression**: Display face (`happy`, `scary`, `sleepy`, `speaking`, etc.).[^src-20260822-readme-3]
  * **Sound**: Emotion tone or musical melody.[^src-20260822-readme-3]
  * **Spoken Response**: Natural language response synthesized in the user's language.[^src-20260822-readme-3]
* **Action Chaining**: Combines movements, sounds, and facial expressions into synchronized execution sequences.[^src-20260822-readme-3]

## Saved Blockly Action Library (`ActionLibrary`)

The `ActionLibrary` (`ninja_core.action_library.ActionLibrary`) manages custom actions uploaded from the Code IDE over BLE or Web:[^src-20260822-developmentguide] [^src-20260822-developmentlog]

* **Storage**: Saved as `ninja-action-v1` JSON files under `ninja_actions/*.json`.[^src-20260822-developmentlog]
* **Protected Overwrite**:
  * Native movements defined in `config.json` (e.g. `wave`, `bow`) are protected and cannot be overwritten.[^src-20260822-developmentlog]
  * Existing user actions can be replaced if `overwrite=True` is provided.[^src-20260822-developmentlog]
* **Dynamic Agent Integration**: Saved actions are automatically loaded into the Gemini prompt so the robot can trigger user-created Blockly programs via voice/chat commands.[^src-20260822-developmentlog]

## Cooperative Interruption

When a new user message arrives while a previous movement or action plan is executing, the server executes a cooperative interruption sequence:[^src-20260822-developmentlog]
1. Signals cancellation to `SafeExecutor`.[^src-20260822-developmentlog]
2. Calls `ServoGroup.abort()` to halt active motor trajectories.[^src-20260822-developmentlog]
3. Resets sound and face queues.[^src-20260822-developmentlog]
4. Acquires an async execution lock before starting the new action plan.[^src-20260822-developmentlog]

[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-readme-3]: ninja_core Readme.
[^src-20260822-developmentlog]: NinjaRobot V5 Development Log.
