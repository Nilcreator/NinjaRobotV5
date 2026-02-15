# Development Log


## 2026-02-16: pi0vl53l0x — Consolidated Interactive `sensor-tool` CLI ✓
- **Action**: Consolidated CLI into a single interactive `sensor-tool` TUI command.
- **Details**:
    - Merged interactive TUI (originally `vl53l0x_tool.py`) into `sensor_tool.py` as the `sensor-tool` subcommand.
    - Removed redundant individual CLI commands (`get`, `performance`, `calibrate`, `test`, `status`, `config`) — all functionality is now accessible through the 8-option interactive menu.
    - Deleted `vl53l0x_tool.py`. Single file `sensor_tool.py` now contains the `cli` group + `sensor-tool` command.
    - Simplified `__main__.py` — imports `cli` and `main` directly from `sensor_tool.py`.
    - Uses `blessed` for TUI rendering and `click` for command registration, matching `pi0servo`'s `servo-tool` pattern.
    - Updated `pi0vl53l0x/README.md`: removed old individual command docs, renamed to `sensor-tool`, updated directory structure.
- **Related Files**: `pi0vl53l0x/src/pi0vl53l0x/cli/sensor_tool.py`, `pi0vl53l0x/src/pi0vl53l0x/__main__.py`, `pi0vl53l0x/src/pi0vl53l0x/cli/__init__.py`, `pi0vl53l0x/pyproject.toml`, `pi0vl53l0x/README.md`.

## 2026-02-16: pi0vl53l0x Bug Fix — Entry Point & pigpio Import ✓
- **Action**: Fixed two critical bugs in pi0vl53l0x CLI and documented `uv sync` installation.
- **Details**:
    - Fixed `ImportError: cannot import name 'cli'` — root `pyproject.toml` referenced `:cli` but `__main__.py` only exported `main`. Now exports both.
    - Aligned `pi0vl53l0x/pyproject.toml` entry point to `:cli` (matching root convention).
    - Guarded top-level `VL53L0X` import in `__init__.py` for environments without pigpio.
    - Improved `_connect_pigpio()` error message with `uv sync --extra pi` instructions.
    - Added `uv sync` (recommended) alongside `uv pip install -e .` in `InstallationGuide.md` Step 6.3 (EN/JA/ZH-TW).
    - Updated `pi0vl53l0x/README.md` installation section with `uv sync --extra pi`.
- **Related Files**: `pi0vl53l0x/src/pi0vl53l0x/__main__.py`, `pi0vl53l0x/src/pi0vl53l0x/__init__.py`, `pi0vl53l0x/src/pi0vl53l0x/cli/sensor_tool.py`, `pi0vl53l0x/pyproject.toml`, `InstallationGuide.md`, `pi0vl53l0x/README.md`.

## 2026-02-15: InstallationGuide.md — pi0vl53l0x V2 Content Refinement ✓
- **Action**: Expanded all pi0vl53l0x sections in `InstallationGuide.md` (EN/JA/ZH-TW) to reflect V2 CLI.
- **Details**:
    - Step 7.2 (Test Distance Sensor): Added `test`, `status`, and `calibrate` commands.
    - Test 8.4 (Performance): Added `status` and `config show` commands.
    - Troubleshooting (Distance sensor not responding): Added `test`/`status` diagnostics and power-cycle guidance.
- **Related Files**: `InstallationGuide.md`.

## 2026-02-15: pi0vl53l0x V2 Documentation Update ✓
- **Action**: Updated all project documentation to reflect the pi0vl53l0x V2 rebuild.
- **Details**:
    - `DevelopmentGuide.md`: Rewrote section 3.3 (new I2C/sensor/config/CLI modules, full API reference tables, exception contract, usage examples). Updated file tree, version to 5.2.3, added V5.2.3 change summary, updated dependency graph.
    - `README.md`: Updated version to 5.2.3 and pi0vl53l0x V2 status in EN/JA/ZH-TW.
    - `pi0vl53l0x/README.md`: Full rewrite with directory structure, installation, Python API examples, complete API reference, 8 CLI commands with examples, test coverage table, and ASCII architecture diagram.
- **Related Files**: `DevelopmentGuide.md`, `README.md`, `pi0vl53l0x/README.md`.

