---
type: Concept
title: Dual Connectivity and Communication Protocols
description: Dual Wi-Fi and Bluetooth Low Energy connectivity, GATT service specifications,
  and chunked transfer protocols.
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
- id: src-20260822-readme
  resource: urn:llmwiki:source:src-20260822-readme
  title: NinjaRobot V5 Readme
  content_hash: sha256:747c8c2e1e67d24b5d6f6b9c797a6eb7ec7b92b1ce4368623cc9b77b62c442a4
- id: src-20260822-developmentlog
  resource: urn:llmwiki:source:src-20260822-developmentlog
  title: NinjaRobot V5 Development Log
  content_hash: sha256:503fe3ddfad6f04902d9b3a707a8be9d9da7c24eb9eae5b1dc5ea739225c5bc3
semantic_review:
  version: 1
  performed_by: agent:codex
  performed_at: '2026-09-01T07:28:37Z'
  target_hash: sha256:0f71db1dd9e5371fee11024d21b928273700aa4ca37710b29419ec3a2d041bac
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Transport, dispatcher, BLE chunking, CRC, and fallback claims are supported; CRC is described as integrity
    checking rather than lossless delivery.
---

# Dual Connectivity and Communication Protocols

NinjaRobot V5 features dual connectivity that allows users to interact with the robot over local Wi-Fi, remote ngrok tunnels, or zero-configuration Bluetooth Low Energy (BLE).[^src-20260822-readme] [^src-20260822-developmentguide]

## Connectivity Architecture

All input channels funnel into the central `CommandDispatcher` in `ninja_core`, which routes actions to the HAL, AI Agent, or SafeExecutor:[^src-20260822-readme-2] [^src-20260822-developmentguide]

```
┌──────────────────┐       HTTP / WebSockets       ┌────────────────────────┐
│  Web / Mobile    │ ───────────────────────────▶  │ ninja_core.web_server  │
│  (React WebApp)  │ ◀───────────────────────────  │ (FastAPI on Port 8000) │
└──────────────────┘                               └───────────┬────────────┘
                                                               │
┌──────────────────┐         BLE GATT Protocol                 │
│ Code IDE App /   │ ───────────────────────────▶  ┌───────────▼────────────┐
│ nRF Connect      │ ◀───────────────────────────  │ ninja_ble.NinjaBLE     │
└──────────────────┘                               └───────────┬────────────┘
                                                               │
                                                   ┌───────────▼────────────┐
                                                   │   CommandDispatcher    │
                                                   └────────────────────────┘
```

## BLE GATT Service Specification

The BLE peripheral is implemented using `bless` with BlueZ on Linux:[^src-20260822-readme-2] [^src-20260822-developmentguide]

* **Service Name**: Configurable via `bluetooth.name` (default: `NinjaRobot`).[^src-20260822-developmentguide] [^src-20260822-developmentlog]
* **Service UUID**: `00000001-710e-4a5b-8d75-3e5b444bc3cf` [^src-20260822-readme-2]

### Characteristics

| Characteristic | UUID | Properties | Purpose |
|----------------|------|------------|---------|
| **Command** | `00000002-710e-4a5b-8d75-3e5b444bc3cf` | Write | Inbound JSON commands & chunks [^src-20260822-readme-2] |
| **Response** | `00000003-710e-4a5b-8d75-3e5b444bc3cf` | Read, Notify | Live notification stream [^src-20260822-readme-2] |
| **Command Status** | `00000004-710e-4a5b-8d75-3e5b444bc3cf` | Read | Cached status readback by `request_id` [^src-20260822-developmentlog] |

## Binary Chunking Protocol

For payloads exceeding BLE MTU limits (e.g. Blockly code uploads >160 bytes), a binary chunking protocol provides sequence tracking and CRC32 integrity checking:[^src-20260822-readme-2] [^src-20260822-developmentlog]

| Packet Type | Magic Byte | Format |
|-------------|------------|--------|
| **HEADER** | `0x01` | `[0x01][total_chunks: 2B][crc32: 4B][payload_len: 4B]` [^src-20260822-readme-2] |
| **DATA** | `0x02` | `[0x02][sequence: 2B][chunk_data: N bytes]` [^src-20260822-readme-2] |
| **EOF** | `0x03` | `[0x03][chunks_received: 2B]` [^src-20260822-readme-2] |

Each packet is ACKed (`{"type": "ack", "seq": N, "status": "ok"}`). On EOF, the server computes the CRC32 checksum before dispatching.[^src-20260822-readme-2]

## Command Status Caching

To prevent false timeout errors in web browsers when Bluetooth notification packets are dropped, `NinjaBLEService` caches command execution and save results by `request_id`.[^src-20260822-developmentlog] The browser can query characteristic `00000004` to recover confirmation state deterministically.[^src-20260822-developmentlog]

[^src-20260822-readme-2]: ninja_ble Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-readme]: NinjaRobot V5 Readme.
[^src-20260822-developmentlog]: NinjaRobot V5 Development Log.
