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
| **pi0servo** | Servo motor control | 🔴 High | Plan Complete |
| **pi0vl53l0x** | Distance sensor | 🟡 Medium | Planned |
| **pi0disp** | Display rendering | 🟡 Medium | Planned |
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
│       ├── core/      # PiServo, CalibrableServo, MultiServo
│       ├── helper/    # ThreadMultiServo, ThreadWorker (UNUSED)
│       ├── utils/     # ServoConfigManager
│       └── command/   # CLI tools
│
├── pi0vl53l0x/        # Distance sensor driver (VL53L0X)
│   └── src/pi0vl53l0x/
│       ├── driver.py
│       ├── constants.py
│       └── config_manager.py
│
├── pi0disp/           # Display driver (ST7789V)
│   └── src/pi0disp/
│       ├── disp/      # Display controllers
│       ├── fonts/     # Font resources
│       ├── utils/     # Utilities
│       └── commands/  # CLI tools
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
    "servos": {"module": "pi0servo.core.multi_servo", "class": "MultiServo"},
    "distance": {"module": "pi0vl53l0x.driver", "class": "VL53L0XDriver"},
    "display": {"module": "pi0disp.disp.dispv3", "class": "DisplayDriverV3"},
    "buzzer": {"module": "pi0buzzer.driver", "class": "BuzzerDriver"},
}
```

---

## 4. pi0servo Library Rebuild (Detailed)

### 4.1 Vulnerability Analysis (Current Library)

#### 4.1.1 CRITICAL: Blocking `time.sleep()` in Sync Movement

| Severity | Location | Impact |
|----------|----------|--------|
| **CRITICAL** | `multi_servo.py:220-250` | Blocks entire application during servo movement |

**Problematic Code:**
```python
# Current: move_angle_sync()
for _step_i in range(1, step_n + 1):
    next_angles = [...]
    self.move_all_angles(next_angles)
    time.sleep(_step_sec)  # ⚠️ BLOCKING!
