# Development Log

## 2026-01-07: Phase 5.2 - Educational 2-Agent Workflow & API Optimization - COMPLETE
- **Action**: Enhanced Backend & Frontend for Code Platform (`app`) Integration.
- **Details**:
    - **Backend (ninja_core)**:
        - Added `move_all()` and `center()` batch methods to `ServoArrayWrapper`.
        - Updated `NinjaCoderAgent` prompt to strictly enforce optimization of sequential servo commands.
        - Updated `CommandDispatcher` to enforce `Code Agent -> Executor` pipeline for all code execution and broadcast "Optimized Code" feedback.
    - **Code Platform (app)**:
        - Updated `ninja_servo_all` generator to use `move_all()` API.
        - Updated `useBluetooth` hook to expose received messages.
        - Updated `Editor` UI to display "AI Optimization" alerts when code is improved by the backend.
- **Related Files**: `api_wrappers.py`, `ninja_coder.py`, `dispatcher.py`, `generators.js`, `Editor/index.jsx`.

## 2026-01-07: Health Check & Optimization Implementation - COMPLETE
- **Action**: Resolved Agent Feedback, Movement Pipelining, and Shutdown issues.
- **Details**:
    - **Agent Feedback**: `NinjaCoderAgent` returns structured JSON; `CommandDispatcher` parsing added.
    - **Pipelining**: Updated Agent rules for `move_all` batching.
    - **Robust Shutdown**: Updated `web_server.py` with task cancellation and timeout logic.
    - **Fixes**: Corrected `ServoArrayWrapper.move_all` bug (`self._multi_servo`), added ngrok connection feedback.
- **Verification**: `ruff` passed. `RuntimeError` resolved.
- **Verification**: `ruff` linting passed for all core files.
- **Related Files**: `ninja_core/ninja_coder.py`, `ninja_core/dispatcher.py`, `ninja_core/web_server.py`, `ninja_core/perception.py`.

## 2026-01-04: Phase 5 Web Interface - COMPLETE
- **Action**: Implemented complete React-based Web Application (`ninja_webapp`).
- **Details**:
    - **Project Setup**: Created `ninja_webapp/` with Vite, React 18, react-router-dom, react-i18next.
    - **Pages Implemented**:
        - **Home**: Hero image, gradient title, power-off slider (V4-style touch drag).
        - **Agent**: Full-width chat dialog, hardware controls (expressions/sounds/movements), distance sensor display, slidable bottom log panel.
        - **Help**: Documentation and troubleshooting.
    - **Components**: Layout (Header, Footer), Button, IconButton, LanguageSelector, PowerOffSlider.
    - **Features**:
        - Multi-language support (EN, JA, ZH-TW, ZH-CN).
        - BLE advertising status indicator in header.
        - Voice input via Web Speech API with language auto-detection.
        - Real-time WebSocket events (`/ws/distance`, `/ws/events`).
        - Hardware controls via REST API endpoints.
    - **Backend Updates**:
        - Fixed `RuntimeError: no running event loop` in hardware endpoints.
        - Added `/api/system/shutdown` endpoint.
        - Updated `/api/ble/status` to return advertising state.
        - Fixed WebSocket `/ws/events` to use `asyncio.sleep` instead of blocking.
    - **Code Cleanup**:
        - Removed Code page and Blockly integration (simplification).
        - Removed `services/blockly/` and `services/bluetooth/` directories.
        - Bundle size reduced from ~1MB to 304KB.
- **Verification**: Build successful (Vite 7.3.0, 648ms). Mobile layout verified.
- **Related Files**: `ninja_webapp/src/*`, `ninja_core/web_server.py`

## 2026-01-03: Phase 4 Backend Core & Agent Intelligence - COMPLETE
- **Action**: Implemented Safe Execution Engine and NinjaCoder Agent.
- **Details**:
    - Created `ninja_core/safe_executor.py`: Threaded logic for safe code execution (restricted globals).
    - Created `ninja_core/ninja_coder.py`: AI Agent specialized for Python coding (Gemini 3 Flash).
    - Updated `ninja_core/dispatcher.py`: Integrated `SafeExecutor` with real-time log broadcasting.
    - Updated `ninja_core/web_server.py`: Added API endpoints (`/api/code/execute`, `/api/code/analyze`).