## 2026-02-14: pi0vl53l0x V2 Library Rebuild — COMPLETE ✓
- **Action**: Full rewrite of the VL53L0X distance sensor driver from scratch.
- **Details**:
    - **Phase 1 - Scaffold & I2C**: Created `core/i2c.py` with thread-safe `threading.Lock`, exponential backoff retry (10→20→50ms), bus recovery, big-endian word handling. `registers.py` with ~60 semantic constants (22 tests).
    - **Phase 2 - Sensor Driver**: Created `core/sensor.py` with hardened init (firmware boot polling up to 1.0s), fixed V2 offset bug (raw_value now truly raw), defined exception contract (`I2CError`/`TimeoutError`/`RuntimeError`), async support, health check, reinitialize. `driver.py` backward-compat shim (22 tests).
    - **Phase 3 - Config Manager**: Created `config/config_manager.py` with load/save, export/import, corrupt JSON handling, project-relative default path (16 tests).
    - **Phase 4 - CLI Module**: Created `cli/sensor_tool.py` with 8 commands: `get`, `performance`, `calibrate`, `test`, `status`, `config show/export/import`. English output, lazy `pigpio` import.
    - **Phase 5 - Integration**: Verified backward compat with `ninja_core/hal.py` (`pi0vl53l0x.driver.VL53L0X`). Updated `README.md` with full docs.
- **Key Fixes**:
    - **V2 offset bug**: `get_data()` now stores true raw value before offset correction
    - **Reboot bug**: Firmware boot polling with configurable timeout prevents "returns 0"
    - **Thread safety**: All I2C access serialized via `threading.Lock`
- **Validation**: 60/60 tests pass, ruff lint clean.
- **Related Files**: `pi0vl53l0x/src/pi0vl53l0x/*`, `pi0vl53l0x/tests/*`, `pi0vl53l0x/README.md`.

## 2026-02-09: Movement Fluidity Enhancement ✓
- **Issue**: Multi-servo recorded movements feel mechanical with abrupt transitions.
- **Root Cause**: Each step uses `ease_in_out_cubic` independently, creating stop-start pattern.
- **Solution**: Position-aware transition easing:
    - Single step: `ease_in_out_cubic` (full curve)
    - First step: `ease_in_cubic` (accelerate only)
    - Middle steps: `linear` (constant velocity)
    - Last step: `ease_out_cubic` (decelerate to stop)
- **Modified Files**:
    - `ninja_core/src/ninja_core/movement_controller.py`

## 2026-02-09: Ninja Core Servo & Shutdown Fixes ✓
- **Issues Fixed**:
    1. Servo limpness during ninja_core server operation
    2. Missing wake-up behavior (servos not centering on user connect)
    3. Shutdown error traceback on Ctrl+C
- **Root Causes**:
    - `MovementController.move_servos()` didn't pass `force=True` to `move_all_sync()`
    - `trigger_welcome()` only played face/sound, no servo centering
    - `sigint_handler()` raised `KeyboardInterrupt` conflicting with uvloop
- **Fixes**:
    1. Added `force=True` to `move_all_sync()` in movement_controller.py
    2. Added servo centering in `trigger_welcome()` on user connection
    3. Added servo priming at server startup in `lifespan()`
    4. Replaced `raise KeyboardInterrupt` with `sys.exit(0)` for clean shutdown
- **Modified Files**:
    - `ninja_core/src/ninja_core/movement_controller.py`
    - `ninja_core/src/ninja_core/web_server.py`

## 2026-02-09: Servo Limpness Prevention ✓
- **Issue**: Servos occasionally become limp and unresponsive during movements.
- **Root Cause**: `move_all_sync()` skips PWM updates when `distance < 0.1°`, combined with stale `last_angle` tracking.
- **Solutions Implemented**:
    1. Added `refresh()` and `ensure_active()` methods to `Servo` class
    2. Added `force` flag to `move_all_sync()` to bypass skip-if-negligible logic
    3. Added skip logging for debugging (`logger.debug()`)
    4. Added `refresh_all()` and `ensure_all_active()` to `ServoGroup`
    5. Updated `servo_tool.py` to reuse persistent `ServoGroup`, preserving `last_angle` state
- **Modified Files**:
    - `pi0servo/src/pi0servo/core/servo.py`
    - `pi0servo/src/pi0servo/core/multi_servos.py`
    - `pi0servo/src/pi0servo/cli/servo_tool.py`
