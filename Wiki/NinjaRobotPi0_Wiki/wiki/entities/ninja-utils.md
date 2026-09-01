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
  content_hash: sha256:26272dce2ec7dcab9f3181e1ce0621448ef12547ff26f3b7a0ac4fc50cef9b4d
semantic_review:
  version: 1
  performed_by: agent:codex
  performed_at: '2026-09-01T07:28:37Z'
  target_hash: sha256:600c6efd521843feabc09da35b1da62809d35c3a3a3cd98fded1c072dad66725
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Shared logging, interface, and service-management claims use the current service_manager.py path;
    the older package README is treated as legacy context.
---

# ninja_utils Package

`ninja_utils` provides shared foundation utilities and interface contracts across all NinjaRobot V5 packages.[^src-20260822-readme-4] [^src-20260822-developmentguide]

## Module Summary

* **`interfaces.py`**: Defines the `Actuator` and `Sensor` Abstract Base Classes (ABCs) and the `DistanceData` dataclass.[^src-20260822-readme-4] [^src-20260822-developmentguide]
* **`my_logger.py`**: Centralized, formatted logging system for console and file output.[^src-20260822-readme-4]
* **`keyboard.py`**: Non-blocking single-keypress terminal input helper for interactive TUIs.[^src-20260822-readme-4]
* **`service_manager.py`**: Manages Linux systemd service configuration for autostarting the robot on boot.[^src-20260822-developmentguide]

## CLI Commands

* `uv run ninja_utils install-startup`: Installs and enables the `ninjarobot.service` systemd unit.[^src-20260822-readme-4]
* `uv run ninja_utils remove-startup`: Disables and removes the autostart service.[^src-20260822-readme-4]
* `uv run ninja_utils status-startup`: Checks the status of the systemd service.[^src-20260822-readme-4]

[^src-20260822-readme-4]: ninja_utils Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
