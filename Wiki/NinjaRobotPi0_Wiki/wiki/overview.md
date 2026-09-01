---
type: Concept
title: NinjaRobot V5 Platform Overview
description: Comprehensive overview of the NinjaRobot V5 AI-powered educational and
  research robotics platform.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-readme
  resource: urn:llmwiki:source:src-20260822-readme
  title: NinjaRobot V5 Readme
  content_hash: sha256:747c8c2e1e67d24b5d6f6b9c797a6eb7ec7b92b1ce4368623cc9b77b62c442a4
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:26272dce2ec7dcab9f3181e1ce0621448ef12547ff26f3b7a0ac4fc50cef9b4d
semantic_review:
  version: 1
  performed_by: agent:codex
  performed_at: '2026-09-01T07:28:37Z'
  target_hash: sha256:4852441f395e00f9a56afc151756097124ba9069429582f80374b1ca150a3d28
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - The overview accurately summarizes the current documented architecture and capabilities after removing
    promotional and unverified performance wording.
---

# NinjaRobot V5 Platform Overview

**NinjaRobot V5** is an advanced, modular AI robot platform designed for research and STEAM education, powered by the Raspberry Pi Zero 2W.[^src-20260822-readme] It integrates a Google Gemini agent with a mobile-first web interface, dual connectivity (Wi-Fi and Bluetooth Low Energy), and rebuilt non-blocking hardware drivers.[^src-20260822-readme] [^src-20260822-developmentguide]

## Hardware Specifications

| Component | Specification | Details |
|-----------|---------------|---------|
| **Brain / SBC** | Raspberry Pi Zero 2W | Quad-core ARM Cortex-A53 @ 1.0 GHz, 512MB RAM [^src-20260822-readme] |
| **Display** | 2.0" / 2.8" ST7789V IPS LCD | 240×320 pixels, SPI interface, PWM brightness control [^src-20260822-readme] [^src-20260822-developmentguide] |
| **Distance Sensor** | VL53L0X Time-of-Flight | Up to 2m documented range, I2C interface, distance readings in millimetres [^src-20260822-readme] |
| **Sound / Audio** | Passive Buzzer | GPIO 17, 35 musical notes (C3–B7), 14 emotion sounds [^src-20260822-readme] |
| **Actuators** | 8× SG90 / MG90S Servos | GPIO 20–27, velocity-based physics control [^src-20260822-readme] |
| **Connectivity** | Wi-Fi & Bluetooth | Wi-Fi 802.11n (2.4GHz), BLE 4.2 GATT Server [^src-20260822-readme] |

## Software Architecture

The NinjaRobot software stack is organized as a layered monorepo with 7 independent Python packages and a modern web application:[^src-20260822-developmentguide]

* **[Architecture & Hardware Abstraction Layer](concepts/architecture-and-hal.md)**: Dynamic driver registry and ABC interfaces in `ninja_utils`.[^src-20260822-developmentguide]
* **[Motion System & Easing](concepts/motion-system-and-easing.md)**: Velocity-based servo control and position-aware cubic easing curves.[^src-20260822-developmentguide]
* **[Dual Connectivity & Protocols](concepts/dual-connectivity-and-protocols.md)**: Centralized command dispatching across BLE and Web interfaces with chunked transport.[^src-20260822-developmentguide]
* **[Safe Execution & Blockly Runtime](concepts/safe-execution-and-blockly-runtime.md)**: Sandboxed code execution engine and dual runtime pipeline.[^src-20260822-developmentguide]
* **[Action Library & AI Agent](concepts/action-library-and-ai-agent.md)**: Validated user-selected Gemini models, bounded Gemini 3 compatibility, and a persistent Blockly action library.[^src-20260822-readme] [^src-20260822-developmentguide]
* **[Perception & Expression](concepts/perception-and-expression.md)**: Distance monitoring, animated facial expressions, and emotion audio queues.[^src-20260822-developmentguide]

## Component Packages

* **[NinjaRobot V5 Entity](entities/ninjarobot-v5.md)**: High-level robot platform entity.[^src-20260822-readme]
* **[ninja_core](entities/ninja-core.md)**: Central application server, HAL, motion system, and web controllers.[^src-20260822-developmentguide]
* **[ninja_ble](entities/ninja-ble.md)**: BLE GATT server service supporting zero-network mobile connection.[^src-20260822-developmentguide]
* **[ninja_utils](entities/ninja-utils.md)**: Shared interfaces (`Sensor`, `Actuator`), logging, and system utilities.[^src-20260822-developmentguide]
* **[pi0servo](entities/pi0servo.md)**: Velocity-based multi-servo controller with easing.[^src-20260822-developmentguide]
* **[pi0disp](entities/pi0disp.md)**: Thread-safe ST7789V display driver with delta rendering.[^src-20260822-developmentguide]
* **[pi0buzzer](entities/pi0buzzer.md)**: Non-blocking passive buzzer driver with emotion sounds and melodies.[^src-20260822-developmentguide]
* **[pi0vl53l0x](entities/pi0vl53l0x.md)**: Hardened VL53L0X Time-of-Flight distance sensor driver.[^src-20260822-developmentguide]
* **[ninja_webapp](entities/ninja-webapp.md)**: React 18 + Vite frontend SPA with multilingual support.[^src-20260822-developmentguide]

## References & Deep Dives

* **[Installation & Wiring Guide](references/installation-and-wiring.md)**: Step-by-step assembly, wiring tables, and OS setup.[^src-20260822-developmentguide]
* **[Hardware Calibration & Tools](references/hardware-calibration-and-tools.md)**: Guided initialization and interactive TUIs for each subsystem.[^src-20260822-developmentguide]
* **[API & CLI Reference](references/api-and-cli-reference.md)**: Unified Python API, REST endpoints, and CLI commands.[^src-20260822-developmentguide]
* **[Driver Rebuild & Vulnerability Analysis](analyses/driver-rebuild-and-vulnerability-analysis.md)**: Evolution from legacy blocking drivers to non-blocking architectures.[^src-20260822-developmentguide]
* **[Development History & Evolution](analyses/development-history-and-evolution.md)**: Detailed chronology of V5 development phases and audits.[^src-20260822-developmentguide]

[^src-20260822-readme]: NinjaRobot V5 Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
