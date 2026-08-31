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
  content_hash: sha256:374bb5c44297ceb5134e5c4558f07d84378db45ea18ece6cdc3ecf3319a08e85
- id: src-20260822-projectupgradeplan
  resource: urn:llmwiki:source:src-20260822-projectupgradeplan
  title: NinjaRobot V5 Project Upgrade Plan
  content_hash: sha256:e4c2e08c7e62522fe2d289456b9f7d27db2058691e93e0bc8bb72d72d5498c59
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:0f052997cc223bd060e27ebe72e1627fa0ca2816acc17e487e7917cef94befa6
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - 8-channel servo driver, angle-to-pulse width mapping, and easing velocity calculations
    verified.
---

# pi0servo Package

`pi0servo` is a velocity-based servo control library designed for Raspberry Pi Zero 2W, controlling up to 8 SG90 or MG90S micro servos.[^src-20260822-readme-7] [^src-20260822-developmentguide]

## Core Features

* **Velocity-Based Calculations**: Physics-based angular displacement per 10ms step (100Hz update rate) eliminates timing jitter.[^src-20260822-readme-7]
* **Cubic Easing**: Default `ease_in_out_cubic` provides smooth S-curve acceleration and deceleration.[^src-20260822-readme-7]
* **Per-Servo Speed Limits**: Configurable in `servo.json` (0–100%) to prevent mechanical overshoot and gear wear.[^src-20260822-readme-7]
* **Abort Mechanism**: Immediate thread-safe cancellation of active movements via `ServoGroup.abort()`.[^src-20260822-readme-7]

## Key Classes & Modules

* **`ServoGroup` (`pi0servo.core.servo_group`)**: Multi-channel servo controller implementing `Actuator` ABC.[^src-20260822-readme-7] [^src-20260822-developmentguide]
* **`Servo` (`pi0servo.core.servo`)**: Individual servo channel model with angle-to-pulse interpolation.[^src-20260822-projectupgradeplan]
* **`ConfigManager` (`pi0servo.config.config_manager`)**: Manages `servo.json` calibration profiles.[^src-20260822-readme-7]

## CLI & Calibration TUI

* `uv run pi0servo servo-tool`: Launches the interactive calibration and testing TUI.[^src-20260822-readme-7]
* `uv run pi0servo calib <pin>`: Calibrates Min, Center, and Max pulse widths for a given GPIO pin.[^src-20260822-readme-7]
* `uv run pi0servo cmd "<command>"`: Executes a movement command string (e.g. `F_20:45/21:-30`).[^src-20260822-readme-7]

[^src-20260822-readme-7]: pi0servo Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-projectupgradeplan]: NinjaRobot V5 Project Upgrade Plan.
