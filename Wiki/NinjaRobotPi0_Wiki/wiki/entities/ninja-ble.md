---
type: Entity
title: ninja_ble Package
description: Bluetooth Low Energy peripheral service package implementing GATT characteristics
  and binary chunking.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-readme-2
  resource: urn:llmwiki:source:src-20260822-readme-2
  title: ninja_ble Readme
  content_hash: sha256:76bbd36ab8a5d9d81b4e73fd2e3910e4c8a9b79c82e7558e94044e6c81871910
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
  target_hash: sha256:5e1e701b2500a758b7fecc03f8071d38848d2cf1d936f7845363f5561cca17fa
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - GATT, chunking, notification, and dispatcher integration claims align with the cited BLE and core
    documentation.
---

# ninja_ble Package

`ninja_ble` provides the Bluetooth Low Energy (BLE) peripheral interface for NinjaRobot V5, enabling direct zero-configuration control from web browsers (Web Bluetooth) and mobile apps.[^src-20260822-readme-2] [^src-20260822-developmentguide]

## Architecture & Dependencies

* **`service.py`**: Implements `NinjaBLEService` using `bless` (GATT server) on top of BlueZ (`dbus-fast`) on Linux.[^src-20260822-readme-2]
* **`chunking.py`**: Handles packet fragmentation and reassembly for large payloads (>160 bytes) with CRC32 verification.[^src-20260822-readme-2] [^src-20260822-developmentlog]

## GATT Services and Characteristics

* **Service UUID**: `00000001-710e-4a5b-8d75-3e5b444bc3cf` [^src-20260822-readme-2]
* **Command Characteristic** (`...0002...`): Write JSON command or binary chunk.[^src-20260822-readme-2]
* **Response Characteristic** (`...0003...`): Read/Notify JSON events, status updates, and execution logs.[^src-20260822-readme-2]
* **Command Status Characteristic** (`...0004...`): Read cached response status by `request_id`.[^src-20260822-developmentlog]

## Custom Naming & Robot Info

The BLE advertisement name is configured in `config.json` under `bluetooth.name` (max 29 UTF-8 bytes).[^src-20260822-developmentlog] When queried via `{"type": "robot_info"}`, the service responds with the robot's configured name, type, and sanitized GPIO pin assignments.[^src-20260822-developmentlog]

[^src-20260822-readme-2]: ninja_ble Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-developmentlog]: NinjaRobot V5 Development Log.
