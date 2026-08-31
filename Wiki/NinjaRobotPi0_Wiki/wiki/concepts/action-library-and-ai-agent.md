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
  content_hash: sha256:374bb5c44297ceb5134e5c4558f07d84378db45ea18ece6cdc3ecf3319a08e85
- id: src-20260822-readme-3
  resource: urn:llmwiki:source:src-20260822-readme-3
  title: ninja_core Readme
  content_hash: sha256:4c4bc38f4de4851f444770bd63e6214e5d04a4ee12d30f0d8b0b2a5b5a453471
- id: src-20260822-developmentlog
  resource: urn:llmwiki:source:src-20260822-developmentlog
  title: NinjaRobot V5 Development Log
  content_hash: sha256:8d069ece52a85c0abb5cb6f5de64857f76353d9040315629dceb9e30cf3caa33
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:0f0817612edbb5cc71548d3d62142946c79a5fa48ac83b6e246300b3e207aca5
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Agentic AI capabilities, Gemini prompt flows, and Code IDE action persistence
    match development guide.
---

# Action Library and AI Agent

NinjaRobot V5 combines large language model intelligence with an extensible on-robot action library, allowing natural language commands to trigger complex multi-modal behaviors.[^src-20260822-readme-3] [^src-20260822-developmentguide]

## Google Gemini Agent (`ninja_core.ninja_agent`)

The AI agent integrates Google Gemini (`gemini-3-flash-preview`):[^src-20260822-readme-3] [^src-20260822-developmentguide]

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