- **Tests**: All 82 unit tests passed
## 2026-02-09: Fix First-Run Servo Initialization ✓
- **Issue**: After Pi restart, servos didn't react on first CLI run; auto-center failed.
- **Root Cause**: `move_all_sync()` skips movement when `distance < 0.1`. On first run, `last_angle=None` and `get_pulse()=0`, so code falls back to `angle_center=0`. Since target is also 0, movement was skipped.
- **Fix**: Use `center_all()` (direct PWM) instead of `move_all_sync()` for startup centering.
- **Modified Files**:
    - `pi0servo/src/pi0servo/cli/servo_tool.py` - Replaced `move_all_sync()` with `center_all()`
    - `ninja_core/src/ninja_core/movement_cli.py` - Use direct `hal.servos.center_all()`

## 2026-02-09: Auto-Center Servos on CLI Start/Quit ✓
- **Action**: Added automatic servo centering (0°) when starting and quitting CLI tools.
- **Changes**:
    - On tool startup: all calibrated servos move to 0°
    - On tool exit: all servos center before shutdown
- **Modified Files**:
    - `pi0servo/src/pi0servo/cli/servo_tool.py`
    - `ninja_core/src/ninja_core/movement_cli.py`

## 2026-02-09: Servo Smoothness Optimization ✓
- **Action**: Reduced jittering by increasing update frequency and adding cubic easing.
- **Changes**:
    - Step interval: 20ms → 10ms (50Hz → 100Hz)
    - Added 3 cubic easing functions: `ease_in_cubic`, `ease_out_cubic`, `ease_in_out_cubic`
    - Default easing: `ease_in_out` → `ease_in_out_cubic`
- **Modified Files**:
    - `pi0servo/src/pi0servo/motion/easing.py`
    - `pi0servo/src/pi0servo/motion/__init__.py`
    - `pi0servo/src/pi0servo/core/multi_servos.py`
    - `ninja_core/src/ninja_core/movement_controller.py`

## 2026-02-09: Default Easing Changed to ease_in_out ✓
- **Action**: Changed default servo easing from `ease_out` to `ease_in_out`.
- **Reason**: Provides smoother motion at both start and end of movements.
- **Modified Files**:
    - `pi0servo/src/pi0servo/core/multi_servos.py` - All method defaults
    - `ninja_core/src/ninja_core/movement_controller.py` - `move_servos()` call

## 2026-02-08: Phase 12 - Documentation Update ✓
- **Action**: Updated all documentation for pi0servo V2 integration.
- **Changes**:
    - Deleted `pi0servo_bak` folder.
    - Updated `README.md` version to 5.2.1 in all language sections.
    - Updated `DevelopmentGuide.md` file structure (pi0servo now has cli, config, core, motion, parser folders).
    - Replaced Section 3.5 pi0servo API docs with new ServoGroup/ConfigManager/MotionPlanner API.
    - Updated `ninja_core/README.md` driver registry (ServoGroup instead of MultiServo).
- **Note**: `pi0servo/tests/` folder contains valid unit tests and was kept.

## 2026-02-08: Phase 11 - First Run Servo Issue ✓
- **Issue**: Servo 23 had no reaction on first movement-tool run after calibrating pin 23.
- **Root Cause**: After calibration, `config` was reloaded but HAL's `ServoGroup` kept old pin list. New pins (e.g., 23) not included until restart.
- **Solution**: After calibration, turn off old servos and reinitialize HAL with new config:
    - `hal.servos.off()` - release old PWM
    - `hal.config = config` - update config reference
    - `hal._init_servos()` - create new ServoGroup with all pins
- **Related Files**: `movement_cli.py`, `hal.py`.

## 2026-02-08: Phase 10 - Movement Tool Health Check ✓
- **Issue**: `edit_sequence_menu` threw `TypeError: dict - int` when editing/inserting steps.
- **Root Cause**: `parse_movement_command` returns `{pin: {"angle": X, "speed": Y}}`, but edit/insert stored this directly as `moves` instead of extracting angles.
- **Solution**:
    - Added `extract_movement_data()` helper to split parsed moves into `(angles_dict, per_servo_speeds_dict)`.
    - Fixed Edit Step, Insert Step to use helper and store separate `moves` and `per_servo_speeds`.
    - Fixed Preview to pass `per_servo_speeds` to `move_servos`.
