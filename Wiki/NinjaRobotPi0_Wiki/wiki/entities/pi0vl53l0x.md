---
type: Entity
title: pi0vl53l0x Package
description: Hardened VL53L0X Time-of-Flight distance sensor driver with transaction-level
  locking and bus recovery.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-readme-8
  resource: urn:llmwiki:source:src-20260822-readme-8
  title: pi0vl53l0x Readme
  content_hash: sha256:6d02713847e83b720c6093afade910a3989dc1e8d8b48d889d61c1e381b7b680
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
  target_hash: sha256:80bed65c4203b3b7fd5f5a841b449ba31e14a58046d965b26dc00e21a4289783
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Sensor APIs, transaction locking, recovery, calibration, and fallback behavior are supported; no live
    I2C or ranging validation was performed.
---

# pi0vl53l0x Package

`pi0vl53l0x` is a robust Python driver for the VL53L0X Time-of-Flight distance sensor using `pigpio` I2C on Raspberry Pi.[^src-20260822-readme-8] [^src-20260822-developmentguide]

## Core Features

* **Transaction-Level Locking**: Wraps complete single-shot ranging transactions in a `threading.RLock`, preventing race conditions when both the background `DistanceMonitor` and Blockly user scripts query the sensor.[^src-20260822-readme-8] [^src-20260822-developmentlog]
* **Hardened Boot Initialization**: Firmware boot polling (up to 1.0s timeout) resolves the legacy "returns 0mm after reboot" issue.[^src-20260822-readme-8]
* **Automatic Bus Recovery**: Exponential backoff retry (10→20→50ms) with bus reinitialization upon repeated communication failures.[^src-20260822-readme-8]
* **Async Ready**: `get_range_async()` runs ranging in a thread pool executor for seamless asyncio integration.[^src-20260822-readme-8]

## Key Classes & Modules

* **`VL53L0X` (`pi0vl53l0x.core.sensor`)**: Main sensor driver providing sensor-compatible initialization, data, and cleanup methods.[^src-20260822-readme-8] [^src-20260822-developmentguide]
* **`I2CBus` (`pi0vl53l0x.core.i2c`)**: Thread-safe I2C bus wrapper with retry and error handling.[^src-20260822-readme-8]
* **`registers.py`**: Semantic register constants (~60 registers) for full hardware control.[^src-20260822-readme-8]
* **`ConfigManager` (`pi0vl53l0x.config.config_manager`)**: Manages `vl53l0x.json` offset calibration data.[^src-20260822-readme-8]

## CLI Commands

* `uv run pi0vl53l0x get [--count N] [--interval S]`: Reads distance measurements.[^src-20260822-readme-8]
* `uv run pi0vl53l0x test`: Runs quick 5-sample diagnostic read.[^src-20260822-readme-8]
* `uv run pi0vl53l0x calibrate --distance <mm>`: Guided offset calibration at known target distance.[^src-20260822-readme-8]
* `uv run pi0vl53l0x sensor-tool`: Launches the 8-option interactive TUI.[^src-20260822-readme-8]

[^src-20260822-readme-8]: pi0vl53l0x Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-developmentlog]: NinjaRobot V5 Development Log.
