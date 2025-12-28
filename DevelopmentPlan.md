# NinjaRobot V5 Development Plan

**Status:** Draft
**Version:** 0.2.0
**Last Updated:** 2025-12-28
**Objective:** Evolve NinjaRobot from a fixed V4 architecture to a modular, connected, and AI-adaptive V5 platform.

---

## 1. Project Vision

NinjaRobot V5 aims to be the ultimate educational & research robotics platform by addressing three key pillars:
1.  **Hyper-Modularity**: Transition from "hardcoded support" to a true "plugin-based" hardware architecture.
2.  **Seamless Connectivity**: Introduce Bluetooth Low Energy (BLE) support for direct local control.
3.  **Adaptive AI Coding**: Elevate the AI agent to a "coding partner" capable of generating executable code.

---

## 2. Optimization of Existing Code & Libraries

### 2.1 Hardware Abstraction Layer (`ninja_core/hal.py`)

**Current State:**
- **Tight Coupling:** Explicitly imports `MultiServo`, `ST7789V`, `VL53L0X`. Adding a new sensor requires modifying `hal.py`.
- **Initialization Logic:** Hardcoded `if/elif` blocks for each component type.

**Optimization Plan (Phase 1):**
1.  **Dynamic Loading:** Use Python's `importlib` to load drivers based on strings in `config.json` (e.g., `"driver": "pi0vl53l0x.driver.VL53L0X"`).
2.  **Dependency Injection:** Pass a generic `IOManager` (wrapping `pigpio`) to drivers instead of raw `pigpio.pi` instances, facilitating future hardware portability.
3.  **Interface Standardization:** Enforce that all loaded drivers adhere to `Sensor` or `Actuator` protocols.

### 2.2 VL53L0X Driver (`pi0vl53l0x/driver.py`)

**Current State:**
- **Blocking Calls:** Uses `time.sleep()` and `while` loops for valid data waits, blocking the main thread.
- **Return Type:** Returns raw `int` (mm), managing error states via magic numbers (e.g., `8190`).

**Optimization Plan (Phase 1):**
1.  **Non-Blocking I/O:** Refactor `get_range` to support an `async` interface or offload polling to a background thread (similar to `ThreadMultiServo`).
2.  **Standardized Output:** Return a `DistanceData` dataclass (timestamp, distance, confidence, valid_flag) instead of raw integers.
3.  **Error Handling:** Replace magic numbers with explicit `SensorError` exceptions or status enums.

### 2.3 Servo Driver (`pi0servo/core/piservo.py`)

**Current State:**
- **Robustness:** Currently good, but relying on `pigpio` daemon presence without fallback/mocking for testing.
- **Calibration:** `calib` tool is separate; better to integrate calibration data loading directly into the driver's `__init__`.

**Optimization Plan (Phase 1):**
1.  **Unified Configuration:** Move calibration logic inside the `MultiServo` class, accepting a standard config dictionary.
2.  **Mocking Support:** Implement a `MockServo` mode when `pigpio` is unavailable, allowing development on non-Pi machines.

### 2.4 Display Driver (`pi0disp/disp/st7789v.py`)

**Current State:**
- **Initialization:** Contains hardcoded delays (`time.sleep`) in the main thread.
- **Rendering:** `display` method blocks until SPI transfer is complete.

**Optimization Plan (Phase 1):**
1.  **Async Rendering:** Move the SPI write loop to a separate thread/task. The main loop pushes `PIL.Image` frames to a queue.
2.  **Frame Dropping:** Implement logic to drop frames if the rendering queue grows too large (preventing lag).

---

## 3. New Code & Library Development

### 3.1 `ninja_ble` (New Library)

**Objective:** Provide Bluetooth Low Energy (BLE) connectivity for local control without WiFi.

**Functions:**
- **GATT Server:** Hosts the `NinjaRobotService`.
- **Command Characteristic (Write):** Accepts JSON payloads for motor control (e.g., `{"cmd": "move", "servo": 1, "angle": 90}`).
- **Status Characteristic (Notify):** Streams sensor data (distance, battery) at 10Hz.
- **Terminal Characteristic (Notify):** Streams stdout/logs to the client.

