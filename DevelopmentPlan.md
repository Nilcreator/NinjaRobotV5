# NinjaRobot V5 Development Plan

**Status:** Approved
**Version:** 1.0.0
**Last Updated:** 2025-12-30
**Objective:** Evolve NinjaRobot from a fixed V4 architecture to a modular, connected, and AI-adaptive V5 platform.

---

## 1. Project Vision

NinjaRobot V5 aims to be the ultimate educational & research robotics platform by addressing four key pillars:
1.  **Hyper-Modularity**: Transition from "hardcoded support" to a true "plugin-based" hardware architecture.
2.  **Dual Connectivity (Hybrid Mode)**: Simultaneous support for **Local Bluetooth (BLE)** control (instant, low-latency) and **Remote Web/ngrok** control (telepresence).
3.  **Visual Programming**: Integrated Google Blockly interface for drag-and-drop coding.
4.  **Adaptive AI Coding**: Elevate the AI agent to a "coding partner" capable of generating executable code.

---

## 2. Health Check Findings

A comprehensive line-by-line code review was conducted on 2025-12-30. The following issues were identified:

### 2.1 `ninja_utils`
| File | Finding | V5 Action |
|---|---|---|
| `my_logger.py` | Basic logger. | None (works as-is). |
| **MISSING** | No ABCs for hardware interfaces. | **Create `interfaces.py` with `Sensor`/`Actuator` ABCs.** |

### 2.2 `pi0buzzer`
| File | Finding | V5 Action |
|---|---|---|
| `driver.py` L31 | **Blocking `time.sleep()`** in `play_sound()`. | **Refactor to threaded sound queue.** |
| `driver.py` L22 | Hardcoded `"buzzer.json"` path. | **Inject config via constructor.** |
| **MISSING** | No ABC inheritance. | **Implement `Actuator` interface.** |

### 2.3 `pi0servo`
| File | Finding | V5 Action |
|---|---|---|
| `multi_servo.py` L~190 | Blocking `time.sleep()` in `move_angle_sync()`. | **Use existing `ThreadMultiServo` in core.** |
| `calibrable_servo.py` | Hardcoded `"servo.json"` path. | **Inject config via constructor.** |
| **MISSING** | No ABC inheritance. | **Implement `Actuator` interface.** |

### 2.4 `pi0disp`
| File | Finding | V5 Action |
|---|---|---|
| `st7789v.py` L~80 | Blocking `time.sleep()` during init (acceptable). | **Document.** |
| **MISSING** | No ABC inheritance. | **Implement `Actuator` interface.** |

### 2.5 `pi0vl53l0x`
| File | Finding | V5 Action |
|---|---|---|
| `driver.py` L~360 | Blocking `time.sleep()` in `get_range()` polling. | **Already wrapped by `perception.py` (threaded). No change needed.** |
| `driver.py` | Returns raw `int`. | **Create `DistanceData` dataclass.** |
| **MISSING** | No ABC inheritance. | **Implement `Sensor` interface.** |

### 2.6 `ninja_core`
| File | Finding | V5 Action |
|---|---|---|
| `hal.py` L14-17 | **Hardcoded driver imports.** | **Use `importlib` for dynamic loading.** |
| `hal.py` L52-100 | Hardcoded `if/elif` init logic. | **Replace with plugin loop from config.** |
| `perception.py` | Uses `threading` for background loop. | **Good! Keep as-is.** |
| `ninja_agent.py` | Uses async Gemini API. | **Good! Keep as-is.** |

---

## 3. Optimization of Existing Code & Libraries

### 3.1 Hardware Abstraction Layer (`ninja_core/hal.py`)

**Current State:**
- **Tight Coupling:** Explicitly imports drivers (`from pi0servo...`, `from pi0buzzer...`).
- **Initialization Logic:** Hardcoded `if/elif` blocks for each component.

**Optimization Plan (Phase 1):**
1.  **Dynamic Loading:** Use `importlib.import_module()` to load drivers based on class paths in `config.json`.
2.  **Dependency Injection:** Pass a shared `pigpio.pi()` instance to drivers.
3.  **Interface Validation:** Verify loaded drivers implement `Sensor` or `Actuator` ABCs.