- **Verification**: `test_safe_executor.py` passed. Linting verified.
- **Cleanup**: Removed legacy `app` folder (web client moved to Phase 5).
- **Related Files**: `safe_executor.py`, `ninja_coder.py`, `dispatcher.py`, `web_server.py`

## 2026-01-04: Phase 4 Refinement - Code Execution & Error Feedback
- **Action**: Enhanced `SafeExecutor` and `Dispatcher` for better user feedback.
- **Details**:
    - **Safe Imports**: Patched `SafeExecutor` to allow `time`, `math`, `random` via custom `__import__`.
    - **API Wrappers**: Implemented `RobotWrapper` in `api_wrappers.py` to bridge the gap between low-level HAL and Blockly/IDE high-level API.
    - **AI Code Translation**: Implemented `translate_code` in `NinjaCoderAgent` and hooked it into `CommandDispatcher`. Incoming code is now automatically optimized/fixed by the AI Agent before execution (e.g., mapping "startup" sound to tones).
    - **Ninja Core Compatibility**: Mocked `from ninja_core import robot` to return the Wrapped Robot instance.
    - **Error Feedback**: Implemented `on_complete` callback in `SafeExecutor`.
    - **Agent Integration**: `Dispatcher` now broadcasts "Optimizing..." status and error diagnosis.
- **Verification**: `test_safe_executor.py` updated and passed.
- **Related Files**: `safe_executor.py`, `dispatcher.py`, `ninja_coder.py`, `test_safe_executor.py`, `api_wrappers.py`
- **WebSocket Fix (2026-01-04)**: Added `ConnectionManager` and `/ws/events` endpoint to bridge `Dispatcher` broadcasts to the Web UI. Fixed critical JavaScript syntax error in `main.js` (`pass;` was Python, not JS) that prevented the event WebSocket from connecting.
- **System Prompt Refinement (2026-01-04)**: Rewrote `NinjaCoderAgent` system prompt with comprehensive API tables, explicit sound/image mappings (e.g., "startup" → tones, "success" → "happy"), and strict translation rules to ensure clean code output.

## 2026-01-03: Phase 3 BLE Protocol Upgrade - COMPLETE
- **Action**: Verified BLE Client Protocol logic on Robot Hardware.
- **Details**:
    - Created and passed unit tests (`test_ble_chunking.py`) for `ChunkReassembler`.
    - Confirmed robust handling of Header/Data/EOF packets, CRC32 checks, and ACK flow control.
    - **Verification**: `python3 test_ble_chunking.py` passed (5 tests).
    - **Note**: Web Client JS implementation deferred to Phase 5.
- **Action**: Implemented chunking protocol for large BLE payloads + execute command handler.
- **Details**:
    - Created `ninja_ble/chunking.py` with `ChunkReassembler` class.
    - Protocol: HEADER (0x01) → DATA (0x02) → EOF (0x03) binary packets.
    - CRC32 verification for data integrity.
    - ACK flow control via Notify characteristic.
    - Backward compatible: legacy JSON still works.
    - Added `"type": "execute"` handler in `CommandDispatcher`.
    - Enhanced logging shows full received code content (WARNING level).
- **Verification**: BLE transmission verified - code received on robot.
- **Related Files**: `ninja_ble/chunking.py`, `ninja_ble/service.py`, `ninja_core/dispatcher.py`

## 2025-12-31: Phase 2 Dual Connectivity - COMPLETE
- **Action**: Implemented BLE integration with AI chat support.
- **Details**:
    - Created `ninja_ble` library with GATT server using `bless`.
    - Implemented `CommandDispatcher` singleton in `ninja_core` for routing commands.
    - Integrated BLE with Web Server for dual connectivity.
    - AI Agent responses now broadcast via BLE notifications.
    - Fixed `bleak` version compatibility (pinned to `<1.0.0`).
    - Fixed callback registration using `server.write_request_func` property.
