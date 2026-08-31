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
  content_hash: sha256:374bb5c44297ceb5134e5c4558f07d84378db45ea18ece6cdc3ecf3319a08e85
- id: src-20260822-developmentlog
  resource: urn:llmwiki:source:src-20260822-developmentlog
  title: NinjaRobot V5 Development Log
  content_hash: sha256:8d069ece52a85c0abb5cb6f5de64857f76353d9040315629dceb9e30cf3caa33
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:4b514a9787d8ff7810885aa227f5b14f660831051507610ed953859ffb5ee284
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Bless GATT server architecture, UUID definitions, and status readback characteristics
    verified against package documentation.
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