### 3.2 Buzzer Driver (`pi0buzzer/driver.py`)

**Current State:** Blocking `time.sleep()` in `play_sound()` and `play_song()`.

**Optimization Plan (Phase 1):**
1.  **Threaded Sound Queue:** Implement a background worker thread that processes sounds from a queue.
2.  **Non-Blocking API:** `play_sound()` returns immediately after adding to the queue.
3.  **Config Injection:** Remove hardcoded `"buzzer.json"` path.
4.  **ABC Implementation:** Inherit from `Actuator` interface.

### 3.3 Servo Driver (`pi0servo`)

**Current State:** `MultiServo.move_angle_sync()` uses blocking `time.sleep()`.

**Optimization Plan (Phase 1):**
1.  **Use `ThreadMultiServo`:** The helper already exists in `pi0servo/helper/`. Use it in `ninja_core`.
2.  **Config Injection:** Remove hardcoded `"servo.json"` path.
3.  **ABC Implementation:** Inherit from `Actuator` interface.

### 3.4 Display Driver (`pi0disp/disp/st7789v.py`)

**Current State:** Synchronous SPI writes. `time.sleep()` during init is acceptable.

**Optimization Plan (Phase 1):**
1.  **ABC Implementation:** Inherit from `Actuator` interface.
2.  **Document Blocking:** Add docstring noting init blocking behavior.

### 3.5 Distance Sensor Driver (`pi0vl53l0x/driver.py`)

**Current State:** Blocking I2C polling in `get_range()`, but already wrapped by `perception.py`.

**Optimization Plan (Phase 1):**
1.  **No Driver Change Needed:** `perception.py` already runs in a background thread.
2.  **`DistanceData` Dataclass:** Create a standardized output format.
3.  **ABC Implementation:** Inherit from `Sensor` interface.

---

## 4. New Code & Library Development

### 4.1 `ninja_utils/interfaces.py` (NEW)

**Objective:** Define strict "contracts" (ABCs) for all hardware drivers.

**Contents:**
```python
from abc import ABC, abstractmethod

class Sensor(ABC):
    @abstractmethod
    def initialize(self) -> None: ...
    @abstractmethod
    def get_data(self) -> dict: ...
    @abstractmethod
    def close(self) -> None: ...

class Actuator(ABC):
    @abstractmethod
    def initialize(self) -> None: ...
    @abstractmethod
    def execute(self, command: dict) -> None: ...
    @abstractmethod
    def off(self) -> None: ...
```

> **Explanation:** ABCs act as strict "blueprints" that all hardware drivers must follow. This ensures `ninja_core` can interact with *any* sensor or actuator using the same standard commands (e.g., `initialize()`, `get_data()`), enabling true plugin-based modularity where you can swap hardware without rewriting the main code.

### 4.2 Dual Connectivity Architecture (Phase 2)

**Objective:** Enable simultaneous control via **Local BLE** (Priority: AI Chat) and **Remote Web**, managed by a strict dispatcher to handle concurrency.

#### A. System Diagram
```mermaid
graph TD
    subgraph "Ninja Core"
        Dispatcher[CommandDispatcher<br>(Singleton)]
        HAL[Hardware Abstraction Layer]
        Agent[Ninja Agent]
    end
    
    subgraph "Connectors"
        BLE[ninja_ble<br>GATT Server]
        Web[Web Server<br>FastAPI]
    end

    BLE -->|JSON Command| Dispatcher
    Web -->|JSON Command| Dispatcher
    Dispatcher -->|Control| HAL
    Dispatcher -->|Intent| Agent
    Dispatcher -->|Broadcast| BLE
    Dispatcher -->|Broadcast| Web
```

#### B. `ninja_ble` Specification
- **Library:** `bless` (AsyncIO compatible).
- **Service Name:** `NinjaRobot Service`
- **UUID:** `00000001-710e-4a5b-8d75-3e5b444bc3cf`