- **Verification**: AI Chat tested successfully via nRF Connect on iOS.
- **Related Files**: `ninja_ble/service.py`, `ninja_core/dispatcher.py`, `ninja_core/web_server.py`

## 2025-12-30: Phase 1 Documentation Update
- **Action**: Updated all documentation to reflect Phase 1 completion.
- **Details**:
    - **README.md**: Updated Current Status to "Phase 1 Complete ✅" (EN/JP).
    - **DevelopmentPlan.md**: Marked Phase 1 as "VERIFIED (2025-12-30)".
    - **Library READMEs**: Added "V5 Changes" section to pi0buzzer, pi0vl53l0x, pi0servo, pi0disp.
    - **ninja_core/README.md**: Added V5 Changes section with driver registry.
    - **DevelopmentGuide.md**: Updated header to V5, added V5 Changes Summary.
    - **InstallationGuide.md**: Updated header to V5, changed `import-all` to `import`.
- **Related Files**: All documentation files.

## 2025-12-30: Config Import CLI Fix
- **Action**: Added `uv run ninja_core config import` command.
- **Details**: The original command was `import-all`. Added `import` as an alias for convenience.
- **Related Files**: `ninja_core/__main__.py`

## 2025-12-30: Phase 1 Integration Fixes
- **Action**: Fixed issues discovered during hardware testing.
- **Details**:
    - **pi0buzzer CLI**: Added `initialize()` calls to `beep`, `init`, and `playmusic` commands.
    - **HAL Logging**: Added debug logging with helpful tips when servo/buzzer initialization is skipped.
    - **Walkthrough**: Added missing calibration and config import steps (2a-2c).
- **Root Cause**: HAL requires `config.json` to have data imported from `buzzer.json` and `servo.json`.
- **Related Files**: `pi0buzzer/__main__.py`, `ninja_core/hal.py`, `walkthrough.md`

## 2025-12-30: Phase 1 Modularity & Foundation - COMPLETE
- **Action**: Implemented all Phase 1 tasks for V5 modular architecture.
- **Details**:
    - Created `ninja_utils/interfaces.py` with `Sensor`, `Actuator` ABCs and `DistanceData` dataclass.
    - Refactored `pi0buzzer` to use **threaded sound queue** for non-blocking playback.
    - Refactored `pi0vl53l0x` with `get_data()` method for standardized sensor output.
    - Refactored `pi0disp` with `initialize()`, `execute()`, `off()` methods.
    - Refactored `pi0servo/multi_servo.py` with ABC interface methods.
    - Refactored `ninja_core/hal.py` with **dynamic driver loading** via `importlib` and driver registry.
    - All files pass `ruff` linting.
- **Manual Checkpoints**: See task.md for Raspberry Pi verification steps.
- **Related Files**: `interfaces.py`, `driver.py` (buzzer, vl53l0x), `st7789v.py`, `multi_servo.py`, `hal.py`


## 2025-12-30: V5 Development Plan Refined (v1.0.0)
- **Action**: Refined `DevelopmentPlan.md` based on approved implementation plan.
- **Details**:
    - Added comprehensive "Health Check Findings" section summarizing all library issues.
    - Detailed refactoring plans for each driver (`pi0buzzer` threaded queue, ABC implementations).
    - Updated Phase 1 roadmap with specific tasks and checkboxes.
    - Clarified that `pi0vl53l0x` blocking is already mitigated by `perception.py` threading.
    - Added ABC code preview for `interfaces.py`.
- **Related Files**: `DevelopmentPlan.md`

## 2025-12-30: Comprehensive Codebase Health Check
- **Action**: Conducted line-by-line review of all libraries using Serena `read_file`.
- **Details**:
    - **`ninja_utils`**: Basic logging, no ABCs. Need to add `interfaces.py`.
    - **`pi0buzzer`**: Blocking `time.sleep()` in `play_sound()`, hardcoded config path.
    - **`pi0servo`**: Blocking `time.sleep()` in `move_angle_sync()`, hardcoded config path.
    - **`pi0disp`**: Blocking init (acceptable), no ABC.
    - **`pi0vl53l0x`**: Blocking I2C polling, but wrapped by `perception.py` (threaded).
    - **`ninja_core/hal.py`**: Hardcoded driver imports, tight coupling.