**Integration:**
- Runs as a separate service/thread within `ninja_core`.
- Shares the same `CommandDispatcher` as the Web Server to ensure consistent behavior.

### 3.2 `ninja_interfaces` (New Module in `ninja_utils`)

**Objective:** Define the contracts for all hardware components.

**Functions:**
- **`Sensor` (ABC):**
    - `initialize(config: dict)`
    - `read() -> SensorData`
    - `shutdown()`
- **`Actuator` (ABC):**
    - `initialize(config: dict)`
    - `execute(command: str, params: dict)`
    - `shutdown()`

**Integration:**
- All hardware libraries (`pi0*`) will import and inherit from these ABCs.
- `ninja_core` type-checks loaded drivers against these interfaces.

### 3.3 `ninja_coder` (New Module in `ninja_core`)

**Objective:** A sandboxed environment for the AI Agent to generate and execute code.

**Functions:**
- **`CodeGenerator`:** specialized prompt chain for Gemini to output Python functions.
- **`SafeExecutor`:** A wrapper utilizing `exec()` with restricted globals (only `hal`, `time`, `math` allowed).
- **`ScriptManager`:** Saves validated scripts to `user_scripts/` for persistence.

**Integration:**
- `NinjaAgent` calls `CodeGenerator` when it detects an intent to "create a new behavior".
- `SafeExecutor` has access to the initialized `HAL` instance to control hardware.

---

## 4. Phase-by-Phase Roadmap

### Phase 1: Modularity & Foundation (Weeks 1-2)
1.  Create `ninja_interfaces` with ABCs.
2.  Refactor `pi0vl53l0x`, `pi0servo`, `pi0disp` to inherit from ABCs.
3.  Rewrite `ninja_core.hal` to use dynamic loading.
4.  Update `config.json` schema to include driver paths.

### Phase 2: Connectivity (Weeks 3-4)
1.  Develop `ninja_ble` using `bless` or `dbus-fast`.
2.  Integrate BLE service into `ninja_core` startup.
3.  Create a simple static HTML/JS web client (hosted on GitHub Pages) to test Web Bluetooth connection.

### Phase 3: AI Code Agent (Weeks 5-6)
1.  Implement `ninja_coder` module.
2.  Update `NinjaAgent` system prompt to handle code generation requests.
3.  Create the `SafeExecutor` sandbox and test with simple movement scripts.

---

## 5. Ideal V5 Project File Structure

```text
NinjaRobotV5/
├── pyproject.toml              # Unified dependencies (adds bleak/bless)
├── config.json                 # Updated with "driver_class" fields
├── driver_config/              # New: Folder for individual hardware configs
│   ├── servo.json
│   ├── buzzer.json
│   └── sensors.json
│
├── ninja_utils/
│   └── src/ninja_utils/
│       ├── interfaces.py       # [NEW] Sensor/Actuator ABCs
│       ├── my_logger.py
│       └── ...
│
├── ninja_ble/                  # [NEW] Bluetooth Library
│   ├── pyproject.toml
│   └── src/ninja_ble/
│       ├── __init__.py
│       ├── gatt_server.py      # BLE Service definition
│       └── connection.py       # Connection manager
│
├── ninja_core/
│   └── src/ninja_core/
│       ├── hal/
│       │   ├── __init__.py
│       │   ├── loader.py       # [NEW] Dynamic driver loader
│       │   ├── manager.py      # [Refactored] Replaces old hal.py
│       ├── coder/              # [NEW] AI Coding System
│       │   ├── generator.py    # Gemini wrapper for code gen
│       │   └── executor.py     # Sandboxed execution
│       ├── ninja_agent.py
│       ├── web_server.py       
│       └── ...
│
├── pi0servo/ (Refactored to inherit Actuator)
├── pi0disp/ (Refactored to inherit Actuator)
├── pi0vl53l0x/ (Refactored to inherit Sensor)
└── ...
```
