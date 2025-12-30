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

### 4.2 `ninja_ble` (NEW - Phase 2)

**Objective:** Enable direct, zero-setup local control via Bluetooth Low Energy.

**Functions:**
- **GATT Server:** Hosts `NinjaRobotService`.
- **Characteristics:** `Command` (Write), `Status` (Notify), `Console` (Notify).
- **Concurrency:** Operates alongside the Web Server via `CommandDispatcher`.

### 4.3 Connectivity Orchestration (Dual Mode - Phase 2)

**Objective:** Seamlessly manage inputs from both BLE and Web/ngrok.

**Architecture:**
- **Refactor `ninja_core`:** Create `CommandDispatcher` singleton.
- **State Synchronization:** Broadcasts updates to WebSocket clients and BLE notifications.
- **Conflict Resolution:** "Last Command Wins" policy.

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

### Phase 1: Modularity & Foundation (Weeks 1-2) ✅ COMPLETE
- [x] Conduct comprehensive health check.
- [x] Create `ninja_utils/interfaces.py` with `Sensor`/`Actuator` ABCs.
- [x] Refactor `pi0buzzer` to threaded sound queue + ABC.
- [x] Refactor `pi0servo`, `pi0disp`, `pi0vl53l0x` to ABC.
- [x] Rewrite `ninja_core/hal.py` for dynamic loading.
- [x] Create `DistanceData` dataclass.


### Phase 2: Dual Connectivity Implementation (Weeks 3-4)
- [ ] Create `CommandDispatcher` singleton in `ninja_core`.
- [ ] Develop `ninja_ble` library.
- [ ] Integrate BLE service with WebSocket server.

### Phase 3: Visual Programming & AI (Weeks 5-7)
- [ ] Integrate Google Blockly into frontend.
- [ ] Implement `SafeExecutor` backend.
- [ ] Implement `ninja_coder` AI code generation.

---

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