- **Related Files**: All library source files.

## 2025-12-30: Refined System Instructions (GEMINI.md)
- **Action**: Updated `GEMINI.md` to reflect V5 requirements.
- **Details**:
    - Explicitly listed MCP tools (`Serena`, `SequentialThinking`) and their usage strategies.
    - Defined "Core Capabilities" emphasizing Asyncio and Defensive Coding for RPi Zero 2W.
    - Updated "Project Architecture" to match the V5 modular design (`ninja_core`, `ninja_ble`, `ninja_interfaces`).
    - Removed outdated V4-specific context.
- **Related Files**: `GEMINI.md`

## 2025-12-30: V5 ABC Explanation
- **Action**: Added explanation of ABCs (Abstract Base Classes) to `DevelopmentPlan.md`.
- **Details**:
    - Clarified that ABCs serve as "blueprints" or "contracts" for hardware drivers.
    - Explained how this enables plugin-based modularity by allowing `ninja_core` to interact with generic interfaces rather than specific implementations.
- **Related Files**: `DevelopmentPlan.md`

## 2025-12-30: V5 Health Check & Plan Refinement
- **Action**: Conducted comprehensive codebase health check and refined `DevelopmentPlan.md`.
- **Details**:
    - Analyzed `pi0buzzer` and identified blocking I/O and hardcoded config paths.
    - Updated plan to include `pi0buzzer` refactoring (Async/Threaded).
    - Added "General Codebase Health" section to plan (Unified Logging, Centralized Config).
    - Confirmed `hal.py` coupling and reinforced need for dynamic loading.
- **Related Files**: `DevelopmentPlan.md`

## 2025-12-30: V5 README Blockly Update
- **Action**: Updated `README.md` to reflect Blockly Integration.
- **Details**:
    - Added "Visual Programming (Blockly)" as a key V5 feature.
    - Updated System Architecture diagram to include "Blockly Editor" and "Code Sandbox".
    - Updated "Current Status" to include Visual Programming in Phase 3.
- **Related Files**: `README.md`

## 2025-12-30: V5 Blockly Integration Plan
- **Action**: Updated `DevelopmentPlan.md` to include Google Blockly Integration.
- **Details**:
    - Added "Visual Programming" as a key project pillar.
    - Defined "Phase 3: Visual Programming & AI" to cover both Blockly and AI Code Agent.
    - Outlined technical strategy: Frontend Blockly workspace + Backend `SafeExecutor` (shared with AI Agent).
    - Updated File Structure to include `ninja_core/static/blockly/`.
- **Related Files**: `DevelopmentPlan.md`

## 2025-12-28: V5 Connectivity Refinement
- **Action**: Refined V5 Plan and README for Dual Connectivity.
- **Details**:
    - Architected the coexistence of Bluetooth (local) and ngrok (remote) via a unified `CommandDispatcher`.
    - Updated `DevelopmentPlan.md` and `README.md` to explicitely describe the "Dual Connectivity (Hybrid Mode)".
    - Defined shared state synchronization synchronization strategy.
- **Related Files**: `README.md`, `DevelopmentPlan.md`

## 2025-12-28: V5 README Update
- **Action**: Updated `README.md` to reflect V5 goals.
- **Details**:
    - Replaced V4 documentation with V5 vision: Hyper-Modularity, Connectivity, Agentic AI.
    - Updated System Architecture diagram to show plugin-based HAL.
    - Updated "Current Status" to indicate "V5 Alpha Planning".
- **Related Files**: `README.md`, `DevelopmentPlan.md`

## 2025-12-28: V5 Planning Init
- **Action**: Initialized V5 Development Plan.
- **Details**:
    - Drafted `DevelopmentPlan.md` outlining the roadmap for Modularity, Connectivity (BLE), and AI Code Integration.
    - Transitioning focus from V4 maintenance to V5 architecture evolution.
- **Objective**: Establish the foundation for a plugin-based, Bluetooth-enabled educational robot platform.