```

**Impact:** When a movement executes (e.g., 0.5 seconds), the entire FastAPI server is blocked. WebSocket updates stop, BLE commands queue up, and the robot becomes unresponsive.

#### 4.1.2 MEDIUM: No Speed/Duration in Actuator.execute()

The Actuator ABC `execute()` interface doesn't support duration or speed parameters:

```python
# Current limited interface
servo.execute({"angles": [0, 45, -30, 0, 0, 0, 0, 0]})
servo.execute({"angles": [...], "sync": True})  # Still blocking!
```

#### 4.1.3 MEDIUM: Duplicate Interpolation Logic

Interpolation code exists in two places:
- `MultiServo.move_angle_sync()` 
- `MovementController.move_servos()`

This creates inconsistency and maintenance burden.

#### 4.1.4 MEDIUM: No Easing Curves

Current implementation uses linear interpolation only. Professional robotics benefits from:
- `ease_out`: Start fast, end slow (most natural for servos)
- `ease_in_out`: Smooth acceleration and deceleration

#### 4.1.5 LOW: Mixed Angle Conventions

| Location | Convention | Range |
|----------|------------|-------|
| CalibrableServo | Centered | -90° to +90° |
| ServoArrayWrapper | Blockly | 0° to 180° |

Conversion happens in wrapper, creating cognitive overhead.

#### 4.1.6 LOW: Unused Code

The following files are NOT used by ninja_core:
- `helper/thread_multi_servo.py` (~140 lines)
- `helper/thread_worker.py` (~215 lines)

**Total: ~355 lines of dead code**

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
    │   └── group.py              # Multi-servo with sequence execution
    │
    ├── motion/
    │   ├── __init__.py
    │   ├── easing.py             # Interpolation curves
    │   └── calculator.py         # Duration/velocity calculations
    │
    ├── config/
    │   ├── __init__.py
    │   └── store.py              # Calibration persistence
    │
    ├── parser/
    │   ├── __init__.py
    │   └── command.py            # Movement-tool format parser
    │
    └── cli/
        ├── __init__.py
        ├── tool.py               # Interactive tool menu
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
uv run pi0servo tool
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
uv run pi0servo tool

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
from .core.group import ServoGroup

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
| `core/multi_servo.py` | ~320 | Replaced by `core/group.py` |
| `helper/thread_multi_servo.py` | ~140 | Unused by ninja_core |
| `helper/thread_worker.py` | ~215 | Unused by ninja_core |
| `utils/servo_config_manager.py` | ~100 | Replaced by `config/store.py` |
| **Total Deleted** | **~1215** | Lines of old/unused code |

---

## 5. pi0vl53l0x Library Upgrade (Planned)

### 5.1 Current Structure

```
pi0vl53l0x/src/pi0vl53l0x/
├── __init__.py
├── __main__.py
├── driver.py           # Main VL53L0X driver
├── constants.py        # Register constants
└── config_manager.py   # Configuration persistence
```

### 5.2 Identified Issues (Preliminary)

| Issue | Severity | Description |
|-------|----------|-------------|
| Callback handling | Medium | Distance callbacks may need refinement |
| Error recovery | Medium | I2C communication failures |
| Config management | Low | Consistency with other drivers |

### 5.3 Planned Improvements

- [ ] Unified API protocol matching pi0servo pattern
- [ ] Robust I2C error handling and recovery
- [ ] Continuous monitoring mode optimization
- [ ] CLI tool for standalone testing

> **Status:** Detailed analysis pending after pi0servo completion

---

## 6. pi0disp Library Upgrade (Planned)

### 6.1 Current Structure

```
pi0disp/src/pi0disp/
├── __init__.py
├── __main__.py
├── disp/               # Display controllers
├── fonts/              # Font resources
├── utils/              # Utilities
└── commands/           # CLI tools
```

### 6.2 Identified Issues (Preliminary)

| Issue | Severity | Description |
|-------|----------|-------------|
| Animation performance | Medium | Frame buffer management |
| Font rendering | Low | Unicode support |
| CLI consistency | Low | Match pi0servo pattern |

### 6.3 Planned Improvements

- [ ] Unified API protocol matching pi0servo pattern
- [ ] Optimized animation rendering
- [ ] Async-compatible display updates
- [ ] CLI tool enhancement

> **Status:** Detailed analysis pending after pi0servo completion

---

## 7. pi0buzzer Library Upgrade (Planned)

### 7.1 Current Structure

```
pi0buzzer/src/pi0buzzer/
├── __init__.py
├── __main__.py
└── driver.py           # Main buzzer driver
```

### 7.2 Identified Issues (Preliminary)

| Issue | Severity | Description |
|-------|----------|-------------|
| Sound queue | Low | Non-blocking sound playback |
| Melody support | Low | Pre-defined melodies |

### 7.3 Planned Improvements

- [ ] Unified API protocol matching pi0servo pattern
- [ ] Non-blocking sound playback
- [ ] CLI tool for standalone testing

> **Status:** Detailed analysis pending after pi0servo completion

---

## 8. Integration Strategy

### 8.1 ninja_core HAL Updates

After all driver upgrades, the HAL will remain unchanged:

```python
# ninja_core/hal.py (no changes needed)
DRIVER_REGISTRY = {
    "servos": {"module": "pi0servo", "class": "ServoGroup"},  # NEW alias works
    "distance": {"module": "pi0vl53l0x", "class": "VL53L0XDriver"},
    "display": {"module": "pi0disp", "class": "DisplayDriver"},
    "buzzer": {"module": "pi0buzzer", "class": "BuzzerDriver"},
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
   uv run pi0servo tool      # Test servo control
   uv run pi0vl53l0x test    # Test distance sensor
   uv run pi0disp test       # Test display
   uv run pi0buzzer test     # Test buzzer
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
| Phase 1 | pi0servo rebuild | 1-2 weeks | **Plan Complete** |
| Phase 2 | pi0servo verification | 1 week | Pending |
| Phase 3 | pi0vl53l0x analysis | 2-3 days | Pending |
| Phase 4 | pi0vl53l0x upgrade | 1 week | Pending |
| Phase 5 | pi0disp analysis | 2-3 days | Pending |
| Phase 6 | pi0disp upgrade | 1 week | Pending |
| Phase 7 | pi0buzzer analysis | 1-2 days | Pending |
| Phase 8 | pi0buzzer upgrade | 3-5 days | Pending |
| Phase 9 | Integration testing | 1 week | Pending |

---

## Appendix A: Related Documents

- [DevelopmentPlan.md](DevelopmentPlan.md) - Overall project roadmap
- [DevelopmentGuide.md](DevelopmentGuide.md) - API reference
- [README.md](README.md) - Project overview

---

**Document maintained by:** Development Team  
**Last updated:** 2026-02-06