- **Related Files**: `movement_cli.py`.

## 2026-02-08: Phase 9 - Fix Silent Failure ✓
- **Issue**: movement-tool showed no reaction when entering servo commands.
- **Root Cause**: `ServoArrayWrapper` was missing methods that `MovementController` calls:
    - `move_all_sync()` - per-servo speed movement
    - `pins` property - ordered GPIO pin list
    - `get_all_angles()` - current angle state
    - `move_all_angles()` - instant movement
- **Solution**: Added wrapper methods to `ServoArrayWrapper` that proxy to `_multi_servo`.
- **Related Files**: `api_wrappers.py`.

## 2026-02-08: Phase 8 - Per-Servo Speed Execution ✓
- **Action**: Refactored `MovementController` to use pi0servo's velocity-based motion.
- **Root Cause**: Old implementation used manual interpolation with single global duration.
- **Solution**:
    - `move_servos()` now calls `move_all_sync(speed_mode=list[str])` for per-servo speeds.
    - Each servo calculates its own duration: `distance / (speed_limit × mode_factor)`.
    - Faster servos reach target before slower ones within the same movement.
- **Flow**: Parser → Recording → Storage (`per_servo_speeds`) → Execution
- **Related Files**: `movement_controller.py`, `movement_cli.py`.

## 2026-02-08: Phase 7 Refinements - Speed & Parser ✓
- **Action**: Added speed field import and per-servo speed parsing.
- **Issue 1 - Speed not imported**:
    - `ServoCalibration` model now includes `speed: int = 80` field.
    - `import_and_update_config()` now maps `speed` from servo.json.
- **Issue 2 - Per-servo speed parsing**:
    - `parse_movement_command()` now parses suffixes: `22:45S`, `23:-30F`.
    - Returns `{pin: {"angle": value, "speed": str|None}}` format.
    - `record_new_movement()` stores `per_servo_speeds` in sequence.
- **Command Format** (matches pi0servo servo-tool):
    - Global: `F_22:45/23:-30` → All servos use Fast speed
    - Per-servo: `22:45S/23:-30F` → Pin 22 Slow, Pin 23 Fast
    - Mixed: `F_22:45/23:-30S` → Global Fast, but Pin 23 overrides to Slow
- **Related Files**: `ninja_core/config.py`, `ninja_core/movement_cli.py`.

## 2026-02-08: Fixed pi0servo Integration Issues ✓
- **Action**: Fixed config import compatibility between pi0servo and ninja_core.
- **Root Cause**: 
    - pi0servo saves `servo.json` as dict with `pulse_min/center/max` field names.
    - ninja_core `import_and_update_config()` only handled list format and used `min_pulse/center_pulse/max_pulse`.
- **Solution**: 
    - Updated `config.py` to handle both dict (pi0servo) and list (legacy) formats.
    - Added field name mapping: `pulse_min` → `min_pulse`, `pulse_center` → `center_pulse`, etc.
- **Commands Verified**:
    - `uv run ninja_core config import` ✓ (alias for import-all)
    - `uv run ninja_core config import-all` ✓
    - `uv run ninja_core movement-tool` ✓ (not `ninja-cli movement`)
- **Related Files**: `ninja_core/config.py`.

## 2026-02-08: pi0servo Integration Phase 3 & 4 ✓
- **Action**: Completed angle standardization and velocity-based movement.
- **Phase 3 - Angle Standardization (±90°)**:
    - Updated `api_wrappers.py`: ServoWrapper and ServoArrayWrapper now use ±90° directly.
    - Removed all 0-180 → ±90 conversions (breaking change for Blockly programs).
    - Center position now 0° (was 90° in old API).
- **Phase 4 - Movement-Tool Enhancement**:
    - Updated `movement_controller.py`: Replaced fixed `duration_map` with `calculate_duration()`.
    - Uses physics-based velocity calculation (SG90 spec: 600°/sec).
    - Duration now depends on actual travel distance and speed mode (F/M/S).
- **Verification**: Ruff lint passed for both files.
- **Related Files**: `ninja_core/api_wrappers.py`, `ninja_core/movement_controller.py`.

