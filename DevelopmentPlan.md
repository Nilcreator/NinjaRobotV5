# NinjaRobot V5 Development Plan

**Status:** Draft
**Version:** 0.4.0
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

## 2. Optimization of Existing Code & Libraries

### 2.1 Hardware Abstraction Layer (`ninja_core/hal.py`)

**Current State:**
- **Tight Coupling:** Explicitly imports drivers.
- **Initialization Logic:** Hardcoded `if/elif` blocks.

**Optimization Plan (Phase 1):**
1.  **Dynamic Loading:** Use `importlib` for driver loading based on `config.json`.
2.  **Dependency Injection:** Pass generic `IOManager` to drivers.
3.  **Interface Standardization:** Enforce `Sensor`/`Actuator` protocols.

### 2.2 VL53L0X Driver (`pi0vl53l0x/driver.py`)

**Current State:** Blocking calls, raw return types.

**Optimization Plan (Phase 1):**
1.  **Non-Blocking I/O:** Refactor `get_range` to `async` or threaded.
2.  **Standardized Output:** Return `DistanceData` dataclass.
3.  **Error Handling:** Use explicit exceptions.

### 2.3 Servo Driver (`pi0servo/core/piservo.py`)

**Current State:** Good basics, but calibration logic is separated.

**Optimization Plan (Phase 1):**
1.  **Unified Configuration:** Integrate calibration into `MultiServo`.
2.  **Mocking Support:** Add `MockServo` for dev-without-hardware.

### 2.4 Display Driver (`pi0disp/disp/st7789v.py`)

**Current State:** Blocking SPI transfers.

**Optimization Plan (Phase 1):**
1.  **Async Rendering:** Threaded SPI writes.
2.  **Frame Dropping:** Prevents lag during heavy load.

---

## 3. New Code & Library Development

### 3.1 `ninja_ble` (New Library for Local Connectivity)

**Objective:** Enable direct, zero-setup local control via Bluetooth Low Energy.

**Functions:**
- **GATT Server:** Hosts `NinjaRobotService`.
- **Characteristics:** `Command` (Write), `Status` (Notify), `Console` (Notify).
- **Concurrency:** Operates alongside the Web Server.

### 3.2 Connectivity Orchestration (Dual Mode)

**Objective:** Seamlessly manage inputs from both BLE and Web/ngrok.

**Architecture:**
- **Command Dispatcher (Singleton):** The single source of truth for robot state.
- **State Synchronization:** Broadcasts updates to WebSocket clients and BLE notifications.
- **Conflict Resolution:** "Last Command Wins" policy.

### 3.3 Visual Programming (Google Blockly Integration)

**Objective:** Enable visual, block-based programming directly from the Web Interface.

**Integration Strategy:**
- **Frontend (`ninja_core/static`):**
    - Integrate `blockly_compressed.js`, `blocks_compressed.js`, `python_compressed.js`.
    - **Custom Blocks:** Define blocks for Robot Actions (e.g., `servo_move`, `play_sound`, `show_face`, `check_distance`).
    - **UI Layout:** Add a "Blockly Workspace" tab/section to `index.html`.
- **Backend (`ninja_core`):**
    - **Execution Endpoint:** `POST /api/blockly/execute` receives generated Python code.
    - **Sandbox:** The code runs in a restricted scope (using the same `SafeExecutor` as the AI Coder) with access to the `dispatcher`.

### 3.4 `ninja_interfaces` & `ninja_coder`

**Objective:** Define contracts and Safe Execution Environment.

**Functions:**
- **`Sensor` / `Actuator` ABCs.**
- **`SafeExecutor`:** A wrapper utilizing `exec()` with restricted globals. Used by **both** Blockly and AI Agent.

---

## 4. Phase-by-Phase Roadmap

### Phase 1: Modularity & Foundation (Weeks 1-2)
1.  Create `ninja_interfaces` with ABCs.
2.  Refactor `pi0vl53l0x`, `pi0servo`, `pi0disp` to inherit from ABCs.
3.  Rewrite `ninja_core.hal` to use dynamic loading.

### Phase 2: Dual Connectivity Implementation (Weeks 3-4)
1.  Refactor `ninja_core` to create a unified `CommandDispatcher`.
2.  Develop `ninja_ble`.
3.  Integrate BLE service and WebSocket server.

### Phase 3: Visual Programming & AI (Weeks 5-7)
1.  **Blockly Integration:**
    - Embed Blockly in Web UI.
    - Create Custom Blocks for NinjaRobot API.
    - Implement `SafeExecutor` backend.
2.  **AI Integration:**
    - Implement `ninja_coder` logic.
    - Update `NinjaAgent` prompts for code generation.

---

## 5. Ideal V5 Project File Structure

```text
NinjaRobotV5/
├── pyproject.toml
├── config.json
├── driver_config/
│   ├── servo.json
│   ├── buzzer.json
│   └── sensors.json
│
├── ninja_utils/
│   └── src/ninja_utils/
│       ├── interfaces.py       # Sensor/Actuator ABCs
│       └── ...
│
├── ninja_ble/                  # Bluetooth Library
│   └── src/ninja_ble/
│       ├── gatt_server.py
│       └── connection.py
│
├── ninja_core/
│   └── src/ninja_core/
│       ├── core/               # Core Logic
│       │   ├── dispatcher.py   # Unified Command Dispatcher
│       │   └── executor.py     # [NEW] SafeExecutor for Blockly/AI
│       ├── hal/
│       │   ├── loader.py
│       │   └── manager.py
│       ├── static/
│       │   ├── blockly/        # [NEW] Blockly Assets
│       │   ├── css/
│       │   └── js/
│       ├── ninja_agent.py
│       ├── web_server.py       
│       └── ...
│
├── pi0servo/
├── pi0disp/
└── pi0vl53l0x/
```
