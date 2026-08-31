---
type: Entity
title: ninja_utils Package
description: Shared utilities package containing Abstract Base Classes, centralized
  logging, and systemd service managers.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-readme-4
  resource: urn:llmwiki:source:src-20260822-readme-4
  title: ninja_utils Readme
  content_hash: sha256:c8224fa991d7331e188187187def4af8e454464a762d05f7ad91fba5e7104cde
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:374bb5c44297ceb5134e5c4558f07d84378db45ea18ece6cdc3ecf3319a08e85
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:28e1f811fff7d77a34a3e2d65bff290c5d04972699c37480e0326c65b69986c2
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Shared ABCs, sensor/actuator contracts, and logging utilities verified.
---

# ninja_utils Package

`ninja_utils` provides shared foundation utilities and interface contracts across all NinjaRobot V5 packages.[^src-20260822-readme-4] [^src-20260822-developmentguide]

## Module Summary

* **`interfaces.py`**: Defines the `Actuator` and `Sensor` Abstract Base Classes (ABCs) and the `DistanceData` dataclass.[^src-20260822-readme-4] [^src-20260822-developmentguide]
* **`my_logger.py`**: Centralized, formatted logging system for console and file output.[^src-20260822-readme-4]
* **`keyboard.py`**: Non-blocking single-keypress terminal input helper for interactive TUIs.[^src-20260822-readme-4]
* **`startup.py`**: Manages Linux systemd service configuration for autostarting the robot on boot.[^src-20260822-readme-4]

## CLI Commands

* `uv run ninja_utils install-startup`: Installs and enables the `ninjarobot.service` systemd unit.[^src-20260822-readme-4]
* `uv run ninja_utils remove-startup`: Disables and removes the autostart service.[^src-20260822-readme-4]
* `uv run ninja_utils status-startup`: Checks the status of the systemd service.[^src-20260822-readme-4]

[^src-20260822-readme-4]: ninja_utils Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
