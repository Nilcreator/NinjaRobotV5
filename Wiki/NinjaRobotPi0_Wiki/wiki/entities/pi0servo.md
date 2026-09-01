---
type: Entity
title: pi0servo Package
description: Velocity-based servo control library for SG90/MG90S servos with cubic
  easing and interactive calibration.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-readme-7
  resource: urn:llmwiki:source:src-20260822-readme-7
  title: pi0servo Readme
  content_hash: sha256:23793729576aa0b8f5b460d7fe4e47ab1d7ad4f9a6af4348bf4c8208a6610a76
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:26272dce2ec7dcab9f3181e1ce0621448ef12547ff26f3b7a0ac4fc50cef9b4d
- id: src-20260822-projectupgradeplan
  resource: urn:llmwiki:source:src-20260822-projectupgradeplan
  title: NinjaRobot V5 Project Upgrade Plan
  content_hash: sha256:e4c2e08c7e62522fe2d289456b9f7d27db2058691e93e0bc8bb72d72d5498c59
semantic_review:
  version: 1
  performed_by: agent:codex
  performed_at: '2026-09-01T07:28:37Z'
  target_hash: sha256:8509f2a434766ef804ccbfd121c948caf2c45cb61e561ab84fbb2d06e1c5e5af
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Servo APIs, calibration, easing, and abort behavior are supported using the current multi_servos.py
    module path; no energized-servo validation was performed.
---

# pi0servo Package

`pi0servo` is a velocity-based servo control library designed for Raspberry Pi Zero 2W, controlling up to 8 SG90 or MG90S micro servos.[^src-20260822-readme-7] [^src-20260822-developmentguide]

## Core Features

* **Velocity-Based Calculations**: Angular displacement is calculated per 10ms step (100Hz update rate), reducing dependence on arbitrary fixed delays.[^src-20260822-readme-7]
* **Cubic Easing**: Default `ease_in_out_cubic` provides smooth S-curve acceleration and deceleration.[^src-20260822-readme-7]
* **Per-Servo Speed Limits**: Configurable in `servo.json` (0–100%) to prevent mechanical overshoot and gear wear.[^src-20260822-readme-7]
* **Abort Mechanism**: Thread-safe cancellation signaling for active movements via `ServoGroup.abort()`.[^src-20260822-readme-7]

## Key Classes & Modules

* **`ServoGroup` (`pi0servo.core.multi_servos`)**: Multi-channel controller used by the HAL and providing actuator-compatible lifecycle methods.[^src-20260822-developmentguide]
* **`Servo` (`pi0servo.core.servo`)**: Individual servo channel model with angle-to-pulse interpolation.[^src-20260822-projectupgradeplan]
* **`ConfigManager` (`pi0servo.config.config_manager`)**: Manages `servo.json` calibration profiles.[^src-20260822-readme-7]

## CLI & Calibration TUI

* `uv run pi0servo servo-tool`: Launches the interactive calibration and testing TUI.[^src-20260822-readme-7]
* `uv run pi0servo calib <pin>`: Calibrates Min, Center, and Max pulse widths for a given GPIO pin.[^src-20260822-readme-7]
* `uv run pi0servo cmd "<command>"`: Executes a movement command string (e.g. `F_20:45/21:-30`).[^src-20260822-readme-7]

[^src-20260822-readme-7]: pi0servo Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-projectupgradeplan]: NinjaRobot V5 Project Upgrade Plan.
