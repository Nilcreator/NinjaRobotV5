---
type: Concept
title: Safe Code Execution and Blockly Runtime
description: Sandboxed Python execution, AST compilation preflight, runtime ownership
  switching, and GPIO-first wrapper contracts.
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
  target_hash: sha256:acafa42cc4007d9aa0793e2c288764fd5bf6a19e4ad16ab13480bfb76900bdeb
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Restricted execution and runtime ownership claims are supported; cancellation is explicitly cooperative
    and non-cooperative loops remain a documented limitation.
---

# Safe Code Execution and Blockly Runtime

NinjaRobot V5 enables students and researchers to execute generated Python scripts and Blockly visual code through a restricted on-robot execution path.[^src-20260822-readme-3] [^src-20260822-developmentguide]

## Sandboxed Python Execution Engine (`SafeExecutor`)

`SafeExecutor` runs user and AI scripts in an isolated execution thread with AST validation:[^src-20260822-readme-3] [^src-20260822-developmentguide]

* **AST Preflight Compilation**: Code is compiled and checked for dangerous imports (`os`, `sys`, `subprocess`, `shutil`) before starting the worker thread.[^src-20260822-developmentguide] [^src-20260822-developmentlog]
* **Syntax Error Isolation**: Syntax and compilation errors return structured diagnostic events (`line`, `offset`, `text`) without triggering hardware cleanup or stopping native face animations.[^src-20260822-developmentlog]
* **Cooperative Cancellation**: Generated loops periodically call `check_stop()`, allowing web UI or BLE `stop` commands to request a halt.[^src-20260822-developmentlog]

> [!IMPORTANT]
> Cancellation is cooperative rather than a forced thread kill. Python loops that never call `check_stop()` may require the Stop Robot path or a server restart.[^src-20260822-developmentguide]

## Dual Pipeline & Ownership Management (`RuntimePipeline`)

To prevent conflicts between native robot behavior (such as idle face animations and web UI commands) and uploaded Blockly programs, `RuntimePipeline` coordinates execution ownership:[^src-20260822-developmentguide] [^src-20260822-developmentlog]

1. **Native Idle Mode**: The robot displays natural blinking and breathing expressions.[^src-20260822-developmentlog]
2. **Blockly Execution Mode**: Upon valid script launch, native idle loops pause, allowing the script exclusive control over servos, display, and buzzer.[^src-20260822-developmentlog]
3. **Display Clear Hold**: When script calls `robot.display.clear()`, the screen stays intentionally blank until native interaction, the next upload, or Disconnect.[^src-20260822-developmentlog]
4. **Restoration**: On script completion, stop button press, or BLE disconnection, native ownership and idle animations resume gracefully.[^src-20260822-developmentlog]

## GPIO-First Motion & Sensor Wrapper Contract

For visual Blockly code generation (`web-blockly-v2`), `ninja_core.api_wrappers` exposes high-level, safe APIs:[^src-20260822-developmentguide] [^src-20260822-developmentlog]

* **`robot.servos.move_pin(pin, angle, speed_mode="M")`**: Moves a specific GPIO pin (`20..27`) with angle clamping (`-90..90`).[^src-20260822-developmentlog]
* **`robot.servos.move_pins({pin: angle}, per_servo_speeds={...})`**: Synchronized multi-pin motion routed to `pi0servo.move_all_sync()`.[^src-20260822-developmentlog]
* **`robot.distance.read()`**: Returns distance in millimeters. If the physical sensor is disconnected or I2C errors occur, it safely returns `9999` (fallback) to prevent accidental obstacle emergency halts.[^src-20260822-developmentguide] [^src-20260822-developmentlog]
* **`robot.display.text(text, scroll=False, lang="auto")`**: Displays static or scrolling multilingual text using Noto fonts.[^src-20260822-developmentguide] [^src-20260822-developmentlog]
* **`robot.buzzer.play_song(name)`**: Plays named songs (`happy_birthday`, `jingle_bells`, etc.) asynchronously.[^src-20260822-developmentguide] [^src-20260822-developmentlog]

[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-readme-3]: ninja_core Readme.
[^src-20260822-developmentlog]: NinjaRobot V5 Development Log.