## 2026-02-08: pi0servo Integration into ninja_core - Phase 1 ✓
- **Action**: Integrated rebuilt `pi0servo` library into `ninja_core` HAL.
- **Breaking Changes**:
    - **DRIVER_REGISTRY**: Updated to point to `pi0servo.core.multi_servos.ServoGroup` (was `multi_servo.MultiServo`).
    - **HAL init**: Modified `_init_servos()` to use `ConfigManager` for pre-loading calibrations.
    - Calibrations now passed as `dict[int, ServoCalibration]` instead of `conf_file` path.
- **Legacy Compatibility**:
    - Added `move_all_angles()` method to `ServoGroup` for instant movement.
    - Added `get_all_angles()` method to `ServoGroup` for reading current state.
    - Added `servo` property to `ServoGroup` for list-style access.
    - Existing `move_all_angles_sync()` wrapper maintained for duration-based calls.
- **Verification**: Ruff lint passed for both `hal.py` and `multi_servos.py`.
- **Related Files**: `ninja_core/hal.py`, `pi0servo/core/multi_servos.py`.


## 2026-02-08: Fixed GPIO Initialization Error ✓
- **Action**: Fixed critical error `'GPIO is not in use for servo pulses'` that occurred after reboot.
- **Root Cause**: `get_servo_pulsewidth()` throws exception when GPIO has no PWM initialized (after reboot).
- **Solution**:
    - Wrapped `get_pulse()` in try/except to return 0 on pigpio error.
    - Changed default calibration to safe values (all pulses = 1500) to prevent unexpected servo movement.
    - Added `HARDWARE_PULSE_MIN/MAX` constants (500/2500) to `calib.py` for calibration TUI (separate from default calibration).
- **Documentation**:
    - Added calibration CAUTION warning to README Quick Start.
    - Clarified `uv sync` installation (no manual venv activation needed).
    - Added NOTE about default uncalibrated behavior in Configuration section.
- **Tests**: Added 2 new tests for exception handling, updated 6 tests for new defaults. **82/82 passed**.
- **Related Files**: `core/servo.py`, `cli/calib.py`, `README.md`, `tests/test_core.py`, `tests/test_config.py`.

## 2026-02-08: Per-Servo Speed Control Implemented ✓
- **Action**: Added support for individual servo speed overrides in `movement-tool` commands.
- **Details**:
    - **Parser**: Updated `parse_command` to detect speed suffixes (e.g., `45F`, `45S`).
    - **Logic**: Updated `move_all_sync/async` to apply per-servo duration scaling.
    - **Validation**: Enforced strict regex matching to prevent invalid command parsing.
- **Documentation**: Updated `README.md` with new command syntax and examples.
- **Verification**: Added unit tests for new parser features (27/27 passed).
- **Related Files**: `parser/command.py`, `core/multi_servos.py`, `README.md`.

## 2026-02-08: Servo-Tool Movement Control Fixes ✓
- **Action**: Fixed 3 user-reported issues from servo-tool testing.
- **Issue 1: Calibration Not Refreshing**:
    - Added `manager.load()` after `CalibApp.main()` returns in `servo_tool.py`.
    - New calibration values now apply immediately without restarting servo-tool.
- **Issue 2: Speed Control Not Working**:
    - Refactored `move_all_sync()` and `move_all_async()` to use **per-servo timing**.
    - Each servo now moves at its own calibrated speed (faster servos finish first).
    - Changed from step-based to time-based movement loop (`time.monotonic()`).
- **Issue 3: Continuous Input Mode**:
    - Rewrote `quick_move()` and `single_move()` with continuous input loops.
    - Users can enter multiple commands until pressing 'q' to return to menu.
- **Verification**: 74/74 tests passing, linter clean.
- **Related Files**: `servo_tool.py`, `multi_servos.py`.

## 2026-02-10: pi0servo Audit Issues Fixed ✓
- **Action**: Fixed all issues identified in the pi0servo code audit.
- **P0 Critical Bugs**:
    - Fixed `_configs` attribute errors in `config_cmd.py` and `servo_tool.py` (replaced with `get_all_calibrations()` method).
    - Added missing `_to_dict()`, `save_to()`, and `load_from()` methods to `ConfigManager`.
- **P1 Moderate Issues**:
    - Added `finally` block in `servo_tool.py` for proper `pi.stop()` cleanup.
    - Added division-by-zero guards in `servo.py` `angle_to_pulse()` and `pulse_to_angle()`.
    - Added pulse validation warning in `set_pulse()` for out-of-range values.
