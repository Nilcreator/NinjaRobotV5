---
type: Concept
title: Architecture and Hardware Abstraction Layer
description: Monorepo structure, dynamic driver loading, interface ABCs, and centralized
  configuration in NinjaRobot V5.
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
- id: src-20260822-readme-4
  resource: urn:llmwiki:source:src-20260822-readme-4
  title: ninja_utils Readme
  content_hash: sha256:c8224fa991d7331e188187187def4af8e454464a762d05f7ad91fba5e7104cde
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:1c490a883d46f7d389df626901055cb8083d5156d7b312932111fd897c40821d
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Modular HAL, abstract base classes, and singleton driver registry verified against
    ninja_utils and ninja_core documentation.
---

# Architecture and Hardware Abstraction Layer

NinjaRobot V5 adopts a layered, modular architecture where independent hardware driver packages are decoupled from the core application logic through a Hardware Abstraction Layer (HAL).[^src-20260822-developmentguide] [^src-20260822-readme-3]

## Monorepo Package Layout

The project consists of 7 standalone Python packages and 1 React web application:[^src-20260822-developmentguide]

```
NinjaRobotV5/
├── pyproject.toml              # Root workspace definition
├── config.json                 # Centralized master runtime configuration
├── servo.json, buzzer.json...  # Subsystem configuration files
├── ninja_utils/                # Shared logging, keyboard, and ABC interfaces
├── ninja_ble/                  # BLE GATT server and chunking protocol
├── ninja_webapp/               # React 18 + Vite web interface
├── pi0servo/                   # Velocity-based servo controller
├── pi0buzzer/                  # Non-blocking passive buzzer driver
├── pi0vl53l0x/                 # Thread-safe VL53L0X distance sensor driver
├── pi0disp/                    # Thread-safe ST7789V display driver
└── ninja_core/                 # Main application, HAL, web server, AI agent
```

## Abstract Base Classes (`ninja_utils.interfaces`)

Standardized interfaces enforce consistency across all hardware drivers:[^src-20260822-readme-4] [^src-20260822-developmentguide]

* **`Actuator`**: Defines standard lifecycle methods for output devices:
  * `initialize()`: Sets up hardware pins and starts background worker threads.[^src-20260822-readme-4]
  * `execute(command: dict)`: Executes a structured command dictionary (e.g. `{"angles": [...]}` or `{"image": img}`).[^src-20260822-readme-4]
  * `off()`: Silences or disables the device safely.[^src-20260822-readme-4]
* **`Sensor`**: Defines standard methods for input sensors:
  * `initialize()`: Performs hardware handshake and calibration.[^src-20260822-readme-4]
  * `read() -> DistanceData`: Returns structured reading with validity flags and timestamps.[^src-20260822-readme-4]
  * `health_check() -> bool`: Verifies hardware communication status.[^src-20260822-readme-4]

## Dynamic Driver Registry (`ninja_core.hal`)

The HAL (`ninja_core/hal.py`) initializes and coordinates drivers using dynamic module loading via `importlib` rather than hardcoded static imports:[^src-20260822-readme-3] [^src-20260822-developmentguide]

```python
DRIVER_REGISTRY = {
    "servos": {"module": "pi0servo.core.servo_group", "class": "ServoGroup"},
    "buzzer": {"module": "pi0buzzer.driver", "class": "MusicBuzzer"},
    "display": {"module": "pi0disp.core.driver", "class": "ST7789V"},
    "distance_sensor": {"module": "pi0vl53l0x.driver", "class": "VL53L0X"},
}
```

This design allows individual drivers to be updated, replaced, or mocked during automated testing without modifying the core server.[^src-20260822-developmentguide]

## Centralized Configuration (`config.json`)

All runtime settings are consolidated into a master `config.json` managed by `ninja_core.config.NinjaConfig`:[^src-20260822-readme-3] [^src-20260822-developmentguide]
* **Hardware settings**: Servo pulse calibrations, buzzer volume, display rotation/brightness, sensor offsets.[^src-20260822-developmentguide]
* **System settings**: Robot name (`bluetooth.name`), robot type (`robot_type`: `tire`, `humanoid`, `spider`), API keys (Gemini), ngrok authtoken.[^src-20260822-developmentguide]
* **Synchronization**: Subsystem configurations can be synchronized via `uv run ninja_core config import` or `config import-all`.[^src-20260822-readme-3] [^src-20260822-developmentguide]

[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-readme-3]: ninja_core Readme.
[^src-20260822-readme-4]: ninja_utils Readme.
