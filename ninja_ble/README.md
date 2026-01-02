# ninja_ble

Bluetooth Low Energy (BLE) control service for NinjaRobot V5. Enables direct, zero-network-setup communication with the robot via standardized GATT protocol.

## Features

- **GATT Server**: Exposes NinjaRobot as a BLE peripheral
- **AI Chat Integration**: Send text commands, receive AI responses via notifications
- **HAL Control**: Control servos, buzzer, and display over BLE
- **Cross-Platform**: Works with Web Bluetooth, React Native, and native iOS/Android apps

---

## Architecture

```
┌─────────────────┐     JSON Command      ┌──────────────────┐
│  Mobile Device  │ ──────────────────▶   │  ninja_ble       │
│  (nRF Connect)  │                       │  GATT Server     │
│                 │ ◀──────────────────   │                  │
└─────────────────┘     JSON Notify       └────────┬─────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │ CommandDispatcher│
                                          │   (ninja_core)   │
                                          └────────┬─────────┘
                                                   │
                              ┌────────────────────┼────────────────────┐
                              ▼                    ▼                    ▼
                         ┌────────┐          ┌──────────┐         ┌─────────┐
                         │  HAL   │          │  Agent   │         │   Web   │
                         │        │          │ (Gemini) │         │ Clients │
                         └────────┘          └──────────┘         └─────────┘
```

---

## BLE Service Specification

| Item | Value |
|---|---|
| **Service Name** | `NinjaRobot` |
| **Service UUID** | `00000001-710e-4a5b-8d75-3e5b444bc3cf` |

### Characteristics

| Name | UUID | Properties | Purpose |
|---|---|---|---|
| **Command** | `00000002-710e-...` | Write | Receive JSON commands |
| **Response** | `00000003-710e-...` | Read, Notify | Send JSON responses |

---

## JSON Protocol

### AI Chat
```json
// Send (Write to Command)
{"type": "chat", "text": "Tell me a joke"}

// Receive (Notify from Response)
{"type": "chat", "sender": "ninja", "text": "Why did the robot..."}
```

### HAL Control
```json
// Servo Control
{"type": "hal", "command": "execute", "payload": {"servos": {"angles": [0,0,0,0,0,0,0,0]}}}

// Buzzer Control
{"type": "hal", "command": "execute", "payload": {"buzzer": {"frequency": 440, "duration": 0.5}}}
```

---

## Chunking Protocol (Phase 3)

For large payloads (>512 bytes), use the binary chunking protocol:

### Packet Types

| Type | Byte | Format |
|---|---|---|
| HEADER | `0x01` | `[0x01][total_chunks:2B][crc32:4B][payload_len:4B]` |
| DATA | `0x02` | `[0x02][seq:2B][chunk_data:N bytes]` |
| EOF | `0x03` | `[0x03][chunks_received:2B]` |

### ACK Response
```json
{"type": "ack", "seq": 0, "status": "ok"}
{"type": "ack", "status": "complete"}
{"type": "ack", "status": "error", "msg": "CRC mismatch"}
```

### Flow
1. Client sends HEADER with metadata
2. Robot ACKs header
3. Client sends DATA packets (seq 0, 1, 2...)
4. Robot ACKs each chunk
5. Client sends EOF
6. Robot verifies CRC32, ACKs complete, dispatches payload

---

## Verification Instructions

### Prerequisites
- **iOS**: [nRF Connect for Mobile](https://apps.apple.com/us/app/nrf-connect-for-mobile/id1054362403)
- **Android**: [nRF Connect for Mobile](https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp)

### Step 1: Start the Server
```bash
uv run ninja_core server
```

Look for:
```
BLE Service started.
BLE Service 'NinjaRobot' advertising...
Ninja AI Agent initialized and attached to Dispatcher.
```

### Step 2: Connect via nRF Connect
1. Open nRF Connect → **SCAN**
2. Find **"NinjaRobot"** → Tap **CONNECT**
3. Expand service `00000001-710e-...`

### Step 3: Subscribe to Notifications
1. Find Response characteristic (`...0003...`)
2. Tap the **⬇️ (subscribe)** icon to enable notifications

### Step 4: Send a Chat Command
1. Find Command characteristic (`...0002...`)
2. Tap the **⬆️ (write)** icon
3. Select **Text** format
4. Enter: `{"type": "chat", "text": "Hello!"}`
5. Tap **Write**

### Step 5: Verify Response
- You should receive a notification (hex encoded JSON)
- Decode hex → `{"type": "chat", "sender": "ninja", "text": "..."}`

---

## Dependencies

- `bless>=0.2.6` (BLE GATT Server)
- `bleak>=0.21.0,<1.0.0` (BLE backend)
- `dbus-fast>=1.86.0` (BlueZ D-Bus on Linux)
- `ninja-core` (CommandDispatcher)

---

## License

MIT License © 2025 Chihkuang Chang