| Characteristic | UUID | Type | Purpose |
| :--- | :--- | :--- | :--- |
| **Command** | `...0002-...` | Write | JSON commands (Chat, HAL control). |
| **Response** | `...0003-...` | Notify | AI responses (text), Status updates. |

#### C. `CommandDispatcher` (The Brain)
- **Role:** Central traffic controller. Decouples input source from execution.
- **Protocol (JSON):**
    - **Chat:** `{ "type": "chat", "text": "..." }`
    - **Control:** `{ "type": "hal", "command": "execute", "payload": {...} }`
- **Output Routing:** AI responses are routed to **both** BLE (Notify) and Web (WebSocket) to keep clients in sync.

#### D. User Priorities
1.  🔴 **AI Chat over BLE** (Text-based) - Highest Priority
2.  🟡 **Basic Control** (Servos, Buzzer, Faces)
3.  🟢 **Sensor Streaming** (Distance, Status)

### 4.4 Visual Programming (Google Blockly - Phase 3)

**Objective:** Enable visual, block-based programming directly from the Web Interface.

**Integration Strategy:**
- **Frontend (`ninja_core/static`):** Integrate `blockly` JS assets. Define custom blocks for robot actions.
- **Backend (`ninja_core`):** `POST /api/blockly/execute` endpoint. Runs code in `SafeExecutor`.

### 4.5 `ninja_coder` (Phase 3)

**Objective:** AI Agent capability to write and execute code.

**Functions:**
- **`SafeExecutor`:** A wrapper utilizing `exec()` with restricted globals. Used by **both** Blockly and AI Agent.
- **`NinjaCoder`:** AI Agent generates Python code for the Executor.

---

## 5. Phase-by-Phase Roadmap

### Phase 1: Modularity & Foundation ✅ VERIFIED (2025-12-30)
- [x] Conduct comprehensive health check.
- [x] Create `ninja_utils/interfaces.py` with `Sensor`/`Actuator` ABCs.
- [x] Refactor `pi0buzzer` to threaded sound queue + ABC.
- [x] Refactor `pi0servo`, `pi0disp`, `pi0vl53l0x` to ABC.
- [x] Rewrite `ninja_core/hal.py` for dynamic loading.
- [x] Create `DistanceData` dataclass.
- [x] **Hardware verification on Raspberry Pi Zero 2W.**


### Phase 2: Dual Connectivity Implementation ✅ VERIFIED (2025-12-31)
- [x] Create `CommandDispatcher` singleton in `ninja_core`.
- [x] Develop `ninja_ble` library (GATT Server with `bless`).
- [x] Integrate BLE service with Web Server.
- [x] Route AI Agent responses through Dispatcher to BLE notifications.
- [x] **AI Chat via Bluetooth verified on Raspberry Pi Zero 2W.**

### Phase 3: BLE Protocol Upgrade (`ninja_ble`) ✅ Robot-Side Complete (2026-01-02)

> **Goal:** Support "Code Upload" (large payloads > 512 bytes) via a robust BLE Chunking Protocol.

**3.1 Robot-Side Chunking Logic (`ninja_ble`)** ✅
- [x] **Implement Chunk Buffering:**
    - Created `ChunkReassembler` class in `ninja_ble/chunking.py`.
    - Logic: Detect `Header` (0x01) -> Initialize Buffer -> Append `Data` (0x02) -> Finalize on `EOF` (0x03).
- [x] **Implement Flow Control (ACKs):**
    - ACKs sent via Notify on Response Characteristic.
    - JSON format: `{"type": "ack", "seq": N, "status": "ok"}`.
- [x] **Data Integrity:**
    - CRC32 verification using `binascii.crc32()`.
- [x] **Dispatch Integration:**
    - Payload dispatched only after full reassembly and CRC verification.
- [x] **Backward Compatibility:**
    - Legacy JSON commands still work (auto-detected by first byte).

**3.2 Web Client Protocol (`Code IDE`)**
- [x] **Protocol Verification (Robot-Side)**:
    - Verified `ChunkReassembler` against protocol specs using unit tests.
    - Confirmed Packet creation helpers match expected Client behavior.
    - Note: JS implementation moved to Phase 5.