- **User-Reported Issues**:
    - Added **speed control** (`+`/`-` keys) to calibration TUI for adjusting per-servo speed limits.
    - Verified easing implementation is correct in `multi_servos.py` using `ease_out` by default.
    - Added **Set Speed menu option** to `servo-tool` (option 4) for dedicated speed limit setting.
- **Documentation**:
    - Completely rewrote `pi0servo/README.md` with `servo-tool` as primary interface.
    - Added detailed calibration guide with speed control, easing explanation, and command reference.
    - Added Python API section for setting speed limits programmatically.
- **Verification**: `uv run ruff check` passed for all source files.
- **Related Files**: `config_manager.py`, `config_cmd.py`, `servo_tool.py`, `calib.py`, `servo.py`, `README.md`.

## 2026-02-08: pi0servo V5 Refinement - Bugs Fixed ✓
- **Action**: Fixed 4 user-reported bugs + 4 audit gaps to complete the pi0servo library to 100%.
- **P0 Bug Fixes**:
    - **CLI `move` negative angles**: Changed angle type from `float` to `str` to prevent Click parsing `-90` as option flag.
    - **CLI `cmd` TypeError**: Fixed `config_path` invalid parameter by loading calibrations via `ConfigManager`.
    - **CLI `calib` not interactive**: Rewrote as full TUI using `blessed` library with keyboard navigation (Tab/Up/Down/Enter).
- **P1 Backward Compatibility**:
    - Added `MultiServo = ServoGroup` alias in `__init__.py` for ninja_core.
    - Added `move_all_angles_sync()` legacy wrapper method in `ServoGroup`.
- **P1 Documentation**:
    - Updated `pi0servo/README.md` with "calibration-first" Quick Start section.
- **Phase 2 Enhancements (Completed)**:
    - **Interactive Tool**: Added `servo-tool` CLI with menu for quick testing and calibration.
    - **Config Management**: Added `pi0servo config` command for export/import.
    - **Unit Tests**: Added comprehensive tests for `ConfigManager` (13 tests passing).
- **Linting**: Fixed 7 lint errors (unused imports, unsorted imports, f-string).
- **Related Files**: `cli/servo_tool.py`, `cli/config_cmd.py`, `tests/test_config.py`.

## 2026-02-07: pi0servo V5 Rebuild COMPLETE ✓
- **Action**: Completed full pi0servo library rebuild following `RebuildPlan.md`.
- **Details**:
    - **Phase 0 - Scaffold**: Created project structure, `pyproject.toml`, `conftest.py` with mock pigpio.
    - **Phase 1 - Motion**: Implemented easing functions (`linear`, `ease_out`, `ease_in`, `ease_in_out`) and velocity-based duration calculations (17 tests).
    - **Phase 2 - Parser**: Implemented command parsing for `[SPEED_]PIN:ANGLE[/PIN:ANGLE...]` format (21 tests).
    - **Phase 3 - Core**: Implemented `Servo` (single servo with calibration), `ServoGroup` (multi-servo with abort mechanism via `threading.Event` and `asyncio.Event`) (23 tests).
    - **Phase 4 - Config**: Implemented `ConfigManager` for JSON-based calibration persistence with `speed` field (13 tests).
    - **Phase 5 - CLI**: Implemented `cmd`, `move`, `calib`, `status` commands with Click framework.
    - **Phase 6 - Integration**: Finalized exports in `__init__.py`, all 74 tests passing.
- **Key Features**:
    - Non-blocking servo control with abort mechanism
    - Velocity-based movement duration calculation
    - Per-servo speed limits (0-100%)
    - Easing curves for smooth motion profiles
    - Unified command format compatible with movement-tool
    - Optional ninja_utils integration (fallback to standard logging)
- **Validation**: `uv run pytest tests/ -v` → 74 passed, `uv run python -m pi0servo --help` works.
- **Related Files**: `pi0servo/src/pi0servo/*`, `pi0servo/tests/*`, `pi0servo/RebuildPlan.md`.

