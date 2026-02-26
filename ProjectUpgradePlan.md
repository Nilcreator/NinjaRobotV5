# NinjaRobotV5 Project Upgrade Plan

**Document Version:** 1.0  
**Date Created:** 2026-02-06  
**Status:** Active Development  
**Project:** NinjaRobotV5 Driver Libraries Upgrade  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Upgrade Objectives](#2-upgrade-objectives)
3. [Current Driver Libraries Overview](#3-current-driver-libraries-overview)
4. [pi0servo Library Rebuild (Detailed)](#4-pi0servo-library-rebuild-detailed)
5. [pi0vl53l0x Library Upgrade (Planned)](#5-pi0vl53l0x-library-upgrade-planned)
6. [pi0disp Library Upgrade (Planned)](#6-pi0disp-library-upgrade-planned)
7. [pi0buzzer Library Upgrade (Planned)](#7-pi0buzzer-library-upgrade-planned)
8. [Integration Strategy](#8-integration-strategy)
9. [Testing & Verification](#9-testing--verification)
10. [Timeline & Milestones](#10-timeline--milestones)

---

## 1. Executive Summary

This document outlines the comprehensive plan for upgrading the NinjaRobotV5 hardware driver libraries to achieve:

- **More robust and reliable hardware control**
- **Unified API protocols** across all drivers
- **Seamless integration** with the ninja_core application
- **Independent operability** for standalone testing and development

### Libraries to Upgrade

| Library | Purpose | Priority | Status |
|---------|---------|----------|--------|
| **pi0servo** | Servo motor control | 🔴 High | ✅ Complete |
| **pi0vl53l0x** | Distance sensor | 🟡 Medium | ✅ Complete |
| **pi0disp** | Display rendering | 🟡 Medium | Plan Complete |
| **pi0buzzer** | Sound generation | 🟢 Low | Planned |

---

## 2. Upgrade Objectives

### 2.1 Primary Goals

1. **Eliminate Blocking Operations**
   - Replace all `time.sleep()` with abortable patterns
   - Enable responsive robot control during movements

2. **Unified API Protocol**
   - Same interface pattern for all drivers
   - Consistent parameter naming conventions
   - Both CLI and programmatic access

3. **Independent & Integrated Operation**
   - Each library works standalone with its own config
   - Seamless integration when used with ninja_core
   - Bi-directional config synchronization

4. **Velocity-Based Control (pi0servo)**
   - Replace duration-based timing with physics-based calculations
   - Per-servo speed limits for safety and precision

### 2.2 Design Principles

| Principle | Description |
|-----------|-------------|
| **Single Source of Truth** | All logic in core classes; CLI and ninja_core use the same methods |
| **Backward Compatibility** | 100% API compatibility with existing ninja_core integration |
| **Defensive Coding** | Handle hardware exceptions gracefully |
| **Asyncio-Ready** | Non-blocking designs compatible with asyncio event loop |

---

## 3. Current Driver Libraries Overview

### 3.1 Library Inventory

```
NinjaRobotV5/
├── pi0servo/          # Servo motor driver (8 channels)
│   └── src/pi0servo/
│       ├── core/      # Servo, MultiServo (ServoGroup)
│       ├── motion/    # Calculator, Easing
│       ├── config/    # ConfigManager
│       ├── parser/    # Command Parser
│       └── cli/       # CLI tools
│
├── pi0vl53l0x/        # Distance sensor driver (VL53L0X)
│   └── src/pi0vl53l0x/
│       ├── core/      # Sensor, I2C wrapper
│       ├── config/    # ConfigManager
│       ├── cli/       # Sensor Tool, CLI commands
│       └── driver.py  # Compatibility shim
│
├── pi0disp/           # Display driver (ST7789V) — V2 Rebuild
│   └── src/pi0disp/
│       ├── core/      # ST7789V driver + renderer
│       ├── effects/   # Text ticker
│       ├── config/    # ConfigManager
│       ├── cli/       # CLI commands
│       └── fonts/     # Multilingual fonts
│
└── pi0buzzer/         # Buzzer driver (PWM)
    └── src/pi0buzzer/
        └── driver.py
```

### 3.2 Integration Points (ninja_core)

All drivers integrate with ninja_core via the Hardware Abstraction Layer (HAL):

```python
# ninja_core/hal.py
DRIVER_REGISTRY = {
    "servos": {"module": "pi0servo.core.multi_servos", "class": "ServoGroup"},
    "distance_sensor": {"module": "pi0vl53l0x.driver", "class": "VL53L0X"},
    "display": {"module": "pi0disp.core.driver", "class": "ST7789V"},
    "buzzer": {"module": "pi0buzzer.driver", "class": "MusicBuzzer"},
}
```

---

## 4. pi0servo Library Rebuild (Detailed)

### 4.1 Vulnerability Analysis (Current Library)

> **Summary:** 10 vulnerabilities identified across 10 source files (~1,800 lines reviewed)

#### 4.1.1 CRITICAL: Blocking `time.sleep()` in Sync Movement

| Severity | Location | Impact |
|----------|----------|--------|
| **CRITICAL** | `multi_servo.py:220-250` | Blocks entire application during servo movement |

**Problematic Code:**
```python
# Current: move_all_angles_sync()
for _step_i in range(1, step_n + 1):
    next_angles = [...]
    self.move_all_angles(next_angles)
    time.sleep(_step_sec)  # ⚠️ BLOCKING!
```

**Impact:** When a movement executes (e.g., 0.5 seconds), the entire FastAPI server is blocked. WebSocket updates stop, BLE commands queue up, and the robot becomes unresponsive.

---

#### 4.1.2 MEDIUM: No Speed Parameter in Calibration Schema

| Severity | Location | Impact |
|----------|----------|--------|
| **MEDIUM** | `servo_config_manager.py`, `calibrable_servo.py` | Cannot limit per-servo velocity |

**Current JSON Schema:**
```json
{"pin": 20, "min": 500, "center": 1500, "max": 2500}
// Missing: "speed" field
```

**Impact:** All servos move at same speed. Some joints (e.g., head) need slower limits for safety.

---

#### 4.1.3 MEDIUM: No Abort Mechanism in Sync Movement

| Severity | Location | Impact |
|----------|----------|--------|
| **MEDIUM** | `multi_servo.py:move_all_angles_sync()` | Cannot stop mid-movement |

**Problematic Code:**
```python
def move_all_angles_sync(self, target_angles, move_sec=0.2, step_n=40):
    # No check_abort parameter!
    for _step_i in range(1, step_n + 1):
        # ...
        time.sleep(_step_sec)  # Cannot interrupt
```

**Impact:** Robot cannot respond to emergency stop commands during movement execution.

---

#### 4.1.4 MEDIUM: Duplicate Interpolation Logic

| Severity | Location | Impact |
|----------|----------|--------|
| **MEDIUM** | `multi_servo.py`, `movement_controller.py` | Inconsistent behavior, maintenance burden |

Interpolation code exists in two places:
- `MultiServo.move_all_angles_sync()` (in pi0servo)
- `MovementController.move_servos()` (in ninja_core)

**Impact:** Changes must be synchronized across libraries. Bugs may appear in one but not the other.

---

#### 4.1.5 MEDIUM: No Easing Curves

| Severity | Location | Impact |
|----------|----------|--------|
| **MEDIUM** | `multi_servo.py:move_all_angles_sync()` | Jerky, mechanical-looking movements |

Current implementation uses only linear interpolation.

---

#### 4.1.6 LOW: CWD-Only Config File Path

| Severity | Location | Impact |
|----------|----------|--------|
| **LOW** | `servo_config_manager.py:26` | Config file location not portable |

**Problematic Code:**
```python
self.conf_file = str(Path.cwd() / conf_file)  # Always CWD!
```

---

#### 4.1.7 LOW: Duplicate pigpio Initialization in CLI

| Severity | Location | Impact |
|----------|----------|--------|
| **LOW** | `__main__.py`, `cmd_servo.py`, `cmd_calib.py` | Resource waste, potential conflicts |

---

#### 4.1.8 LOW: No Progress Callback for Long Movements

| Severity | Location | Impact |
|----------|----------|--------|
| **LOW** | `multi_servo.py:move_all_angles_sync()` | No real-time feedback to UI |

---

#### 4.1.9 LOW: Mixed Angle Conventions

| Location | Convention | Range |
|----------|------------|-------|
| CalibrableServo | Centered | -90° to +90° |
| ServoArrayWrapper (Blockly) | Positive only | 0° to 180° |

---

#### 4.1.10 LOW: Unused ThreadMultiServo Code (~355 lines)

| File | Lines | Used By |
|------|-------|---------|
| `helper/thread_multi_servo.py` | ~140 | Nothing |
| `helper/thread_worker.py` | ~215 | Nothing |

---



### 4.2 New pi0servo Architecture

#### 4.2.1 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Physical Max Velocity | **600°/sec** | SG90 servo spec (0.10s/60°) |
| Default Easing | **ease_out** | Natural servo motion |
| Angle Convention | **-90° to +90°** | Consistent everywhere |
| Speed Control | **Velocity-based (0-100)** | Physics-based, per-servo limits |
| Config File | **Independent + sync** | Works standalone and integrated |

#### 4.2.2 New File Structure

```
pi0servo/
├── pyproject.toml
├── README.md
├── LICENSE
├── servo.json                    # Default calibration
│
└── src/pi0servo/
    ├── __init__.py               # Exports: Servo, ServoGroup, parse_command
    ├── __main__.py               # CLI entry point
    │
    ├── core/
    │   ├── __init__.py
    │   ├── servo.py              # Single servo class
    │   └── multi_servos.py       # Multi-servo with sequence execution
    │
    ├── motion/
    │   ├── __init__.py
    │   ├── easing.py             # Interpolation curves
    │   └── calculator.py         # Duration/velocity calculations
    │
    ├── config/
    │   ├── __init__.py
    │   └── config_manager.py     # Calibration persistence
    │
    ├── parser/
    │   ├── __init__.py
    │   └── command.py            # Movement-tool format parser
    │
    └── cli/
        ├── __init__.py
        ├── servo_tool.py         # Interactive tool menu
        ├── cmd.py                # Direct command execution
        ├── calib.py              # Calibration command
        ├── move.py               # Single servo movement
        ├── status.py             # Status display
        └── config_cmd.py         # Config management
```

#### 4.2.3 Unified Command Format

Uses the **same format as ninja_core's movement-tool**:

```
[SPEED_]PIN:ANGLE[/PIN:ANGLE...]
```

| Component | Description | Values |
|-----------|-------------|--------|
| `SPEED_` | Speed prefix (optional) | `S_`, `M_`, `F_` |
| `PIN` | GPIO pin number | 0-27 |
| `ANGLE` | Target angle | Number (-90 to 90) or keyword (X/M/C) |

**Speed Multipliers:**

| Prefix | Name | Multiplier | Effect with speed=80 |
|--------|------|------------|---------------------|
| `F_` | Fast | 100% | 80% of max velocity |
| `M_` | Medium | 75% | 60% of max velocity |
| `S_` | Slow | 50% | 40% of max velocity |

**Angle Keywords:**

| Keyword | Angle | Description |
|---------|-------|-------------|
| `X` | +90° | Maximum position |
| `M` | -90° | Minimum position |
| `C` | 0° | Center position |

**Examples:**
```bash
"17:30"           # Pin 17 to 30°, Medium speed
"F_17:30/27:M"    # Fast, Pin 17 to 30°, Pin 27 to -90°
"S_22:-45/23:C"   # Slow, Pin 22 to -45°, Pin 23 to center
```

---

### 4.3 CLI Commands

#### 4.3.1 Interactive Tool

```bash
uv run pi0servo servo-tool
```

**Menu Interface:**
```
╔══════════════════════════════════════════════════════════════╗
║               pi0servo Interactive Tool                       ║
╠══════════════════════════════════════════════════════════════╣
║  1. Quick Move      - Enter commands like '17:30/27:M'       ║
║  2. Calibrate       - Calibrate a servo (set min/center/max) ║
║  3. Set Speed       - Set speed limit for a servo (0-100)    ║
║  4. Test Sequence   - Create and run test movements          ║
║  5. Status          - Show all servo states                  ║
║  6. Config          - Export/import calibration              ║
║  7. Exit                                                      ║
╚══════════════════════════════════════════════════════════════╝
```

#### 4.3.2 Individual Commands

```bash
# Interactive tool
uv run pi0servo servo-tool

# Direct command (movement-tool format)
uv run pi0servo cmd "F_20:45/21:M"

# Calibration
uv run pi0servo calib <pin>
uv run pi0servo calib <pin> --speed 80

# Single servo movement
uv run pi0servo move <pin> <angle> -s F

# Status
uv run pi0servo status

# Config management
uv run pi0servo config show
uv run pi0servo config export <path>
uv run pi0servo config import <path>
```

---

### 4.4 Programmatic API

#### 4.4.1 Core Classes

```python
from pi0servo import Servo, ServoGroup

# Standalone mode
group = ServoGroup(
    pi=pigpio.pi(),
    pins=[20, 21, 22, 23, 24, 25, 26, 27]
)

# Integrated mode (config from ninja_core)
group = ServoGroup(
    pi=pigpio.pi(),
    pins=[20, 21, 22, 23, 24, 25, 26, 27],
    calibration={
        20: {"min": 500, "center": 1500, "max": 2500, "speed": 80},
        21: {"min": 550, "center": 1480, "max": 2450, "speed": 100},
    }
)
```

#### 4.4.2 Movement Methods

```python
# Single servo
servo = group.get_servo(pin=20)
servo.move_to(angle=45, speed_mode="F")

# Multi-servo (synchronized)
group.move_all(
    angles=[45, -30, 0, None, None, None, None, None],
    speed_mode="M",
    check_abort=lambda: False
)

# Using command string
group.execute_command("F_20:45/21:-30/22:C")

# Sequence execution
group.execute_sequence([
    {"angles": [45, -30, 0, 0, 0, 0, 0, 0], "speed_mode": "F"},
    {"angles": [0, 0, 45, -30, 0, 0, 0, 0], "speed_mode": "M"},
    {"angles": [0, 0, 0, 0, 0, 0, 0, 0], "speed_mode": "S"},
], check_abort=safety_check)
```

#### 4.4.3 Actuator ABC Interface (ninja_core compatibility)

```python
group.initialize()       # Center all servos
group.execute(command)   # Execute command dict
group.off()              # Turn off all servos
```

---

### 4.5 Motion Control Implementation

#### 4.5.1 Velocity Calculation

```python
PHYSICAL_MAX_VELOCITY = 600.0  # °/sec (SG90 spec)

FMS_MULTIPLIERS = {
    "F": 1.0,   # Fast = 100% of speed limit
    "M": 0.75,  # Medium = 75% of speed limit
    "S": 0.5    # Slow = 50% of speed limit
}

def calculate_duration(distance, speed_limit, speed_mode):
    fms_mult = FMS_MULTIPLIERS.get(speed_mode, 0.75)
    velocity = PHYSICAL_MAX_VELOCITY * (speed_limit / 100) * fms_mult
    return abs(distance) / velocity if velocity > 0 else 0
```

#### 4.5.2 Motion Completion Detection

**Blocking Execution (Default):**
```python
def move_to(self, angle, speed_mode="M"):
    duration = self._calculate_duration(angle, speed_mode)
    # Execute interpolated movement...
    return True  # Returns when complete
```

**State Polling (Optional):**
```python
servo.start_move(45)               # Non-blocking
while servo.is_moving():           # Poll state
    pass
servo.wait_until_complete()        # Or wait directly
```

---

### 4.6 Backward Compatibility

```python
# __init__.py
from .core.multi_servos import ServoGroup

# Backward compatibility alias
MultiServo = ServoGroup

# Legacy method support
class ServoGroup:
    def move_all_angles_sync(self, angles, move_sec=0.5, step_n=40):
        """Legacy wrapper for ninja_core compatibility."""
        if move_sec <= 0.2:
            speed_mode = "F"
        elif move_sec <= 0.5:
            speed_mode = "M"
        else:
            speed_mode = "S"
        return self.move_all_sync(angles, speed_mode=speed_mode)
```

---

### 4.7 Files to Delete

| File | Lines | Reason |
|------|-------|--------|
| `core/piservo.py` | ~170 | Replaced by `core/servo.py` |
| `core/calibrable_servo.py` | ~270 | Merged into `core/servo.py` |
| `core/multi_servo.py` | ~320 | Replaced by `core/multi_servos.py` |
| `helper/thread_multi_servo.py` | ~140 | Unused by ninja_core |
| `helper/thread_worker.py` | ~215 | Unused by ninja_core |
| `utils/servo_config_manager.py` | ~100 | Replaced by `config/config_manager.py` |
| **Total Deleted** | **~1215** | Lines of old/unused code |

---

## 5. pi0vl53l0x Library Upgrade (Full Rewrite)

> **Status:** Analysis Complete → Refined Plan Approved → Implementation In Progress  
> **Approach:** Full rewrite from scratch (previous code backed up to `pi0vl53l0x_bak/`)  
> **Detailed Plan:** [pi0vl53l0x/RebuildPlan.md](pi0vl53l0x/RebuildPlan.md)  
> **Last Refined:** 2026-02-15 (audit review — thread safety, exception contracts, ContinuousReader deferred)

### 5.1 Previous Structure (Backed Up)

```
pi0vl53l0x_bak/src/pi0vl53l0x/
├── __init__.py          # 3 lines — exports VL53L0X
├── __main__.py          # 184 lines — Click CLI
├── driver.py            # 677 lines — monolithic VL53L0X class
├── constants.py         # ~170 lines — ~160 magic VALUE_XX/REG_XX
└── config_manager.py    # 30 lines — JSON config to ~/vl53l0x.json
```

### 5.2 Identified Vulnerabilities

| ID | Severity | Issue | Impact |
|----|----------|-------|--------|
| V1 | 🔴 Critical | No I2C retry logic — also no thread safety | Single bus glitch crashes driver; concurrent access corrupts state |
| V2 | 🔴 Critical | `get_data()` offset bug — stores offset-corrected value as `raw_value` | `get_range()` subtracts offset, but `get_data()` saves that result as "raw" |
| V3 | 🔴 Critical | No firmware boot polling after soft reset | **Root cause of "returns 0 after reboot"** |
| V4 | 🔴 Critical | VHV config error silently swallowed | I2C voltage misconfiguration |
| V5 | 🟡 Medium | No measurement quality validation | Bad readings not detected |
| V6 | 🟡 Medium | Resource leak on init failure | I2C handle not closed |
| V7 | 🟡 Medium | `close()` doesn't stop sensor ranging | Stale state on reboot |
| V8 | 🟡 Medium | Race condition with pigpiod on boot | Init fails without retry |
| V9 | 🟢 Low | ~160 obfuscated constants | Impossible to maintain |
| V10 | 🟢 Low | Unnecessary numpy dependency | ~30MB on RPi Zero |
| V11 | 🟢 Low | Config in home dir `~/` | Not project-relative |
| V12 | 🟢 Low | Zero test files | No test coverage |

### 5.3 Root Cause Analysis: "Returns 0 After Reboot"

Six contributing root causes identified (see [RebuildPlan.md §1.3](pi0vl53l0x/RebuildPlan.md) for full details):

| RC# | Cause | Fix |
|-----|-------|-----|
| **RC#1** (Primary) | No firmware boot-ready polling after soft reset — only 10ms wait | Poll register 0x01 bit 0 (up to **1.0s**, configurable) |
| RC#2 | VHV config write error silently `pass`-ed | Retry 3× with backoff, fail loudly |
| RC#3 | Race with pigpiod startup, HAL gives up without retry | Check `pi.connected`, retry `initialize()` 3× |
| RC#4 | Stale `SYSRANGE_START` from previous session | Clear register + interrupts after reset |
| RC#5 | First measurement returns stale data | Flush with dummy measurement |
| RC#6 | `close()` never stops sensor ranging | Send STOP + clear before `i2c_close()` |

### 5.4 New Architecture

```
pi0vl53l0x/
├── src/pi0vl53l0x/
│   ├── __init__.py              # Exports: VL53L0X
│   ├── driver.py                # Backward-compat shim → core.sensor
│   ├── core/
│   │   ├── sensor.py            # VL53L0X class (Sensor ABC)
│   │   └── i2c.py               # I2C helper with retry, recovery & Lock
│   ├── registers.py             # Semantic register constants (~60)
│   ├── config/
│   │   └── config_manager.py    # Project-relative config (pi0servo pattern)
│   └── cli/
│       └── sensor_tool.py       # Interactive CLI tool
├── tests/
│   ├── test_i2c.py
│   ├── test_sensor.py
│   └── test_config.py
├── pyproject.toml               # pigpio as optional dep (RPi-only)
├── RebuildPlan.md
├── README.md
└── LICENSE
```

> **Note:** `ContinuousReader` (`core/continuous.py`) is **deferred** to a future Phase 6. The core driver and ninja_core integration come first.

### 5.5 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rewrite scope | Full rewrite from scratch | Too many critical bugs to patch |
| Config path | Project-relative `vl53l0x.json` | Matches pi0servo pattern |
| Async support | `get_range_async()` via `asyncio.to_thread()` | Non-blocking for event loop |
| Continuous monitoring | **Deferred** — ContinuousReader in future Phase 6 | Focus core driver first; perception.py already has its own thread |
| numpy dependency | Remove (use `statistics.mean()`) | Save ~30MB on RPi Zero |
| pigpio dependency | **Optional** (`[project.optional-dependencies].pi`) | Not installable on PC/Mac; RPi-only |
| I2C thread safety | `threading.Lock()` in `I2CBus` | `DistanceMonitor` + `reinitialize()` access from different threads |
| Init failure cleanup | `try/except/close` in `initialize()` | I2C handle must be released on mid-init failure |
| Firmware boot timeout | **1.0s** (configurable via `timeout_s` param) | 500ms may be too short for cold boot |
| Reboot fix | Firmware boot polling + VHV retry + stale flush | Addresses all 6 root causes |
| Runtime recovery | `health_check()` + `reinitialize()` | Recovery without rebooting |

### 5.6 Public API Overview

```python
class VL53L0X(Sensor):  # Sensor ABC from ninja_utils
    def __init__(self, pi, i2c_bus=1, i2c_address=0x29, ...): ...
    def initialize(self) -> None: ...       # Hardened 12-step init (with cleanup on failure)
    def get_data(self) -> dict: ...         # Fixed offset bug + quality validation
    def close(self) -> None: ...            # Proper shutdown (stop + close)
    def get_range(self) -> int: ...         # Single-shot, blocking
        # Raises: I2CError, TimeoutError, RuntimeError
    async def get_range_async(self) -> int: ...  # Non-blocking
    def health_check(self) -> bool: ...     # Quick sensor status
    def reinitialize(self) -> None: ...     # Runtime recovery
        # ⚠️ NOT thread-safe — stop ContinuousReader/DistanceMonitor first
    def calibrate(self, target_mm, samples) -> int: ...
```

> **Note:** `ContinuousReader` API is deferred to Phase 6.

### 5.7 Backward Compatibility

**Zero changes required in ninja_core.** All preserved:

| Import / Usage | Solution |
|----------------|----------|
| `from pi0vl53l0x.driver import VL53L0X` | `driver.py` shim: `from .core.sensor import VL53L0X` |
| `VL53L0X(pi=self.pi)` | Exact constructor signature preserved |
| `.get_range()` → int | Method preserved |
| `.get_data()` → dict | Method preserved (bug fixed) |
| `.close()` | Method preserved (enhanced) |

### 5.8 Implementation Phases

| Phase | Content | Key Deliverables |
|-------|---------|-------------------|
| 1 | Scaffold & I2C Module | `i2c.py` with retry **+ Lock**, `registers.py`, `test_i2c.py` |
| 2 | Core Sensor Driver | `sensor.py` with hardened init **+ cleanup**, `driver.py` shim, `test_sensor.py` |
| 3 | Config Manager | `config_manager.py`, `test_config.py` |
| 4 | CLI Module | `sensor_tool.py`, `__main__.py` |
| 5 | Integration & Documentation | Lint, verify ninja_core compat, update docs |
| 6 | *(Future)* ContinuousReader | `continuous.py`, `test_continuous.py` — **DEFERRED** |

> **Full implementation details with code snippets:** [pi0vl53l0x/RebuildPlan.md](pi0vl53l0x/RebuildPlan.md)

### 5.9 Testing Strategy

**Automated (PC/Mac):**
```bash
cd pi0vl53l0x && uv run pytest tests/ -v
```

**Manual Hardware (Raspberry Pi):**

| Test | Command | Pass Criteria |
|------|---------|---------------|
| Basic reading | `uv run pi0vl53l0x get --count 10` | Within ±20mm |
| **Reboot survival** | **Reboot → immediate `get`** | **No "returns 0"** |
| Performance | `uv run pi0vl53l0x performance --count 100` | ~30-40 Hz |
| Health check | `uv run pi0vl53l0x status` | Reports healthy |
| Integration | `uv run ninja_core server` | Live readings |

---

## 6. pi0disp Library Upgrade (Full Rewrite)

> **Status:** Analysis Complete → Refined Plan Approved → Ready for Implementation  
> **Approach:** Full rewrite from scratch (previous code backed up to `pi0disp_bak/`)  
> **Detailed Plan:** [pi0disp/RebuildPlan.md](pi0disp/RebuildPlan.md)  
> **Last Refined:** 2026-02-20 (comprehensive code review + user-approved design decisions)

### 6.1 Previous Structure (Backed Up)

```
pi0disp_bak/src/pi0disp/        ~1,800 lines total
├── __init__.py                  # Empty
├── __main__.py                  # Click CLI group
├── disp/
│   └── st7789v.py               # 312 lines — Core SPI driver (Actuator ABC)
├── utils/
│   ├── performance_core.py      # 446 lines — MemoryPool, LUT, RegionOptimizer, etc.
│   └── image_processor.py       # ~80 lines — Resize, gamma
├── commands/
│   ├── ball_anime.py            # 531 lines — Physics bouncing ball demo
│   └── image.py                 # ~50 lines — Image display + gamma cycling
└── fonts/                       # NotoSans (EN/JP/TC)
```

### 6.2 Identified Vulnerabilities

> **Summary:** 6 vulnerabilities identified across ~1,800 lines reviewed

| ID | Severity | Issue | Impact |
|----|----------|-------|--------|
| V1 | 🔴 Critical | **No thread safety — SPI race condition** | `AnimatedFaces` (background thread at ~60 FPS) and `web_server.py` (main thread) call `lcd.display()` concurrently with no locking. Interleaved `spi_write()` corrupts display data. |
| V2 | 🔴 Critical | Full-frame SPI bottleneck | `display()` always sends ~115 KB/frame regardless of change amount; blocks GIL, starves asyncio sensor polling |
| V3 | 🟡 Medium | GC stutter from PIL.Image instantiation | Every frame allocates+discards Image+ImageDraw objects; triggers garbage collection pauses |
| V4 | 🟡 Medium | No backlight brightness control | Backlight is digital ON/OFF only; no PWM brightness adjustment |
| V5 | 🟢 Low | Over-engineered utility layer (446 lines) | `MemoryPool`, `AdaptiveChunking` have marginal benefit; add complexity without measurable gain |
| V6 | 🟢 Low | No error recovery on SPI failure | Uncaught SPI errors crash the driver |

#### V1 Root Cause Analysis: SPI Race Condition

The display driver is accessed from **multiple threads** without synchronization:

```
┌─────────────────────┐     ┌──────────────────────┐
│ AnimatedFaces Thread │     │  Main / Asyncio      │
│ (60 FPS loop)        │     │                      │
│ lcd.display(face)  ──┤     ├── display.display(qr) │
│                      │     │   (web_server.py)     │
│                      │     ├── display.execute()   │
│                      │     │   (dispatcher.py)     │
└──────────┬───────────┘     └──────────┬────────────┘
           │                            │
           ▼    ⚠️ NO LOCK ⚠️           ▼
       ┌───────────────────────────────────┐
       │         SPI Bus (pigpio)          │
       │   pi.spi_write(handle, bytes)     │
       └───────────────────────────────────┘
```

**Fix:** `threading.Lock()` protecting all SPI read/write operations in the new driver.

### 6.3 New Architecture

```
pi0disp/
├── pyproject.toml
├── README.md
├── LICENSE
├── display.json                   # Default pin config (standalone)
├── RebuildPlan.md
│
├── src/pi0disp/
│   ├── __init__.py                # Exports: ST7789V, ConfigManager
│   ├── __main__.py                # CLI entry point (Click)
│   │
│   ├── core/
│   │   ├── driver.py              # ST7789V class (Actuator ABC, thread-safe SPI)
│   │   └── renderer.py            # ColorConverter (RGB565 LUT), RegionOptimizer
│   │
│   ├── effects/
│   │   └── text_ticker.py         # Scrolling text / marquee animation
│   │
│   ├── config/
│   │   └── config_manager.py      # Pin config persistence (display.json)
│   │
│   ├── cli/
│   │   ├── display_tool.py        # Interactive display tool (menu)
│   │   ├── init_cmd.py            # Init / first-time setup wizard
│   │   ├── image_cmd.py           # Image display command
│   │   ├── text_cmd.py            # Text display / scroll command
│   │   ├── demo_cmd.py            # Ball animation demo (from old ball_anime.py)
│   │   └── info_cmd.py            # Display status/config info
│   │
│   └── fonts/
│       ├── NotoSans-Regular.ttf        # Latin/English
│       ├── NotoSansJP-Regular.otf      # Japanese
│       └── NotoSansTC-Regular.otf      # Traditional Chinese
│
└── tests/
    ├── test_driver.py             # ST7789V unit tests (mock pigpio)
    ├── test_renderer.py           # ColorConverter, RegionOptimizer tests
    └── test_config.py             # ConfigManager tests
```

### 6.4 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| RGB565 conversion | numpy LUT (keep numpy) | 60 FPS facial animation performance |
| Thread safety | `threading.Lock()` in driver | SPI concurrent access from AnimatedFaces + web_server |
| Delta rendering | `PIL.ImageChops.difference()` + bbox | Reduce SPI traffic by ~90% for facial animations |
| Backlight | PWM brightness (0-100%) via pigpio | User-adjustable brightness |
| Fonts | Bundled multilingual (EN/JA/ZH-TW) | Standalone text display without external deps |
| Display support | ST7789V 2.8" (240×320) + Waveshare 2.0" (240×320) | Both displays use same resolution |
| pigpio | Optional dependency (RPi-only) | Not installable on PC/Mac |
| Config | Project-relative `display.json` | Matches pi0servo/pi0vl53l0x pattern |
| Ball demo | Retained as `uv run pi0disp demo` | Excellent visual hardware validation tool |

### 6.5 Smart Delta Rendering (Core Feature)

The centerpiece optimization. The new driver automatically caches the previous frame and calculates the minimal bounding box of changed pixels:

```python
def display(self, image: Image.Image) -> None:
    with self._spi_lock:  # Thread-safe
        if self._previous_image is None:
            self._write_full_frame(image)  # First frame
        else:
            diff = ImageChops.difference(self._previous_image, image)
            bbox = diff.getbbox()
            if bbox is None:
                return  # No changes — skip SPI entirely
            region = image.crop(bbox)
            self._write_partial_frame(region, *bbox)
        self._previous_image = image.copy()
```

**Expected performance improvement:**

| Scenario | Old (Full Frame) | New (Delta) | Reduction |
|----------|-------------------|-------------|----------|
| Idle face (blinking) | 115 KB/frame | ~5-10 KB/frame | **~90-95%** |
| Speaking (mouth) | 115 KB/frame | ~15-20 KB/frame | **~83%** |
| Full expression change | 115 KB/frame | 115 KB/frame | 0% |
| Static QR code | 115 KB/frame | 0 KB (skipped) | **100%** |

### 6.6 Public API Overview

```python
class ST7789V(Actuator):  # Actuator ABC from ninja_utils
    def __init__(self, pi=None, channel=0, dc_pin=14, rst_pin=15,
                 backlight_pin=16, speed_hz=32_000_000,
                 width=240, height=240, rotation=0): ...

    # --- Core Display Methods (thread-safe) ---
    def display(self, image: Image.Image) -> None: ...     # Smart delta rendering
    def display_region(self, image, x0, y0, x1, y1): ...   # Manual partial update
    def clear(self, color=(0,0,0)) -> None: ...             # Fill with solid color

    # --- Brightness Control ---
    def set_brightness(self, percent: int) -> None: ...     # PWM 0-100%

    # --- Configuration ---
    def set_rotation(self, rotation: int) -> None: ...      # 0/90/180/270
    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...

    # --- Power Management ---
    def sleep(self) -> None: ...
    def wake(self) -> None: ...
    def close(self) -> None: ...                            # Release SPI + GPIO
    def health_check(self) -> bool: ...

    # --- Actuator ABC Interface (ninja_core compat) ---
    def initialize(self) -> None: ...
    def execute(self, command: dict) -> None: ...
        # Keys: "image", "clear", "backlight", "brightness"
    def off(self) -> None: ...
```

### 6.7 Backward Compatibility

**One line change required in ninja_core.** All existing call patterns preserved:

| ninja_core Usage | Old API | New API | Status |
|------------------|---------|---------|--------|
| `hal.py` DRIVER_REGISTRY | `"pi0disp.disp.st7789v"` | `"pi0disp.core.driver"` | ⚠️ Update path |
| `hal.py` constructor | `ST7789V(pi, channel, dc_pin, rst_pin, backlight_pin)` | Same signature | ✅ Compatible |
| `facial_expressions.py` | `lcd.display(image)`, `lcd.width`, `lcd.height` | Same methods/properties | ✅ Compatible |
| `web_server.py` | `display.display(qr)` | Same method | ✅ Compatible |
| `dispatcher.py` | `display.execute({"image": img})` | Same + new keys | ✅ Compatible |
| `api_wrappers.py` | `execute({"image": img})`, `execute({"clear": True})` | Same methods | ✅ Compatible |
| `hal.py` shutdown | `display.off()`, `display.close()` | Same methods | ✅ Compatible |

### 6.8 CLI Commands

```bash
uv run pi0disp init                      # First-time setup (display module + pin config)
uv run pi0disp init --defaults           # Setup with all defaults (no prompts)
uv run pi0disp display-tool              # Interactive menu tool (includes Init)
uv run pi0disp image <path/to/image.png>  # Display an image
uv run pi0disp text "Hello!" --scroll --lang ja  # Text / marquee
uv run pi0disp clear                     # Clear display
uv run pi0disp demo --num-balls 5        # Ball animation demo
uv run pi0disp info                      # Driver state & config
uv run pi0disp brightness 50             # Set PWM brightness
uv run pi0disp config show               # Show configuration
uv run pi0disp config export <path>      # Export config
uv run pi0disp config import <path>      # Import config
```

### 6.9 Implementation Phases

| Phase | Content | Key Deliverables |
|-------|---------|-------------------|
| 1 | Scaffold & Renderer | `renderer.py` (ColorConverter, RegionOptimizer), `test_renderer.py` |
| 2 | Core Driver | `driver.py` (ST7789V with delta + Lock), `test_driver.py` |
| 3 | Config Manager + Init | `config_manager.py` with `init_config()`, display profile selection, `display.json`, `test_config.py` |
| 4 | Effects Module | `text_ticker.py`, bundled multilingual fonts |
| 5 | CLI Commands | `__main__.py`, `display_tool.py`, `init_cmd.py`, image/text/demo/info/brightness cmds |
| 6 | Hardware Validation | Test on both ST7789V 2.8" and Waveshare 2.0" (both 240×320), ninja_core integration |

> **Full implementation details with code snippets:** [pi0disp/RebuildPlan.md](pi0disp/RebuildPlan.md)

### 6.10 Testing Strategy

**Automated (PC/Mac):**
```bash
cd pi0disp && uv run pytest tests/ -v
```

**Manual Hardware (Raspberry Pi):**

| Test | Command | Pass Criteria |
|------|---------|---------------|
| **Init setup** | `uv run pi0disp init` | Prompts for display & pins, saves `display.json` |
| Image display | `uv run pi0disp image sample.jpg` | Correct colors, proper sizing |
| Ball demo | `uv run pi0disp demo --num-balls 5` | Smooth ~30 FPS animation |
| Text scroll | `uv run pi0disp text "ニンジャ" --scroll --lang ja` | Smooth scrolling |
| Brightness | `uv run pi0disp brightness 50` | Noticeably dimmer |
| Clear | `uv run pi0disp clear` | Screen turns black |
| Integration | `uv run ninja_core server` | Facial expressions at ~60 FPS |
| **Thread safety** | Run AnimatedFaces + send QR display simultaneously | **No SPI corruption** |

---

## 7. pi0buzzer Library Rebuild (Full Rewrite)

> **Status**: Analysis complete. Detailed plan approved — Ready for Implementation.  
> **Reference**: [pi0buzzer/RebuildPlan.md](pi0buzzer/RebuildPlan.md)  
> **Backup**: Original library preserved at `pi0buzzer_bak/`

### 7.1 Previous Structure

```
pi0buzzer_bak/src/pi0buzzer/
├── __init__.py
├── __main__.py          # CLI: init, beep, playmusic (90 lines)
└── driver.py            # Buzzer + MusicBuzzer (200 lines)
```

### 7.2 Audit Findings (12+ Issues)

| # | Severity | Issue | Impact |
|---|----------|-------|--------|
| C1 | 🔴 Critical | `play_music()` undefined | CLI `playmusic` crashes with `AttributeError` |
| C2 | 🔴 Critical | Blocking `time.sleep()` in `play_song()` | Freezes calling thread |
| C3 | 🔴 Critical | No queue-based pause support | Timing unpredictable |
| M1 | 🟡 Major | Duplicated note dictionaries | `driver.py` vs `robot_sound.py` — no single source of truth |
| M2 | 🟡 Major | No ConfigManager | Raw JSON, no validation |
| M3 | 🟡 Major | No unit tests | Zero coverage |
| M4 | 🟡 Major | No async interface | Incompatible with asyncio architecture |
| M5 | 🟡 Major | Hardcoded 50% duty cycle | No volume control |
| M6 | 🟡 Major | No `info`/`status` CLI | No hardware inspection |
| M7 | 🟡 Major | No interactive `buzzer-tool` | Missing TUI (unlike pi0disp, pi0vl53l0x) |
| m1 | 🟢 Minor | No frequency validation | Accepts any value |
| m2 | 🟢 Minor | No re-init guard | Double `initialize()` starts two workers |

### 7.3 New Architecture

```
pi0buzzer/src/pi0buzzer/
├── __init__.py              # Public exports
├── __main__.py              # CLI entry point (click group)
├── driver.py                # Compatibility shim (re-exports)
├── notes.py                 # Single source: NOTES, KEYBOARD_MAP, EMOTION_SOUNDS
├── core/
│   ├── driver.py            # Buzzer (Actuator ABC, queue worker, volume)
│   └── music.py             # MusicBuzzer (songs, emotions, play_music)
├── config/
│   └── config_manager.py    # BuzzerConfigManager (load/save/validate)
└── cli/
    └── buzzer_tool.py       # Interactive TUI (9-option menu)
```

### 7.4 Phased Implementation (8 Phases)

| Phase | Component | Key Deliverable |
|---|---|---|
| 1 | Scaffold | Directory structure, `pyproject.toml` |
| 2 | Core Driver | `Buzzer` with all critical fixes |
| 3 | Music Engine | `MusicBuzzer` + shared `notes.py` |
| 4 | Config Manager | JSON config management |
| 5 | CLI + Buzzer Tool | Commands + interactive TUI |
| 6 | Unit Tests | Tests with mocked pigpio |
| 7 | ninja_core Integration | `robot_sound.py` imports from `pi0buzzer.notes` |
| 8 | Documentation | README, DevelopmentLog |

> **Full details**: See [pi0buzzer/RebuildPlan.md](pi0buzzer/RebuildPlan.md)

---

## 8. Integration Strategy

### 8.1 ninja_core HAL Updates

After all driver upgrades, the HAL will use updated module paths:

```python
# ninja_core/hal.py (updated DRIVER_REGISTRY)
DRIVER_REGISTRY = {
    "servos": {"module": "pi0servo.core.multi_servos", "class": "ServoGroup"},
    "distance_sensor": {"module": "pi0vl53l0x.driver", "class": "VL53L0X"},
    "display": {"module": "pi0disp.core.driver", "class": "ST7789V"},
    "buzzer": {"module": "pi0buzzer.driver", "class": "MusicBuzzer"},
}
```

### 8.2 Config Synchronization

```
pi0servo/servo.json  <──────────────>  ninja_core/config.json
pi0vl53l0x/vl53l0x.json  <──────────>  ninja_core/config.json
pi0disp/display.json  <─────────────>  ninja_core/config.json
pi0buzzer/buzzer.json  <────────────>  ninja_core/config.json
```

Commands for synchronization:
```bash
# Import all driver configs into ninja_core
uv run ninja_core config import-all

# Export from ninja_core to driver configs
uv run ninja_core config export-all
```

---

## 9. Testing & Verification

### 9.1 Unit Tests

Each driver library will have pytest-based unit tests:

```bash
cd pi0servo && uv run pytest tests/ -v
cd pi0vl53l0x && uv run pytest tests/ -v
cd pi0disp && uv run pytest tests/ -v
cd pi0buzzer && uv run pytest tests/ -v
```

### 9.2 Integration Tests (Manual on Raspberry Pi)

1. **Standalone Testing:**
   ```bash
   uv run pi0servo servo-tool  # Test servo control
   uv run pi0vl53l0x test      # Test distance sensor
   uv run pi0disp test         # Test display
   uv run pi0buzzer test       # Test buzzer
   ```

2. **ninja_core Integration:**
   ```bash
   uv run ninja_core movement-tool  # Test servo via ninja_core
   uv run ninja_core chat           # Test full integration
   ```

### 9.3 Verification Checklist

- [ ] All drivers initialize without errors
- [ ] HAL loads all drivers successfully
- [ ] Servo movements are non-blocking
- [ ] Distance sensor readings are accurate
- [ ] Display animations are smooth
- [ ] Sound playback works correctly
- [ ] Config import/export works bidirectionally

---

## 10. Timeline & Milestones

| Phase | Library | Duration | Status |
|-------|---------|----------|--------|
| Phase 1 | pi0servo rebuild | 1-2 weeks | **✅ Complete** |
| Phase 2 | pi0servo verification | 1 week | **✅ Complete** |
| Phase 3 | pi0vl53l0x analysis | 2-3 days | **✅ Complete** |
| Phase 4 | pi0vl53l0x rebuild (full rewrite) | 1-2 weeks | **✅ Complete** |
| Phase 5 | pi0disp analysis & plan refinement | 2-3 days | **✅ Complete** |
| Phase 6 | pi0disp rebuild (full rewrite) | 1-2 weeks | Ready for Implementation |
| Phase 7 | pi0buzzer analysis | 1-2 days | **✅ Complete** |
| Phase 8 | pi0buzzer rebuild (full rewrite) | 3-5 days | Ready for Implementation |
| Phase 9 | Integration testing | 1 week | Pending |

---

## Appendix A: pi0servo Step-by-Step Implementation Guide

> **NOTE:** This appendix has been moved to a separate, modular document for easier maintenance.

**See:** [pi0servo/RebuildPlan.md](pi0servo/RebuildPlan.md)

The RebuildPlan.md contains:
- Two-stage development workflow (PC/Mac → Raspberry Pi)
- Abort mechanism design (with `threading.Event` and `asyncio.Event`)
- Native async support (`move_to_async()`)
- Detailed implementation phases with code snippets
- Verification commands and troubleshooting guide

---



## Appendix B: Related Documents

| Document | Purpose |
|----------|---------|
| [DevelopmentPlan.md](DevelopmentPlan.md) | Overall project roadmap |
| [DevelopmentGuide.md](DevelopmentGuide.md) | API reference |
| [README.md](README.md) | Project overview |
| [pi0servo/RebuildPlan.md](pi0servo/RebuildPlan.md) | Modular step-by-step pi0servo implementation guide |
| [pi0vl53l0x/RebuildPlan.md](pi0vl53l0x/RebuildPlan.md) | Complete pi0vl53l0x rebuild plan (analysis, root cause, architecture, phases) |
| [pi0disp/RebuildPlan.md](pi0disp/RebuildPlan.md) | Complete pi0disp rebuild plan (vulnerability analysis, smart delta rendering, multi-display support) |

---

## Appendix C: File Inventory

### C.1 Files to Create (New)

| Path | Purpose | Priority |
|------|---------|----------|
| `motion/__init__.py` | Motion module exports | High |
| `motion/easing.py` | Easing functions | High |
| `motion/calculator.py` | Duration/velocity calculations | High |
| `parser/__init__.py` | Parser module exports | High |
| `parser/command.py` | Movement-tool format parser | High |
| `core/servo.py` | New single servo class | High |
| `core/multi_servos.py` | New multi-servo class | High |
| `config/__init__.py` | Config module exports | High |
| `config/config_manager.py` | Calibration persistence | High |
| `cli/__init__.py` | CLI module exports | Medium |
| `cli/servo_tool.py` | Interactive menu | Medium |
| `cli/cmd.py` | Direct command execution | Medium |
| `cli/move.py` | Single servo movement | Medium |
| `cli/calib.py` | Calibration command | Medium |
| `cli/status.py` | Status display | Medium |
| `cli/config_cmd.py` | Config management | Medium |

### C.2 Files to Delete (After Migration)

| Path | Lines | Replaced By |
|------|-------|-------------|
| `core/piservo.py` | ~170 | `core/servo.py` |
| `core/calibrable_servo.py` | ~270 | `core/servo.py` |
| `core/multi_servo.py` | ~320 | `core/multi_servos.py` |
| `helper/thread_multi_servo.py` | ~140 | (unused) |
| `helper/thread_worker.py` | ~215 | (unused) |
| `utils/servo_config_manager.py` | ~100 | `config/config_manager.py` |

---

## Appendix D: Pi0servo Integration Evaluation Report

> **Date:** 2026-02-08  
> **Status:** Ready for Implementation

### D.1 Integration Summary

The new `pi0servo` library has been rebuilt with velocity-based control, abort mechanism, and per-servo speed limits. This appendix provides detailed integration guidance for connecting the new library to `ninja_core`.

#### D.1.1 API Compatibility Matrix

| ninja_core Usage | Old API | New API | Status |
|-----------------|---------|---------|--------|
| `hal.py:173` | `MultiServo(pi, pins, conf_file)` | `ServoGroup(pi, pins, calibrations)` | ⚠️ Breaking |
| `api_wrappers.py:173` | `move_all_angles_sync(angles, move_sec)` | `move_all_angles_sync(angles, move_sec)` | ✅ Compatible |
| `movement_controller.py:84` | `move_all_angles(angles)` | Need adapter | ⚠️ Breaking |
| `movement_controller.py:105` | `get_all_angles()` | Need adapter | ⚠️ Breaking |
| `dispatcher.py:159` | `execute(dict)` | `execute(str)` | ⚠️ Breaking |

### D.2 Breaking Changes & Solutions

#### D.2.1 Constructor Signature Change

**Old API:**
```python
# hal.py:173 (current)
MultiServo = load_driver_class("servos")
self.servos = MultiServo(
    pi=self.pi,
    pins=pin_list,
    conf_file="servo.json",  # ❌ Not supported in new API
)
```

**New API:**
```python
# hal.py (updated)
from pi0servo import ConfigManager, ServoGroup

# Pre-load calibrations
config_mgr = ConfigManager("servo.json")
config_mgr.load()

calibrations = {}
for pin in pin_list:
    calibrations[pin] = config_mgr.get_calibration(pin)

ServoGroup = load_driver_class("servos")
self.servos = ServoGroup(
    pi=self.pi,
    pins=pin_list,
    calibrations=calibrations,  # ✅ New format
)
```

#### D.2.2 DRIVER_REGISTRY Update

**Current:**
```python
DRIVER_REGISTRY = {
    "servos": {
        "module": "pi0servo.core.multi_servo",   # ❌ Old module
        "class": "MultiServo",
    },
}
```

**Updated:**
```python
DRIVER_REGISTRY = {
    "servos": {
        "module": "pi0servo.core.multi_servos",  # ✅ Note: plural
        "class": "ServoGroup",                   # ✅ New class name
    },
}
```

#### D.2.3 Missing Legacy Methods (Add to ServoGroup)

```python
# Add to pi0servo/src/pi0servo/core/multi_servos.py

def move_all_angles(self, target_angles: list[float | None]):
    """Legacy compatibility: instant movement (no interpolation)."""
    for i, pin in enumerate(self._pins):
        if i < len(target_angles) and target_angles[i] is not None:
            self._servos[pin].set_angle(target_angles[i])

def get_all_angles(self) -> list[float]:
    """Legacy compatibility: get all angles as ordered list."""
    return [self._servos[pin].last_angle or 0.0 for pin in self._pins]

@property
def servo(self) -> list:
    """Legacy compatibility: list access (ordered by pin)."""
    return [self._servos[pin] for pin in self._pins]
```

### D.3 Angle Standardization (±90°)

**Decision:** Standardize on ±90° range across the entire project.

#### D.3.1 Current State

| Component | Range | Conversion |
|-----------|-------|------------|
| Blockly IDE (Web) | 0-180° | None |
| `api_wrappers.py` `ServoWrapper` | 0-180° → ±90° | `angle - 90` |
| `movement_cli.py` | ±90° | None |
| `pi0servo` | ±90° | None |

#### D.3.2 api_wrappers.py Update

```diff
class ServoWrapper:
-    """Blockly uses 0-180 degree range."""
+    """Direct ±90° angle control."""

    @angle.setter
    def angle(self, value):
-        # Clamp to valid range
-        value = max(0, min(180, value))
-        internal_angle = value - 90
+        # Clamp to ±90° range (no conversion)
+        value = max(-90, min(90, value))
+        internal_angle = value
```

#### D.3.3 Blockly Web Platform Update

Update block definitions:
- Slider: `[-90, 90]` instead of `[0, 180]`
- Default: `0` instead of `90`
- Label: `"angle (±90°)"`

### D.4 Movement-Tool Enhancement

**Goal:** Integrate pi0servo's velocity-based speed mode into `ninja_core`.

#### D.4.1 Feature Comparison

| Feature | Current `movement_cli.py` | New `pi0servo` |
|---------|---------------------------|----------------|
| Speed control | Fixed duration (S=1.0s, M=0.5s, F=0.2s) | Velocity-based (600°/s max) |
| Per-servo speed | ❌ | ✅ `20:45S/21:-30F` |
| Easing | ❌ | ✅ ease_out, linear |
| Command format | `S_17:30/27:M` | `F_20:45/21:-30` |

#### D.4.2 Parser Integration

```python
# movement_cli.py (updated)
from pi0servo import parse_command, calculate_duration

def parse_movement_command(command_str: str, definitions: dict):
    """Use pi0servo parser for consistent command handling."""
    try:
        parsed = parse_command(command_str)
        movements = {}
        for target in parsed.targets:
            if target.angle is not None:
                movements[target.pin] = target.angle
            elif target.special:
                movements[target.pin] = {"C": 0, "M": -90, "X": 90}[target.special]
        return parsed.speed_mode, movements
    except ValueError as e:
        print(f"Error: {e}")
        return None, None
```

#### D.4.3 Velocity-Based Duration

```python
# movement_controller.py (updated)
from pi0servo.motion import calculate_duration

def move_servos(self, movements: dict[int, float], speed: str = "M", ...):
    current_angles = self.get_current_angles()
    
    # Calculate duration based on max travel distance
    max_distance = max(
        abs(movements.get(pin, current) - current)
        for pin, current in current_angles.items()
        if pin in movements
    )
    
    # Physics-based duration (80% speed limit, selected mode)
    duration = calculate_duration(max_distance, 80, speed)
    
    # ... rest of movement logic
```

### D.5 Implementation Phases

| Phase | Description | Effort | Priority |
|-------|-------------|--------|----------|
| 1 | Update DRIVER_REGISTRY & HAL init | 1h | 🔴 High |
| 2 | Add legacy compatibility methods | 30m | 🔴 High |
| 3 | Angle standardization (±90°) | 2h | 🟡 Medium |
| 4 | Movement-tool enhancement | 2h | 🟡 Medium |
| 5 | Verification & testing | 1h | 🔴 High |

**Total Estimated Effort:** ~7 hours

### D.6 Verification Checklist

- [ ] `uv sync` completes without errors
- [ ] `uv run ninja_core` starts without import errors
- [ ] Servo calibration loads via `ConfigManager`
- [ ] `robot.servo[0].angle = 45` works (±90° range)
- [ ] Movement-tool uses velocity-based duration
- [ ] Command `F_20:45/21:-30` executes correctly
- [ ] Per-servo speed suffix `20:45S/21:-30F` works
- [ ] Abort mechanism interrupts movement
- [ ] Blockly IDE uses ±90° range

### D.7 Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|------------|
| Default calibration (1500/1500/1500) breaks movement | High | Document calibration requirement |
| Existing Blockly programs incompatible | Medium | Provide migration guide |
| Speed mode differs from expected | Low | Tune `FMS_MULTIPLIERS` |

---

**Document maintained by:** Development Team  
**Last updated:** 2026-02-20