- [ ] MTU negotiation logic (Deferred to Phase 5).

---

### Phase 4: Backend Core & Agent Intelligence (Week 6) ✅ COMPLETE (2026-01-03)

> **Goal:** Create the "brain" and "muscle" for running code safely and intelligently.

**4.1 Safe Execution Engine (`ninja_core`)**
- [x] **Implement `SafeExecutor`:**
    - Sandboxed `exec()` environment restricting access to `os`, `sys`.
    - Expose safe `robot` API (HAL wrapper) + `time`, `math`.
    - Thread-based execution with `stop()` capability.
- [x] **Command Dispatcher Upgrade:**
    - Wire `execute` command (from BLE/Web) to `SafeExecutor`.
    - Broadcast execution logs via WebSocket/BLE Notify.

**4.2 Code Agent (Backend)**
- [x] **Create `NinjaCoderAgent` Class:**
    - Specialized prompt for Python code generation and debugging.
    - Model: `gemini-3-flash-preview` (as requested).
    - Capabilities:
        - `generate_code(query)`: Operations -> Python Code.
        - `analyze_code(code)`: Python Code -> Bug Fixes/Advice.

**4.3 Web Server API Extensions**
- [x] `POST /api/code/execute`: Trigger `SafeExecutor`.
- [x] `POST /api/code/stop`: Terminate running code.
- [x] `POST /api/agent/code/analyze`: Send code to `NinjaCoderAgent`.

---

### Phase 5: Web Interface & Visual Programming (Week 7)

> **Goal:** A unified, mobile-optimized Web App for Chat, Coding, and Control.

**5.1 UI Architecture Overhaul (`templates/index.html`)**
- [ ] **Main Menu System:**
    - Landing page with large touch-friendly buttons: "Ninja Agent" vs "Code Agent".
    - **Multilingual Support**: Switcher for EN, JP, TC, SC (affects UI & Agent language).
- [ ] **System Log Window:**
    - Real-time scrolling log (WebSocket) showing BLE events, server status, and errors.

**5.2 Ninja Agent Interface**
- [ ] **Interaction Mode:**
    - Voice Input (Mic button) + Text Input.
    - Chat History Window (Styled bubbles).

**5.3 Code Agent Interface**
- [ ] **Mobile Blockly Integration:**
    - Embed Blockly library (via CDN or static assets).
    - Custom blocks for NinjaRobot API (`move`, `turn`, `express`, `say`).
    - Vertical layout optimization for mobile.
- [ ] **Python Code Editor:**
    - Read-only view (synced from Blockly) OR Mutable view.
    - **BLE Sync**: When code arrives via BLE, auto-populate this editor.
- [ ] **AI Side-Panel:**
    - "Fix Bug" / "Explain" buttons triggering `NinjaCoderAgent`.
    - Display AI advice overlay.


## 6. Ideal V5 Project File Structure

```text
NinjaRobotV5/
├── pyproject.toml
├── config.json
│
├── ninja_utils/
│   └── src/ninja_utils/
│       ├── interfaces.py       # Sensor/Actuator ABCs (NEW)
│       ├── my_logger.py
│       └── ...
│
├── ninja_ble/                  # Bluetooth Library (Phase 2)
│   └── src/ninja_ble/
│       ├── gatt_server.py
│       └── connection.py
│
├── ninja_core/
│   └── src/ninja_core/
│       ├── core/               # Core Logic (Phase 2/3)
│       │   ├── dispatcher.py   # Unified Command Dispatcher
│       │   └── executor.py     # SafeExecutor for Blockly/AI
│       ├── hal.py              # Refactored for dynamic loading
│       ├── static/
│       │   └── blockly/        # Blockly Assets (Phase 3)
│       ├── ninja_agent.py
│       ├── web_server.py       
│       └── ...
│
├── pi0servo/                   # Implements Actuator ABC
├── pi0disp/                    # Implements Actuator ABC
├── pi0vl53l0x/                 # Implements Sensor ABC
└── pi0buzzer/                  # Implements Actuator ABC (Threaded)
```