## 2026-02-07: pi0servo Rebuild Phase 0 - Project Scaffold COMPLETE
- **Action**: Created new pi0servo project structure from scratch.
- **Details**:
    - Created directory structure: `src/pi0servo/{motion,parser,core,config,cli}`, `tests/`.
    - Created `pyproject.toml` with dependencies: pigpio, click, blessed, ninja_utils.
    - Created `LICENSE` (MIT), `README.md` with usage documentation.
    - Created `__init__.py` (v1.0.0) and `__main__.py` (Click CLI entry point).
    - Created `tests/conftest.py` with mock pigpio fixture for PC/Mac development.
    - All modules have placeholder `__init__.py` files.
- **Validation**: `uv sync` passed, import test (v1.0.0) passed, CLI help works, lint clean.
- **Related Files**: `pi0servo/pyproject.toml`, `pi0servo/src/pi0servo/*`, `pi0servo/tests/conftest.py`.

## 2026-02-07: pi0servo Documentation Modularization
- **Action**: Extracted `pi0servo` rebuild plan into a dedicated `RebuildPlan.md` file.
- **Details**:
    - Created `pi0servo/RebuildPlan.md` with the complete step-by-step implementation guide.
    - Added new sections for **abort mechanism** (`threading.Event` + `asyncio.Event`).
    - Added new sections for **native async support** (`move_to_async()`).
    - Updated `ProjectUpgradePlan.md` Appendix A to reference the new file.
    - Updated Appendix B with link to the new modular document.
- **Backup**: Old `pi0servo` folder renamed to `pi0servo_bak`.
- **Related Files**: `pi0servo/RebuildPlan.md`, `ProjectUpgradePlan.md`.


## 2026-01-25: Graceful Shutdown Animation
- **Action**: Implemented shutdown animation sequence for server termination.
- **Details**:
    - Created `_perform_shutdown_animation()` helper function in `web_server.py`.
    - Sequence: "sleepy" face + "sleepy" sound (parallel) → "Poweroff" pose (blocking).
    - Integrated with Ctrl+C handler (`emergency_cleanup`) for SIGINT shutdown.
    - Integrated with `/api/system/shutdown` endpoint for web interface poweroff.
    - All servo movements complete before system shutdown proceeds.
- **Verification**: `ruff check` passed.
- **Related Files**: `web_server.py`, `config.json` (Poweroff movement definition).

## 2026-01-09: Blockly Execution Flow & Agent Merger
- **Action**: Modified code execution to bypass `NinjaCoderAgent` and merged its capabilities into `NinjaAgent`.
- **Details**:
    - **Direct Execution**: `dispatcher.py` now executes code immediately via `SafeExecutor`.
    - **Parallel Explanation**: `dispatcher.py` triggers async `NinjaAgent.explain_code()` for instant feedback.
    - **Agent Merger**: Migrated `generate_code`, `analyze_error`, `analyze_code` to `NinjaAgent` using dynamic `temperature=0.1`.
    - **Cleanup**: Deleted `ninja_coder.py` and removed references in `web_server.py`.
- **Related Files**: `dispatcher.py`, `ninja_agent.py`, `web_server.py`, `ninja_coder.py` (deleted).

- **Action**: Updated `InstallationGuide.md` to include Node.js and ninja_webapp build instructions.
- **Details**:
    - Added **Step 4.6: Install Node.js** using NodeSource LTS.
    - Added **Step 6.4: Build the Web Interface** (`npm install && npm run build`).
    - Renumbered subsequent steps in all three language versions.
- **Affected Sections**: English, Japanese (日本語), Traditional Chinese (繁體中文).
- **Related Files**: `InstallationGuide.md`.

## 2026-01-08: Server Shutdown Hang Fix (V3)
- **Action**: Fixed server hanging on Ctrl+C during shutdown.
- **Details**:
    - **V1 (failed)**: Targeted `asyncio.gather()` with timeout—problem persisted.
    - **V2 (failed)**: Added `shutdown_event` for WebSocket handlers—lifespan shutdown ran TOO LATE (after connections closed).
    - **V3 (solution)**: Registered a custom SIGINT signal handler that runs BEFORE Uvicorn's. On Ctrl+C:
        1. `shutdown_event.set()` → WebSocket handlers exit loops
        2. `faces.stop()` → Animation thread stops
        3. `distance_monitor.stop_continuous()` → Sensor thread stops
        4. `hal.shutdown()` → Display turns off
        5. `ngrok.kill()` → Tunnel closes
        6. Uvicorn proceeds with normal shutdown
- **Verification**: `ruff check` passed.
- **Related Files**: `web_server.py`.

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
