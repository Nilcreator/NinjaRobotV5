# NinjaRobot V5 Development Guide

**Version:** 5.2.5  
**Last Updated:** 2026-04-21  
**Target Audience:** Experienced Developers

This guide provides a comprehensive technical reference for the NinjaRobot V5 project. It serves as the source of truth for understanding the project architecture, library APIs, and development workflows.

---

## V5 Changes Summary

> [!IMPORTANT]
> V5 introduces a modular, plugin-based architecture with dual connectivity (BLE + Web).

### Key Changes (Phase 1 - Modularity):
| Component | Change |
|---|---|
| `ninja_utils` | Added `Sensor`, `Actuator` ABCs and `DistanceData` dataclass |
| `pi0buzzer` | **Non-blocking** threaded sound queue, implements `Actuator` |
| `pi0vl53l0x` | **REBUILT** — Thread-safe I2C, hardened init, retry with bus recovery, V2 offset fix |
| `pi0disp` | **REBUILT** — Thread-safe SPI, delta rendering, PWM brightness, ConfigManager, CLI |
| `pi0servo` | Added `execute()` for batch control, implements `Actuator` |
| `ninja_core/hal.py` | **Dynamic driver loading** via `importlib` |

### Key Changes (Phase 2 - Dual Connectivity):
| Component | Change |
|---|---|
| `ninja_ble` | **NEW** - BLE GATT server for wireless control |
| `ninja_core/dispatcher.py` | **NEW** - Central command router for BLE/Web |
| `ninja_core/web_server.py` | Integrated Dispatcher, launches BLE on startup |

### Key Changes (Phase 4 - Agent Intelligence):
| Component | Change |
|---|---|
| `ninja_core/safe_executor.py` | **NEW** - Sandboxed Python execution engine |

| `ninja_core/web_server.py` | Added `/api/code/*` endpoints for remote execution |

### Key Changes (Phase 5 - Web Interface):
| Component | Change |
|---|---|
| `ninja_webapp/` | **NEW** - React SPA (Vite + React 18 + react-router-dom) |
| `ninja_webapp/src/pages/Agent/` | Chat dialog, hardware controls, slidable log panel |
| `ninja_webapp/src/pages/Home/` | Hero image, power-off slider |
| `ninja_core/web_server.py` | SPA serving from `ninja_webapp/dist`, `/api/system/shutdown` |

### Key Changes (V5.2 - Graceful Shutdown):
| Component | Change |
|---|---|
| `ninja_core/web_server.py` | **NEW** - `_perform_shutdown_animation()` helper for graceful shutdown |
| Shutdown Sequence | "sleepy" face + sound (parallel) → "Poweroff" pose (blocking) → HAL cleanup |
| Ctrl+C Handler | Modified `emergency_cleanup()` to include shutdown animation |
| `/api/system/shutdown` | Now performs animation before system poweroff |

### Key Changes (V5.2.1 - pi0servo Integration):
| Component | Change |
|---|---|
| `pi0servo` | **REBUILT** - Velocity-based control, abort mechanism, easing curves |
| `pi0servo/ServoGroup` | Added legacy compatibility: `move_all_angles()`, `get_all_angles()`, `servo` property |
| `ninja_core/hal.py` | Updated `DRIVER_REGISTRY` to use `ServoGroup`, `ConfigManager` for calibrations |
| HAL init | Calibrations now passed as `dict[int, ServoCalibration]` instead of `conf_file` |

### Key Changes (V5.2.2 - Movement Fluidity):
| Component | Change |
|---|---|
| `movement_controller.py` | **Position-aware easing** for smooth multi-step sequences |
| Transition Logic | First step: `ease_in_cubic`, Middle: `linear`, Last: `ease_out_cubic` |
| Result | Eliminates stop-start pattern, creates fluid momentum-preserving motion |

### Key Changes (V5.2.3 - pi0vl53l0x V2):
| Component | Change |
|---|---|
| `pi0vl53l0x` | **REBUILT** — Full rewrite with modular architecture |
| `core/i2c.py` | Thread-safe I2C with `threading.Lock`, retry + bus recovery |
| `core/sensor.py` | Hardened init (firmware boot polling), V2 offset bug fix, health check |
| `config/config_manager.py` | JSON-based config with export/import, `ConfigManager` class |
| `cli/sensor_tool.py` | Interactive CLI: `get`, `performance`, `calibrate`, `test`, `status`, `config` |

### Key Changes (V5.2.4 - pi0disp V2):
| Component | Change |
|---|---|
| `pi0disp` | **REBUILT** — Full rewrite with modular architecture |
| `core/driver.py` | Thread-safe SPI (`threading.Lock`), smart delta rendering, PWM brightness |
| `core/renderer.py` | `ColorConverter` (numpy LUT RGB→RGB565), `RegionOptimizer` |
| `config/config_manager.py` | `display.json` config with setup wizard, CRUD, export/import |
| `effects/text_ticker.py` | Scrolling marquee with multilingual fonts (EN/JA/ZH-TW) |
| CLI | 11 commands + `display-tool` interactive menu |
| `ninja_core/hal.py` | Updated `DRIVER_REGISTRY` to `pi0disp.core.driver.ST7789V` |

### Key Changes (V5.2.5 - Blockly Runtime Reliability):
| Component | Change |
|---|---|
| `ninja_core/dispatcher.py` | Preserves the active execution request when duplicate `execute` commands are rejected |
| `ninja_core/dispatcher.py` | Broadcasts full execution log lines without transport-era truncation |
| `ninja_core/dispatcher.py` | Broadcasts structured Blockly syntax errors without reporting a false execution start |
| `ninja_core/safe_executor.py` | Compiles user code before starting the execution thread and keeps syntax failures from triggering hardware stop cleanup |
| `ninja_core/contracts.py` | Allows error events to carry structured `details` such as line, offset, and source text |
| `ninja_ble` | BLE transport v2 remains the required path for large Blockly payloads and large runtime feedback |
| Runtime contract | `execute`, `stop`, `execution_status`, `execution_log`, `chat`, and `error` stay correlated by `request_id` |

### Required Setup:
```bash
uv run pi0buzzer init 17
uv run pi0disp init              # First-time display setup
uv run pi0servo calib 20  # Repeat for each servo
uv run ninja_core config import
```

---

## Table of Contents

1. [Project Architecture](#1-project-architecture)
2. [Development Environment Setup](#2-development-environment-setup)
3. [Library Reference](#3-library-reference)
   - [3.1 ninja_utils](#31-ninja_utils)
   - [3.2 pi0buzzer](#32-pi0buzzer)
   - [3.3 pi0vl53l0x](#33-pi0vl53l0x)
   - [3.4 pi0disp](#34-pi0disp)
   - [3.5 pi0servo](#35-pi0servo)
   - [3.6 ninja_core](#36-ninja_core)
   - [3.7 ninja_ble](#37-ninja_ble)
4. [Configuration System](#4-configuration-system)
5. [Testing & Debugging](#5-testing--debugging)
6. [Contributing Guidelines](#6-contributing-guidelines)
7. [UI/UX Design Guidelines](#7-uiux-design-guidelines)

---

## 1. Project Architecture

### 1.1 Overall Structure

NinjaRobot V5 follows a **layered monorepo architecture** with 7 independent Python packages:

```
NinjaRobotV5/
├── pyproject.toml              # Root project configuration (unified install)
├── config.json                 # Runtime configuration (generated)
├── servo.json                  # Servo calibration data (generated)
├── buzzer.json                 # Buzzer configuration (generated)
├── LICENSE                     # MIT License
├── README.md                   # Project introduction
├── InstallationGuide.md        # End-user installation guide
├── DevelopmentGuide.md         # This document
├── DevelopmentPlan.md          # V5 roadmap and architecture
├── DevelopmentLog.md           # Development history
│
├── ninja_utils/                # Shared utilities library
│   ├── pyproject.toml
│   ├── README.md
│   └── src/ninja_utils/
│       ├── __init__.py
│       ├── my_logger.py        # Centralized logging
│       ├── keyboard.py         # Non-blocking keyboard input
│       └── interfaces.py       # Sensor/Actuator ABCs (V5)
│
├── ninja_ble/                  # BLE control library (V5 Phase 2)
│   ├── pyproject.toml
│   ├── README.md
│   └── src/ninja_ble/
│       ├── __init__.py
│       ├── service.py          # GATT server (bless)
│       └── chunking.py         # BLE payload chunking
│
├── ninja_webapp/               # React Web Application (V5 Phase 5)
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── public/
│   │   ├── logo.png
│   │   └── robot-hero.png
│   └── src/
│       ├── main.jsx            # React entry point
│       ├── App.jsx             # Router configuration
│       ├── index.css           # Global styles
│       ├── i18n.js             # i18next configuration
│       ├── components/
│       │   ├── layout/         # Header, Footer, Layout
│       │   └── common/         # Button, IconButton, PowerOffSlider
│       ├── pages/
│       │   ├── Home/           # Hero + Power-off slider
│       │   ├── Agent/          # Chat + Hardware controls
│       │   └── Help/           # Documentation
│       └── locales/            # en.json, ja.json, zh-tw.json, zh-cn.json
│
├── pi0buzzer/                  # Buzzer control library (V1.0.0 REBUILT)
│   ├── pyproject.toml
│   ├── README.md
│   ├── tests/                  # Unit tests (pytest, 61 tests)
│   └── src/pi0buzzer/
│       ├── __init__.py         # Exports Buzzer, MusicBuzzer
│       ├── __main__.py         # CLI entry point (click group)
│       ├── driver.py           # Backward-compat shim (re-exports from core/)
│       ├── notes.py            # Single source: NOTES, EMOTION_SOUNDS, KEYBOARD_MAP
│       ├── core/               # Core driver modules
│       │   ├── driver.py       # Buzzer (Actuator ABC, non-blocking worker)
│       │   └── music.py        # MusicBuzzer (songs, emotions, piano)
│       ├── config/             # Configuration management
│       │   └── config_manager.py  # BuzzerConfigManager (JSON)
│       └── cli/                # CLI commands + interactive tool
│           └── buzzer_tool.py  # Interactive TUI (9-option menu)
│
├── pi0vl53l0x/                 # VL53L0X distance sensor library (V5.2.3 REBUILT)
│   ├── pyproject.toml
│   ├── README.md
│   ├── tests/                  # Unit tests (pytest, 60 tests)
│   └── src/pi0vl53l0x/
│       ├── __init__.py         # Exports VL53L0X, ConfigManager
│       ├── __main__.py         # CLI entry point
│       ├── registers.py        # ~60 semantic register constants
│       ├── driver.py           # Backward-compat shim (re-exports VL53L0X)
│       ├── core/               # Core sensor modules
│       │   ├── i2c.py          # Thread-safe I2C bus wrapper
│       │   └── sensor.py       # VL53L0X driver (Sensor ABC)
│       ├── config/             # Configuration management
│       │   └── config_manager.py  # JSON config load/save/export/import
│       └── cli/                # CLI commands
│           └── sensor_tool.py  # Click CLI (8 commands)
│
├── pi0disp/                    # ST7789V display library (V5.2.4 REBUILT)
│   ├── pyproject.toml
│   ├── README.md
│   ├── tests/                  # Unit tests (pytest, 54 tests)
│   └── src/pi0disp/
│       ├── __init__.py         # Exports ST7789V, ConfigManager, TextTicker
│       ├── __main__.py         # CLI entry point (click)
│       ├── core/               # Core driver modules
│       │   ├── driver.py       # ST7789V driver (Actuator ABC)
│       │   └── renderer.py     # ColorConverter (numpy LUT), RegionOptimizer
│       ├── config/             # Configuration management
│       │   └── config_manager.py  # JSON config load/save/export/import
│       ├── effects/            # Visual effects
│       │   └── text_ticker.py  # Scrolling marquee animation
│       ├── fonts/              # Bundled Noto fonts (EN/JA/ZH-TW)
│       └── cli/                # CLI commands (11 commands + display-tool)
│
├── pi0servo/                   # Servo motor control library (V5.2.1 REBUILT)
│   ├── pyproject.toml
│   ├── README.md
│   ├── tests/                  # Unit tests (pytest)
│   └── src/pi0servo/
│       ├── __init__.py         # Exports ServoGroup, ConfigManager, CommandParser
│       ├── __main__.py         # CLI entry point
│       ├── cli/                # CLI commands (servo-tool, calib, config, etc.)
│       ├── config/             # ConfigManager, ServoCalibration dataclass
│       ├── core/               # SingleServo, ServoGroup (main classes)
│       ├── motion/             # MotionPlanner, easing functions, velocity control
│       └── parser/             # CommandParser for "F_20:45/21:-30" syntax
│
└── ninja_core/                 # Main application
    ├── pyproject.toml
    ├── README.md
    └── src/ninja_core/
        ├── __init__.py
        ├── __main__.py         # CLI entry point
        ├── config.py           # Centralized configuration
        ├── hal.py              # Hardware Abstraction Layer (dynamic loading)
        ├── dispatcher.py       # Command router (V5 Phase 2)
        ├── ninja_agent.py      # AI agent (Gemini)
        ├── movement_controller.py  # Motion system
        ├── movement_cli.py     # Movement recording tool
        ├── facial_expressions.py   # Visual emotions
        ├── robot_sound.py      # Auditory feedback
        ├── perception.py       # Distance monitoring
        ├── safe_executor.py    # Sandboxed execution (V5 Phase 4)

        ├── web_server.py       # FastAPI server (BLE + Web)
        ├── static/             # Web UI assets
        └── templates/          # HTML templates
```

### 1.2 Design Principles

1. **Separation of Concerns**: Each library has a single, well-defined responsibility
2. **Dependency Injection**: Hardware dependencies (e.g., `pigpio.pi`) are passed to constructors
3. **Configuration over Code**: Hardware settings live in `config.json`, not hardcoded
4. **Fail-Safe Defaults**: Libraries provide sensible defaults if configuration is missing
5. **Testability**: Libraries can be imported and tested without full hardware
6. **Dual Connectivity**: Commands can arrive via BLE or Web, routed through Dispatcher

### 1.3 Dependency Graph

```
ninja_core
    ├─→ ninja_utils (interfaces, logging)
    ├─→ ninja_ble → bless, bleak (BLE backend)
    ├─→ pi0buzzer → pigpio, click, ninja_utils (optional)
    ├─→ pi0vl53l0x → click, blessed, ninja_utils, pigpio (optional)
    ├─→ pi0disp → pigpio, numpy, pillow, click, ninja_utils (optional)
    ├─→ pi0servo → pigpio, click, blessed, ninja_utils (optional)
    ├─→ fastapi, uvicorn, pyngrok
    └─→ google-generativeai, googlesearch-python
```

**Key External Dependencies:**
- `pigpio` - GPIO control daemon (system-level)
- `bless` / `bleak` - BLE GATT server/client (V5)
- `pydantic` - Configuration validation
- `Pillow` - Image processing
- `numpy` - Numerical operations
- `click` - CLI framework
- `blessed` - Terminal UI (servo calibration)

---

## 2. Development Environment Setup

### 2.1 Prerequisites

- **Raspberry Pi Zero 2W** (or compatible model)
- **Raspberry Pi OS** (64-bit recommended)
- **Python 3.9+**
- **uv** package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **pigpiod** daemon (`sudo apt install pigpio && sudo pigpiod`)

### 2.2 Installation

```bash
# Clone repository
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5

# Install all packages in editable mode
uv pip install -e .

# Or install individually
uv pip install -e ./ninja_utils
uv pip install -e ./pi0buzzer
uv pip install -e ./pi0vl53l0x
uv pip install -e ./pi0disp
uv pip install -e ./pi0servo
uv pip install -e ./ninja_core
```

### 2.3 Development Tools

**Linting:**
```bash
uv run ruff check <file_path>
uv run ruff check <file_path> --fix
uv run ruff format <file_path>
```

**Running CLI Tools:**
```bash
uv run ninja_core --help
uv run pi0servo calib 20
uv run pi0disp image test.jpg
```

---

### Step 5: Test Safe Execution (Phase 4)

1.  **Run the Unit Tests:**
    ```bash
    uv run python test_safe_executor.py
    ```
    - Verifies that `os`/`sys` are blocked.
    - Verifies that `robot` API calls work.
    - Verifies `check_stop()` functionality.

2.  **Test Remote Execution (via curl):**
    ```bash
    curl -X POST "http://localhost:8000/api/code/execute" \
         -H "Content-Type: application/json" \
         -d '{"code": "print(\"Hello from API\")"}'
    ```

---

## 3. Library Reference

### 3.1 ninja_utils

**Purpose:** Shared utilities to avoid code duplication across libraries

**Dependencies:** None (pure Python)

**Location:** `ninja_utils/src/ninja_utils/`

#### 3.1.1 `my_logger.py`

**Module:** `ninja_utils.my_logger`

##### Function: `get_logger(name: str = "robot") -> logging.Logger`

Returns a configured logger instance with consistent formatting.

**Parameters:**
- `name` (str): Logger name (default: "robot")

**Returns:**
- `logging.Logger`: Configured logger with ISO timestamp format

**Usage:**
```python
from ninja_utils.my_logger import get_logger

log = get_logger(__name__)
log.info("Robot initialized")
log.error("Sensor failed", exc_info=True)
```

**Log Format:**
```
2025-11-21 12:00:00 - <name> - <level> - <message>
```

---

#### 3.1.2 `keyboard.py`

**Module:** `ninja_utils.keyboard`

##### Class: `NonBlockingKeyboard`

Provides non-blocking keyboard input for interactive CLI tools.

**Constructor:**
```python
def __init__(self)
```

**Methods:**

**`get_key() -> str | None`**
- Returns the key pressed since last call, or `None` if no key
- Non-blocking (returns immediately)

**`cleanup() -> None`**
- Restores terminal to normal mode
- **Must be called before exiting** to avoid terminal corruption

**Usage:**
```python
from ninja_utils.keyboard import NonBlockingKeyboard
import time

kb = NonBlockingKeyboard()
try:
    while True:
        key = kb.get_key()
        if key == 'q':
            break
        elif key:
            print(f"Pressed: {key}")
        time.sleep(0.1)
finally:
    kb.cleanup()
```

**Thread Safety:** Not thread-safe (use from main thread only)

---

#### 3.1.3 `service_manager.py`

**Module:** `ninja_utils.service_manager`

##### Class: `ServiceManager`

Manages the systemd service for automatic startup.

**Constructor:**
```python
def __init__(self, service_name: str = "ninjarobot", description: str = "NinjaRobotV4 Web Server")
```

**Methods:**

**`install() -> None`**
- Generates and installs the systemd service file
- Enables and starts the service
- **Raises:** `RuntimeError` if prerequisites (pigpiod, config) are missing

**`remove() -> None`**
- Stops, disables, and removes the systemd service file

**`status() -> None`**
- Prints the current status of the systemd service

---

#### 3.1.4 CLI Commands

**Entry Point:** `uv run ninja_utils <command>`

**Commands:**

**`install-startup`**
- Installs the autostart service
- **Example:** `uv run ninja_utils install-startup`

**`remove-startup`**
- Removes the autostart service
- **Example:** `uv run ninja_utils remove-startup`

**`status-startup`**
- Checks service status
- **Example:** `uv run ninja_utils status-startup`

---

### 3.2 pi0buzzer

**Purpose:** Non-blocking passive buzzer driver with musical note support, sound queue, and interactive TUI

**Dependencies:** `pigpio`, `click`, `ninja_utils` (optional — library works standalone without it)

**Location:** `pi0buzzer/src/pi0buzzer/`

**Hardware Interface:** GPIO PWM (software PWM via pigpio)

#### 3.2.1 `notes.py` — Note Frequency Constants

**Module:** `pi0buzzer.notes`

Single source of truth for all musical note data. Used by both `pi0buzzer` and `ninja_core/robot_sound.py`.

**Exports:**
- `NOTES` (dict[str, int]): Named note frequencies C3–B7 (e.g. `{"A4": 440, "C5": 523}`)
- `KEYBOARD_MAP` (dict[str, str]): Keyboard key → note name mapping for interactive piano
- `EMOTION_SOUNDS` (dict[str, list]): 14 emotion sound sequences (happy, sad, exciting, etc.)
- `DEMO_SONG` (list): Twinkle Twinkle Little Star melody
- `get_emotion_names() -> list[str]`: Sorted list of available emotion names

---

#### 3.2.2 `core/driver.py` — Buzzer Class

**Module:** `pi0buzzer.core.driver`

##### Class: `Buzzer(Actuator)`

Non-blocking passive buzzer driver implementing the `Actuator` interface. Sounds are played in a dedicated background worker thread.

**Constructor:**
```python
def __init__(self, pin: int, pi: Optional[pigpio.pi] = None, volume: int = 128)
```

**Parameters:**
- `pin` (int): GPIO pin number (BCM)
- `pi` (pigpio.pi, optional): Shared pigpio connection. If `None`, creates one internally.
- `volume` (int): PWM duty cycle 0–255 (default 128 = 50%)

**Actuator Interface Methods:**

| Method | Description | Blocking |
|---|---|---|
| `initialize()` | Starts background worker, sets pin mode. Idempotent. | No |
| `execute(command: dict)` | Queues `{"frequency": Hz, "duration": sec}` for playback | No |
| `off()` | Drains queue, stops worker, silences buzzer | No |

**Additional Methods / Properties:**

| Method / Property | Description |
|---|---|
| `play_sound(frequency, duration)` | Legacy compatibility — delegates to `execute()` |
| `queue_pause(duration)` | Queues a silent pause between notes |
| `volume` (property) | Get/set PWM duty cycle (0–255, clamped) |
| `is_initialized` (property) | Whether the buzzer is initialized |
| `__enter__` / `__exit__` | Context manager support |

**Key Design:**
- **Frequency validation:** Clamped to 20–20,000 Hz
- **Re-initialization guard:** `initialize()` is idempotent (no duplicate workers)
- **Queue-based pauses:** `"__pause__"` sentinel handled in worker thread
- **Queue drain:** `off()` clears pending sounds before stopping

**Usage:**
```python
import pigpio
from pi0buzzer.core.driver import Buzzer

pi = pigpio.pi()
buzzer = Buzzer(pin=17, pi=pi)
buzzer.initialize()

buzzer.play_sound(440, 0.5)  # A4 note, 0.5s — returns immediately
buzzer.off()
pi.stop()
```

**Context Manager Usage:**
```python
with Buzzer(pin=17) as buzzer:
    buzzer.play_sound(440, 0.5)
```

---

#### 3.2.3 `core/music.py` — MusicBuzzer Class

**Module:** `pi0buzzer.core.music`

##### Class: `MusicBuzzer(Buzzer)`

Extends `Buzzer` with named note playback, songs, emotions, and interactive keyboard piano.

**Constructor:**
```python
def __init__(self, pin: int, pi: Optional[pigpio.pi] = None, volume: int = 128)
```

**Inherits:** All `Buzzer` methods

**Methods:**

| Method | Parameters | Description |
|---|---|---|
| `play_note(note_name, duration)` | `"C4"`, `0.3` | Play named note (case-insensitive). Non-blocking. |
| `play_song(song)` | `[("C4", 0.3), ("pause", 0.1), ...]` | Queue note sequence. Non-blocking. |
| `play_emotion(name)` | `"happy"`, `"sad"`, etc. | Play predefined emotion sound. Non-blocking. |
| `play_demo()` | — | Play built-in Twinkle Twinkle Little Star |
| `play_music()` | — | Interactive keyboard piano (stdin-based) |

**Usage:**
```python
from pi0buzzer.core.music import MusicBuzzer

with MusicBuzzer(pin=17) as buzzer:
    buzzer.play_emotion("happy")
    buzzer.play_song([
        ("C4", 0.3), ("E4", 0.3), ("G4", 0.3), ("C5", 0.6),
    ])
```

**Backward Compatibility:** `from pi0buzzer.driver import MusicBuzzer` still works via the compatibility shim. This is the import path used by `ninja_core/hal.py`.

---

#### 3.2.4 `config/config_manager.py` — BuzzerConfigManager

**Module:** `pi0buzzer.config.config_manager`

##### Class: `BuzzerConfigManager`

Manages buzzer configuration stored as JSON. Matches the pattern used by `pi0disp` and `pi0servo`.

**Constructor:**
```python
def __init__(self, config_path: Optional[str] = None)
```
- Defaults to `buzzer.json` in the current working directory.

**Methods:**

| Method | Description |
|---|---|
| `load()` | Load config from JSON (falls back to defaults on missing/corrupt file) |
| `save()` | Save current config to JSON |
| `get_pin() / set_pin(pin)` | Get/set GPIO pin (validates 0–27) |
| `get_volume() / set_volume(vol)` | Get/set volume (validates 0–255) |
| `export_config(path)` | Export config to another file |
| `import_config(path)` | Import config from another file |
| `init_config(pin)` | Set pin and save (used by CLI `init` command) |

---

#### 3.2.5 CLI Commands

**Entry Point:** `uv run pi0buzzer <command>`

**Commands:**

| Command | Description | Example |
|---|---|---|
| `init <pin>` | Initialize config with GPIO pin, saves `buzzer.json`, plays test beep | `uv run pi0buzzer init 17` |
| `beep [freq] [dur]` | Play a single tone (default: 440 Hz, 0.5s) | `uv run pi0buzzer beep 880 0.3` |
| `play <emotion>` | Play a predefined emotion sound | `uv run pi0buzzer play happy` |
| `info [--health-check]` | Show config and optionally verify hardware | `uv run pi0buzzer info --health-check` |
| `config show` | Display current configuration as JSON | `uv run pi0buzzer config show` |
| `config export <path>` | Export config to file | `uv run pi0buzzer config export backup.json` |
| `config import <path>` | Import config from file | `uv run pi0buzzer config import backup.json` |
| `buzzer-tool` | Launch interactive TUI menu (9 options) | `uv run pi0buzzer buzzer-tool` |

**Available Emotions:** angry, confusing, cry, embarrassing, exciting, happy, idle, laughing, sad, scary, shy, sleepy, speaking, surprising

---

### 3.3 pi0vl53l0x

**Purpose:** Robust driver for VL53L0X Time-of-Flight distance sensor

**Dependencies:** `pigpio` (optional, RPi only), `click`, `ninja_utils`

**Location:** `pi0vl53l0x/src/pi0vl53l0x/`

**Hardware Interface:** I2C (default address: 0x29, bus: 1)

> [!IMPORTANT]
> **V5.2.3 REBUILD**: The pi0vl53l0x library was completely rebuilt with a new architecture:
> - **Thread-safe I2C** via `threading.Lock` — safe for multi-threaded `DistanceMonitor` use
> - **Hardened initialization** — firmware boot polling (up to 1.0s) prevents "returns 0 after reboot"
> - **Automatic retry** with exponential backoff (10→20→50ms) and bus recovery
> - **V2 offset bug fix** — `get_data()` now stores true raw value before offset correction
> - **Health check + reinitialize** for runtime recovery without reboot

#### 3.3.1 `core/i2c.py`

**Module:** `pi0vl53l0x.core.i2c`

##### Class: `I2CBus`

Thread-safe I2C bus wrapper with automatic retry and bus recovery.

**Constructor:**
```python
def __init__(
    self,
    pi: pigpio.pi,
    bus: int = 1,
    address: int = 0x29,
    max_retries: int = 3,
)
```

**Parameters:**
- `pi` (pigpio.pi): Shared pigpio connection
- `bus` (int): I2C bus number (default: 1)
- `address` (int): 7-bit I2C address (default: 0x29)
- `max_retries` (int): Max retries per operation (default: 3)

**Key Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `read_byte(register)` | `int` | Read single byte |
| `write_byte(register, value)` | `None` | Write single byte |
| `read_word_big_endian(register)` | `int` | Read 16-bit word (byte-swap) |
| `write_word_big_endian(register, value)` | `None` | Write 16-bit word (byte-swap) |
| `read_block(register, count)` | `list[int]` | Read block of bytes |
| `write_block(register, data)` | `None` | Write block of bytes |
| `close()` | `None` | Close I2C handle (safe to call multiple times) |

**Thread Safety:** All operations are serialized via `threading.Lock`. Concurrent access from `DistanceMonitor` and main thread is safe.

**Retry Strategy:** Exponential backoff (10ms → 20ms → 50ms). On exhaustion, attempts bus recovery by closing and reopening the I2C handle.

##### Exception: `I2CError`

Raised when I2C communication fails after all retries. Inherits from `Exception`.

---

#### 3.3.2 `registers.py`

**Module:** `pi0vl53l0x.registers`

Contains ~60 semantic register constants for the VL53L0X sensor, replacing magic hex values throughout the codebase.

**Key Constants:**
- `SYSRANGE_START = 0x00` — Trigger measurement
- `RESULT_RANGE_STATUS = 0x14` — Result range status
- `IDENTIFICATION_MODEL_ID = 0xC0` — Model ID register (expected: 0xEE)
- `DEVICE_ADDRESS = 0x29` — Default I2C address

---

#### 3.3.3 `core/sensor.py`

**Module:** `pi0vl53l0x.core.sensor`

##### Class: `VL53L0X`

Main driver for the VL53L0X distance sensor. Implements the `Sensor` ABC from `ninja_utils.interfaces`.

**Constructor:**
```python
def __init__(
    self,
    pi: pigpio.pi,
    i2c_bus: int = 1,
    i2c_address: int = 0x29,
    debug: bool = False,
    config_file_path: Any = None,
    firmware_boot_timeout: float = 1.0,
)
```

**Parameters:**
- `pi` (pigpio.pi): Shared pigpio connection
- `i2c_bus` (int): I2C bus number (default: 1)
- `i2c_address` (int): 7-bit I2C address (default: 0x29)
- `debug` (bool): Enable debug logging
- `config_file_path` (str | None): Path to config JSON with offset_mm
- `firmware_boot_timeout` (float): Firmware boot timeout in seconds (default: 1.0)

> [!NOTE]
> The constructor auto-calls `initialize()` — no separate init step is needed. If initialization fails, the I2C handle is automatically released.

**Public API — Measurement:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_range()` | `int` | Single-shot distance in mm (with offset applied) |
| `get_data()` | `dict` | `{distance_mm, is_valid, raw_value, timestamp}` |
| `get_ranges(num_samples)` | `list[int]` | Multiple consecutive measurements |
| `get_range_async()` | `int` | Async version (runs in thread pool executor) |

**Public API — Calibration & Configuration:**

| Method | Returns | Description |
|--------|---------|-------------|
| `set_offset(offset_mm)` | `None` | Set distance offset in mm |
| `calibrate(target_distance_mm, num_samples)` | `int` | Measure and return calculated offset |

**Public API — Health & Recovery:**

| Method | Returns | Description |
|--------|---------|-------------|
| `health_check()` | `bool` | Verify sensor responds (reads Model ID) |
| `reinitialize()` | `None` | Full re-init — NOT thread-safe |
| `close()` | `None` | Release I2C handle |

**Backward Compatibility Shim Methods:**
- `read_byte(register)`, `write_byte(register, value)` — delegate to `self.i2c`
- `read_word(register)`, `write_word(register, value)` — delegate to `self.i2c`
- `read_block(register, count)`, `write_block(register, data)` — delegate to `self.i2c`

**Exception Contract:**

| Exception | When |
|-----------|------|
| `I2CError` | I2C bus failure after retries |
| `TimeoutError` | Measurement/boot did not complete within timeout |
| `RuntimeError` | Sensor not initialized |
| `ConnectionError` | Invalid Model ID or connection failure |

**Usage:**
```python
import pigpio
from pi0vl53l0x import VL53L0X

pi = pigpio.pi()
sensor = VL53L0X(pi)  # Auto-initializes

# Single measurement
distance = sensor.get_range()
print(f"Distance: {distance}mm")

# Structured data with validity check
data = sensor.get_data()
if data["is_valid"]:
    print(f"Distance: {data['distance_mm']}mm (raw: {data['raw_value']}mm)")

# Calibrate at known 100mm distance
offset = sensor.calibrate(target_distance_mm=100, num_samples=10)
sensor.set_offset(offset)

# Health check and recovery
if not sensor.health_check():
    sensor.reinitialize()

sensor.close()
pi.stop()
```

**Context Manager:**
```python
with VL53L0X(pi) as sensor:
    distance = sensor.get_range()
```

**Async Support:**
```python
distance = await sensor.get_range_async()
```

**Backward-Compatible Import:**
```python
# Both imports work (driver.py is a shim)
from pi0vl53l0x import VL53L0X
from pi0vl53l0x.driver import VL53L0X
```

---

#### 3.3.4 `config/config_manager.py`

**Module:** `pi0vl53l0x.config.config_manager`

##### Class: `ConfigManager`

Manages sensor configuration persistence in `vl53l0x.json`.

**Constructor:**
```python
def __init__(self, config_path: Path | str | None = None)
```

**Key Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `load()` | `dict` | Load config from JSON file |
| `save()` | `None` | Save current config to JSON file |
| `get(key, default)` | `Any` | Get config value by key |
| `set(key, value)` | `None` | Set config value |
| `export_config(path)` | `None` | Export to backup file |
| `import_config(path)` | `dict` | Import from backup file |

**Properties:**
- `path` — Config file path
- `config` — Current configuration dictionary

##### Standalone Functions (backward-compatible):

```python
from pi0vl53l0x.config import load_config, save_config

config = load_config()          # Returns {"offset_mm": 0} or {}
save_config(config={"offset_mm": 10})
```

---

#### 3.3.5 CLI Commands

**Entry Point:** `uv run pi0vl53l0x <command>` or `pi0vl53l0x <command>`

| Command | Description |
|---------|-------------|
| `get -c 10 -i 1.0` | Take 10 distance readings at 1s intervals |
| `performance -c 100` | Measure reading speed (readings/sec) |
| `calibrate -d 100 -c 10` | Guided offset calibration at 100mm |
| `test` | Quick sensor validation (5 readings) |
| `status` | Sensor health report (Model ID, connection, test reading) |
| `config show` | Display current configuration |
| `config export backup.json` | Export configuration to file |
| `config import backup.json` | Import configuration from file |

**Examples:**
```bash
# Quick health check
uv run pi0vl53l0x test

# Continuous measurement
uv run pi0vl53l0x get --count 20 --interval 0.5

# Calibration workflow
uv run pi0vl53l0x calibrate --distance 100 --count 10

# Config management
uv run pi0vl53l0x config show
uv run pi0vl53l0x config export backup.json
```

---

### 3.4 pi0disp

**Purpose:** Thread-safe SPI driver for ST7789V 240×320 displays with smart delta rendering

**Dependencies:** `pigpio`, `numpy`, `Pillow`, `click`, `ninja_utils` (optional — library works standalone)

**Location:** `pi0disp/src/pi0disp/`

**Hardware Interface:** SPI0 (SCLK, MOSI) + GPIO (DC, RST, BLK)

> [!IMPORTANT]
> **V5.2.4 REBUILD**: The pi0disp library was completely rebuilt with a new architecture:
> - **Thread-safe SPI** via `threading.Lock` — safe for concurrent `AnimatedFaces` + `web_server` access
> - **Smart delta rendering** — only transmits changed pixels via `PIL.ImageChops.difference()`
> - **PWM brightness** — smooth backlight control (0-100%) via `pigpio.set_PWM_dutycycle()`
> - **ConfigManager** — `display.json` with interactive setup wizard, CRUD, export/import
> - **CLI overhaul** — 11 commands + interactive `display-tool` menu

#### 3.4.1 `core/driver.py`

**Module:** `pi0disp.core.driver`

##### Class: `ST7789V`

Main display driver class. Implements the `Actuator` ABC from `ninja_utils.interfaces`.

**Constructor:**
```python
def __init__(
    self,
    pi=None,
    channel: int = 0,
    dc_pin: int = 14,
    rst_pin: int = 15,
    backlight_pin: int = 16,
    speed_hz: int = 32_000_000,
    width: int = 240,
    height: int = 320,
    rotation: int = 0,
)
```

**Parameters:**
- `pi` (pigpio.pi | None): Shared pigpio connection. If None, creates a new one
- `channel` (int): SPI channel (0 or 1)
- `dc_pin` (int): Data/Command GPIO pin
- `rst_pin` (int): Reset GPIO pin
- `backlight_pin` (int): Backlight GPIO pin
- `speed_hz` (int): SPI clock speed (default: 32 MHz)
- `width`, `height` (int): Display dimensions (default: 240×320)
- `rotation` (int): Display rotation (0, 90, 180, or 270)

**Public API — Display:**

| Method | Returns | Description |
|--------|---------|-------------|
| `display(image)` | `None` | Display image with smart delta rendering (thread-safe) |
| `display_region(image, x0, y0, x1, y1)` | `None` | Display a sub-region (thread-safe) |
| `clear(color=(0,0,0))` | `None` | Fill display with solid color |
| `set_brightness(percent)` | `None` | Set backlight PWM (0-100%) |
| `set_rotation(degrees)` | `None` | Set rotation (0, 90, 180, 270) |

**Public API — Power Management:**

| Method | Returns | Description |
|--------|---------|-------------|
| `sleep()` | `None` | Enter low-power sleep mode |
| `wake()` | `None` | Wake from sleep mode |
| `health_check()` | `bool` | Verify SPI connection is alive |
| `close()` | `None` | Release SPI handle, GPIO, and backlight |

**Actuator ABC Interface:**

| Method | Returns | Description |
|--------|---------|-------------|
| `initialize()` | `None` | Wake display |
| `execute(command)` | `None` | Dispatch command dict (see below) |
| `off()` | `None` | Sleep + backlight off |

**`execute()` command keys:**
- `{"image": PIL.Image}` — Display an image
- `{"brightness": int}` — Set brightness (0-100)
- `{"backlight": int}` — Alias for brightness
- `{"clear": True}` — Clear display
- `{"rotation": int}` — Set rotation

**Usage:**
```python
import pigpio
from PIL import Image
from pi0disp.core.driver import ST7789V

pi = pigpio.pi()
lcd = ST7789V(pi=pi, dc_pin=14, rst_pin=15, backlight_pin=16)

# Display an image (auto-resized, delta rendering)
img = Image.open("face.png").convert("RGB")
lcd.display(img)

# Set brightness and rotation
lcd.set_brightness(80)
lcd.set_rotation(90)

# Cleanup
lcd.close()
pi.stop()
```

**Context Manager:**
```python
with ST7789V(pi=pi) as lcd:
    lcd.display(Image.open("face.png").convert("RGB"))
```

**Backward-Compatible Import:**
```python
# Both imports work
from pi0disp import ST7789V
from pi0disp.core.driver import ST7789V
```

---

#### 3.4.2 `core/renderer.py`

**Module:** `pi0disp.core.renderer`

Contains optimization classes for high-performance rendering:

##### Class: `ColorConverter`
- Fast RGB → RGB565 conversion using numpy lookup tables (LUT)
- Method: `rgb_to_rgb565_bytes(rgb_array) -> bytes`

##### Class: `RegionOptimizer`
- Merges overlapping/nearby dirty regions for efficient SPI transfers
- Method: `clamp_region(region, width, height) -> tuple`
- Method: `merge_regions(regions, max_regions=8, merge_threshold=50) -> list`

**Usage:** These are internal utility classes used by `ST7789V` for delta rendering.

---

#### 3.4.3 `config/config_manager.py`

**Module:** `pi0disp.config.config_manager`

##### Class: `ConfigManager`

Manages display configuration persistence in `display.json`.

**Constructor:**
```python
def __init__(self, config_file: str = "display.json")
```

**Key Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `load()` | `dict` | Load config from JSON file |
| `save()` | `None` | Save current config to disk |
| `get(key, default)` | `Any` | Get a config value |
| `set(key, value)` | `None` | Set a value and save |
| `export_config(path)` | `None` | Export to file |
| `import_config(path)` | `dict` | Import from file |
| `init_config(interactive)` | `dict` | Interactive or default setup wizard |

**Available Display Profiles:**
- `ST7789V 2.8-inch IPS TFT` (240×320)
- `Waveshare 2.0-inch IPS LCD` (240×320)

---

#### 3.4.4 `effects/text_ticker.py`

**Module:** `pi0disp.effects.text_ticker`

##### Class: `TextTicker`

Scrolling marquee text animation with multilingual font support.

**Constructor:**
```python
def __init__(
    self,
    lcd,
    text: str,
    font_size: int = 32,
    color: Tuple[int, int, int] = (255, 255, 255),
    bg_color: Tuple[int, int, int] = (0, 0, 0),
    speed: float = 2.0,
    language: str = "en",
)
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `start()` | `None` | Start scrolling in a background thread |
| `stop()` | `None` | Stop and join the thread |
| `is_running()` | `bool` | Check if currently animating |

**Supported Languages:** `en` (English), `ja` (Japanese), `zh-tw` (Traditional Chinese)

---

#### 3.4.5 CLI Commands

**Entry Point:** `uv run pi0disp <command>`

**Commands:**

**`init [--defaults]`**
- Interactive display setup wizard (pin config, display profile, rotation, brightness)
- **Example:** `uv run pi0disp init`

**`image <path>`**
- Display an image file (auto-resized to fit display)
- **Example:** `uv run pi0disp image assets/images/sample_face.jpg`

**`text "..." [--scroll] [--lang LANG] [--speed N]`**
- Display static or scrolling text with multilingual fonts
- **Example:** `uv run pi0disp text "Hello" --scroll --lang ja`

**`demo [--num-balls N] [--duration SEC]`**
- Bouncing ball physics animation demo
- **Example:** `uv run pi0disp demo --num-balls 5`

**`info [--health-check]`**
- Show driver state, config, and optional hardware health check
- **Example:** `uv run pi0disp info --health-check`

**`clear`**
- Clear the display (fill black)

**`brightness <0-100>`**
- Set backlight brightness
- **Example:** `uv run pi0disp brightness 50`

**`config show | set | export | import`**
- Configuration management subcommands

**`display-tool`**
- Interactive menu with 9 options for exercising all display functions

---

### 3.5 pi0servo

**Purpose:** Velocity-based servo control with calibration and smooth easing

**Dependencies:** `pigpio`, `click`, `blessed`, `ninja_utils`

**Location:** `pi0servo/src/pi0servo/`

**Hardware Interface:** GPIO PWM (500-2500μs pulse width)

> [!IMPORTANT]
> **V5.2.1 REBUILD**: The pi0servo library was completely rebuilt with a new architecture:
> - **Velocity-based control** instead of duration-based (`degrees/sec`)
> - **Per-servo speed modes** (F=Fast, M=Medium, S=Slow)
> - **100Hz update rate** (10ms interval) for jitter-free motion
> - **Thread-safe abort** mechanism
> - **Cubic easing** curves (`ease_in_out_cubic` default, plus 6 other options)

#### 3.5.1 `core/multi_servos.py`

**Module:** `pi0servo.core.multi_servos`

##### Class: `ServoGroup`

Main class for controlling multiple servos. Used by `ninja_core.hal`.

**Constructor:**
```python
def __init__(
    self,
    pi: pigpio.pi,
    pins: list[int],
    calibrations: dict[int, ServoCalibration] | None = None
)
```

**Parameters:**
- `pi` (pigpio.pi): Shared pigpio connection
- `pins` (list[int]): List of GPIO pin numbers
- `calibrations` (dict): Pre-loaded calibration data from `ConfigManager`

**Key Methods:**

**`move_all_sync(targets: list[float | None], speed_mode: str | list[str] = "M", easing: str = "ease_in_out_cubic", force: bool = False) -> bool`**
- Moves all servos to target angles synchronously with smooth easing
- **Parameters:**
  - `targets` (list): Target angles (-90 to 90), `None` = skip servo
  - `speed_mode` (str | list): "F"/"M"/"S" or list for per-servo speeds
  - `easing` (str | Callable): Easing function name or callable (default: `ease_in_out_cubic`)
  - `force` (bool): If `True`, send PWM even for very small movements (prevents limpness)
- **Returns:** `True` if completed, `False` if aborted

**`move_all_async(targets, speed_mode, easing) -> bool`**
- Async (non-blocking) version of `move_all_sync` using `asyncio.sleep`
- **Returns:** `True` if completed, `False` if aborted

**`execute_command(command: str, easing: str = "ease_in_out_cubic") -> bool`**
- Execute a movement-tool format command string (e.g., `"F_20:45/21:-30"`)

**`execute_command_async(command: str, easing: str = "ease_in_out_cubic") -> bool`**
- Async version of `execute_command`

**`get_all_angles() -> list[float]`**
- Returns current angles for all servos

**`abort() -> None`**
- Thread-safe: immediately stops any running movement

**`off() -> None`**
- Turns off PWM for all servos

**`center_all() -> None`**
- Moves all servos to their calibrated center position

**`refresh_all() -> None`**
- Re-sends PWM to all servos with known positions (prevents limpness)

**Legacy Compatibility Methods:**
- `move_all_angles(angles: list[float])` — Instant move (no interpolation)
- `move_all_angles_sync(target_angles, move_sec, step_n)` — Duration-based (maps to velocity internally)
- `get_all_angles() -> list[float]` — Returns current angles for all servos
- `servo` property — List access by pin order

**Usage:**
```python
import pigpio
from pi0servo import ServoGroup, ConfigManager

pi = pigpio.pi()

# Load calibrations
manager = ConfigManager()
manager.load()
calibrations = {20: manager.get_calibration(20), 21: manager.get_calibration(21)}

# Create group
group = ServoGroup(pi, pins=[20, 21], calibrations=calibrations)

# Move with per-servo speeds
group.move_all_sync([45, -30], speed_mode=["F", "S"], easing="ease_in_out_cubic")

# Abort from another thread
group.abort()

group.off()
pi.stop()
```

---

#### 3.5.2 `config/config_manager.py`

**Module:** `pi0servo.config.config_manager`

##### Class: `ConfigManager`

Manages servo calibration persistence in `servo.json`.

**Key Methods:**

**`load() -> bool`**
- Loads calibration from JSON file
- **Returns:** `True` if loaded successfully, `False` if file missing or error

**`save() -> bool`**
- Saves calibration to JSON file
- **Returns:** `True` if saved successfully, `False` on error

**`get_calibration(pin: int) -> ServoCalibration`**
- Returns calibration data for a pin

**`set_calibration(pin: int, calib: ServoCalibration) -> None`**
- Stores calibration data

##### Dataclass: `ServoCalibration`

Defined in `pi0servo.core.servo`:

```python
@dataclass
class ServoCalibration:
    pulse_min: int = 1500       # Min pulse width (μs) — defaults to center (uncalibrated)
    pulse_max: int = 1500       # Max pulse width (μs)
    pulse_center: int = 1500    # Center pulse width (μs)
    angle_min: float = -90.0    # Minimum angle (degrees)
    angle_max: float = 90.0     # Maximum angle (degrees)
    angle_center: float = 0.0   # Center angle (degrees)
    speed: int = 80             # Speed limit (0-100%)
```

---

#### 3.5.3 `motion/calculator.py` + `motion/easing.py`

**Module:** `pi0servo.motion.calculator` — velocity/duration calculations  
**Module:** `pi0servo.motion.easing` — interpolation curves

**Key Functions (calculator):**

**`calculate_duration(distance: float, speed_limit: int, speed_mode: str) -> float`**
- Calculates movement duration from angle distance and velocity
- Uses physics: `velocity = 600°/s × (speed_limit/100) × FMS_multiplier`

**Easing Functions (easing):**

Available via `EASING_FUNCTIONS` dict lookup or direct import:

| Function | Type | Description |
|----------|------|-------------|
| `linear` | — | No easing |
| `ease_in` | Quadratic | Start slow, end fast |
| `ease_out` | Quadratic | Start fast, end slow |
| `ease_in_out` | Quadratic | Smooth accel/decel |
| `ease_in_cubic` | Cubic | Very slow start |
| `ease_out_cubic` | Cubic | Very slow end |
| `ease_in_out_cubic` | Cubic | **Default** — smoothest |

---

#### 3.5.4 CLI Commands

**Entry Point:** `uv run pi0servo <command>`

**Interactive Tool:**
```bash
uv run pi0servo servo-tool  # Recommended for all operations
```

**Direct Commands:**

| Command | Description |
|---------|-------------|
| `uv run pi0servo calib 20` | Calibrate servo on GPIO 20 |
| `uv run pi0servo move 20 45` | Move servo to 45° |
| `uv run pi0servo cmd "F_20:45/21:-30S"` | Multi-servo command |
| `uv run pi0servo config show` | Show all calibrations |

**Command Syntax:**
```
[GLOBAL_SPEED_]PIN:ANGLE[LOCAL_SPEED][/PIN:ANGLE[LOCAL_SPEED]...]
```

| Example | Description |
|---------|-------------|
| `20:45` | Move GPIO20 to 45° (Medium) |
| `F_20:45/21:-30` | Both Fast |
| `M_20:45/21:90S` | Global Medium, 21 overrides to Slow |
| `20:C` | Move to Center (0°) |
| `20:M` | Move to Min (-90°) |
| `20:X` | Move to Max (90°) |

---

### 3.6 ninja_core

**Purpose:** Main robot application integrating all libraries

**Dependencies:** All hardware libraries + `fastapi`, `uvicorn`, `pyngrok`, `google-generativeai`, `googlesearch-python`, `websockets`, `python-multipart`, `qrcode`, `Pillow`, `jinja2`, `python-dotenv`, `pydantic`

**Location:** `ninja_core/src/ninja_core/`

#### 3.6.1 `config.py`

**Module:** `ninja_core.config`

Centralized configuration management using Pydantic.

##### Data Models

**`ServoCalibration`** (Pydantic BaseModel)
```python
class ServoCalibration(BaseModel):
    min_pulse: int = 500
    center_pulse: int = 1500
    max_pulse: int = 2500
    angle_range: int = 180
```

**`ServosConfig`** (Pydantic BaseModel)
```python
class ServosConfig(BaseModel):
    pins: Dict[str, int] = Field(default_factory=dict)
    calibration: Dict[str, ServoCalibration] = Field(default_factory=dict)
```

**`BuzzerConfig`** (Pydantic BaseModel)
```python
class BuzzerConfig(BaseModel):
    pin: Optional[int] = None
```

**`DisplayConfig`** (Pydantic BaseModel)
```python
class DisplayConfig(BaseModel):
    dc: Optional[int] = 14
    rst: Optional[int] = 15
    blk: Optional[int] = 16
```

**`SensorConfig`** (Pydantic BaseModel)
```python
class SensorConfig(BaseModel):
    pass  # Placeholder for future sensor settings
```

**`NinjaConfig`** (Pydantic BaseModel)
```python
class NinjaConfig(BaseModel):
    servos: ServosConfig = Field(default_factory=ServosConfig)
    buzzer: BuzzerConfig = Field(default_factory=BuzzerConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    sensors: SensorConfig = Field(default_factory=SensorConfig)
    movements: Dict[str, list] = Field(default_factory=dict)
    api_keys: Dict[str, str] = Field(default_factory=dict)
```

##### Functions

**`load_config(path: Path = Path("config.json")) -> NinjaConfig`**
- Loads configuration from JSON, creates default if missing

**`save_config(config: NinjaConfig, path: Path = Path("config.json")) -> None`**
- Saves configuration to JSON

**`import_and_update_config() -> None`**
- Imports `servo.json` and `buzzer.json` into main `config.json`
- Applies default servo calibration if `servo.json` not found

**`set_api_key(service: str, key: str) -> None`**
- Sets an API key (e.g., "gemini") and saves config

**Usage:**
```python
from ninja_core.config import load_config, save_config, set_api_key

config = load_config()
print(config.servos.calibration)
print(config.api_keys.get("gemini"))

set_api_key("gemini", "AIzaSy...")
```

---

---

#### 3.6.2 `dispatcher.py` (New Phase 2)

**Module:** `ninja_core.dispatcher`

**Purpose:** The central nervous system for routing versioned commands from multiple sources (Web, BLE) to the HAL, agent, and Blockly execution runtime while preserving a single active execution lifecycle.

##### Class: `CommandDispatcher` (Singleton)

**Constructor:**
`__init__(self, hal: Optional[HardwareAbstractionLayer] = None)`

**Methods:**

**`register_listener(self, callback: Callable[[dict], Any]) -> None`**
- Registers a callback to receive broadcast messages (e.g., AI responses).
- Used by `NinjaBLEService` and `WebSocketManager`.

**`attach_agent(self, agent: Any) -> None`**
- Connects the `NinjaAgent` instance for AI command processing.

**`async handle_command(self, source: str, command: dict) -> dict`**
- Main entry point for all commands.
- **Parameters:**
    - `source`: "ble" or "web"
    - `command`: JSON dictionary (e.g., `{"type": "chat", ...}`)
- **Returns:** JSON-compatible result dictionary.

**Supported Command Types:**
1. **`chat`** -> Routes to `NinjaAgent.process_command()`. Broadcasts user message and AI response.
2. **`hal`** -> Routes to `HardwareAbstractionLayer`.
3. **`execute`** -> Runs Blockly-generated Python through `SafeExecutor`, broadcasts `execute_received`, then `execution_status: started`, and keeps all follow-up events on the same `request_id`.
4. **`stop`** -> Sends a cooperative stop signal to `SafeExecutor.stop()` and broadcasts `execution_status: stop_requested` for the active request.

**Execution Lifecycle Guarantees:**
- Every execution request carries a `request_id`.
- Only one execution may be active at a time.
- If a second `execute` arrives while code is already running, the dispatcher emits an `execute_rejected` error for the new request **without** clearing the original active request.
- If generated code fails syntax compilation, the dispatcher emits `execute_received`, `execution_status: error`, and `error.code: syntax_error` with structured line details, but it does not emit a false `started` status.
- Completion, failure, stop, chat explanation, and execution-log events all stay correlated to the active request.

**Usage:**
```python
dispatcher = CommandDispatcher(hal)
result = await dispatcher.handle_command("ble", {"type": "chat", "text": "Hi"})
```

---

#### 3.6.3 `hal.py`

**Module:** `ninja_core.hal`

Hardware Abstraction Layer providing unified hardware access.

##### Class: `HardwareAbstractionLayer`

**Constructor:**
```python
def __init__(self, config: NinjaConfig)
```

**Attributes (after `initialize()` called):**
- `pi` (pigpio.pi): Shared pigpio connection
- `servos` (MultiServo | None): Servo controller
- `buzzer` (MusicBuzzer | None): Buzzer controller
- `display` (ST7789V | None): Display controller
- `distance_sensor` (VL53L0X | None): Sensor instance

**Methods:**

**`initialize(components: list[str] = None) -> None`**
- Connects to `pigpiod`
- Initializes hardware based on config.
- **Parameters:**
  - `components`: Optional list of keys ("servos", "buzzer", "display", "sensors"). If None, initializes all.
- **Note:** Fault-tolerant; logs warnings if individual components fail.
- **Raises:** `ConnectionError` if pigpiod not running

**`shutdown() -> None`**
- Safely turns off all hardware
- Disconnects from pigpiod

**Usage:**
```python
from ninja_core.config import load_config
from ninja_core.hal import HardwareAbstractionLayer

config = load_config()
hal = HardwareAbstractionLayer(config)
hal.initialize()

# Use hardware
hal.servos.move_all_angles([0, 0, 0])
hal.buzzer.play_sound(440, 0.5)
hal.display.display(my_image)
distance = hal.distance_sensor.get_range()

# Cleanup
hal.shutdown()
```

---

#### 3.6.4 `ninja_agent.py`

**Module:** `ninja_core.ninja_agent`

AI agent powered by Google Gemini for natural language understanding.

##### Exception: `MissingAPIKeyError`

Raised when Gemini API key is not configured.

##### Class: `NinjaAgent`

**Constructor:**
```python
def __init__(self, config: NinjaConfig)
```

**Raises:** `MissingAPIKeyError` if `config.api_keys["gemini"]` is missing

**Attributes:**
- `api_key` (str): Gemini API key
- `robot_capabilities` (dict): Available movements, faces, sounds
- `system_prompt` (str): AI instruction prompt
- `model` (genai.GenerativeModel): Gemini model instance

**Methods:**

**`_load_robot_capabilities(config: NinjaConfig) -> dict`**
- Private method to extract available actions from config

**`_create_system_prompt() -> str`**
- Private method to generate the AI system prompt
- Includes multilingual instructions and JSON output format

**`async process_command(user_input: str) -> dict`**
- Main method to process text commands
- Uses **Gemini 3.0 Flash** to interpret intent.
- **Parameters:**
  - `user_input` (str): User's message
- **Returns:** Dict with keys:
  - `action_plan` (dict): JSON action plan.
    ```json
    {
      "chain": [{"name": "move_name", "repetitions": 1}, ...],
      "face_chain": [{"name": "face_name", "duration": 2.0}, ...],
      "sound_chain": ["sound1", "sound2"],
      "face": "face_name", # (Legacy)
      "sound": "sound_name", # (Legacy)
      "movement": "move_name", # (Legacy)
      "response": "text"
    }
    ```
  - `response` (str): AI's text response
  - `log` (str): Debug information

**`async explain_code(code: str) -> str`**
- Generates a concise natural language explanation of Python code.

**`async generate_code(user_request: str) -> str`**
- Generates Python code from a natural language request.

**`async analyze_error(code: str, error_msg: str) -> str`**
- Analyzes runtime errors and suggests fixes.

**`async analyze_code(code: str) -> str`**
- Analyzes code for potential issues.
  - `logs` (str): Debug log messages

**`async process_audio_command(audio_file_path: str) -> dict`**
- Processes voice commands from audio file
- **Parameters:**
  - `audio_file_path` (str): Path to audio file (e.g., `.webm`)
- **Returns:** Same format as `process_command()`
- **Note:** Uses Gemini's audio transcription + processing

**Usage:**
```python
import asyncio
from ninja_core.config import load_config
from ninja_core.ninja_agent import NinjaAgent

config = load_config()
agent = NinjaAgent(config)

async def main():
    result = await agent.process_command("Walking forward 3 times")
    print(result["response"])
    # result['action_plan']['chain'] contains movement steps

asyncio.run(main())
```

> [!NOTE]
> **Post-Task Reset**: The agent is designed to be state-less regarding mechanical position. The `web_server.py` and `__main__.py` executors automatically center all servos and reset the facial expression to "idle" upon completion of an action plan.

---

#### 3.6.5 `movement_controller.py`

**Module:** `ninja_core.movement_controller`

Motion system with smooth interpolation and safety checks.

##### Exception: `EmergencyStop`

Raised when `abort_check` callback returns `True` during movement.

##### Class: `MovementController`

**Constructor:**
```python
def __init__(self, hal: HardwareAbstractionLayer, config: NinjaConfig)
```

**Attributes:**
- `servos` (MultiServo): Reference to HAL's servo controller
- `servo_definitions` (dict): Calibration data
- `movements` (dict): Named movement sequences from config

**Methods:**

**`move_servos(movements: dict[int, float], speed: str = "M", abort_check: Callable[[], bool] | None = None) -> None`**
- Executes smooth interpolated movement
- **Parameters:**
  - `movements` (dict): `{pin: target_angle}` mapping
  - `speed` (str): "S" (slow, 1.0s), "M" (medium, 0.5s), "F" (fast, 0.2s)
  - `abort_check` (callable): Optional safety callback
- **Raises:** `EmergencyStop` if abort_check returns True

**`get_current_angles() -> dict[int, float]`**
- Returns current angles for all servos

**`center_all_servos() -> None`**
- Moves all servos to 0° (center position)

**`execute_movement(movement_name: str, abort_check: Callable[[], bool] | None = None) -> None`**
- Executes a pre-defined movement sequence by name
- **Position-aware easing** for smooth transitions:
  - Single step: `ease_in_out_cubic` (complete S-curve)
  - First step: `ease_in_cubic` (accelerate only)
  - Middle steps: `linear` (constant velocity)
  - Last step: `ease_out_cubic` (decelerate to stop)
- **Raises:** `EmergencyStop` if safety check fails

**Usage:**
```python
from ninja_core.movement_controller import MovementController

controller = MovementController(hal, config)

# Execute single movement
controller.move_servos({20: 45, 21: -30}, speed="M")

# Execute named sequence
controller.execute_movement("wave")

# With safety check
def check_distance():
    return hal.distance_sensor.get_range() <= 50

try:
    controller.execute_movement("forward", abort_check=check_distance)
except EmergencyStop:
    print("Movement aborted due to obstacle!")
```

---

#### 3.6.6 `facial_expressions.py`

**Module:** `ninja_core.facial_expressions`

Programmatic facial animation system.

##### Class: `AnimatedFaces`

Draws and animates facial expressions on the display.

**Constructor:**
```python
def __init__(self, hal: HardwareAbstractionLayer | None)
```

**Parameters:**
- `hal` (HardwareAbstractionLayer | None): HAL instance (can be None for introspection)

**Attributes:**
- `lcd` (ST7789V): Display driver
- `animations` (dict): Mapping of expression names to animation functions
- `current_expression` (str): Name of currently playing expression

**Available Expressions:**
- `"idle"` - Neutral/calm face
- `"happy"` - Smiling face
- `"sad"` - Frowning face
- `"angry"` - Angry expression
- `"surprised"` - Wide-eyed surprise
- `"thinking"` - Thoughtful expression
- `"speaking"` - Talking animation
- `"scary"` - Frightened/shocked face
- `"laughing"` - Joyful laughing
- `"sleeping"` - Closed eyes

**Methods:**

**`play(expression: str, duration_s: float = float('inf')) -> None`**
- Starts playing an expression animation in a background thread
- **Parameters:**
  - `expression` (str): Expression name from `animations.keys()`
  - `duration_s` (float): Duration in seconds (default: infinite)

**`stop() -> None`**
- Stops the current animation thread

**Usage:**
```python
from ninja_core.facial_expressions import AnimatedFaces

faces = AnimatedFaces(hal)

# Play happy face for 3 seconds
faces.play("happy", duration_s=3.0)
time.sleep(3.5)

# Play speaking animation
faces.play("speaking")
time.sleep(2.0)
faces.stop()
```

---

#### 3.6.7 `robot_sound.py`

**Module:** `ninja_core.robot_sound`

Emotional sound generation.

##### Class: `RobotSoundPlayer`

**Constructor:**
```python
def __init__(self, hal: HardwareAbstractionLayer)
```

**Attributes:**
- `buzzer` (MusicBuzzer): Reference to HAL's buzzer
- `SOUNDS` (dict): Mapping of emotion names to note sequences
- `NOTES` (dict): Note name to frequency mapping

**Available Sounds:**
- `"happy"` - Cheerful ascending melody
- `"sad"` - Descending sad tones
- `"excited"` - Fast upbeat melody
- `"scary"` - Spooky low tones
- `"thinking"` - Contemplative sequence
- `"speaking"` - Speech-like pattern
- `"error"` - Error beep
- `"success"` - Success chime

**Methods:**

**`play(emotion: str) -> None`**
- Plays sound sequence for given emotion
- **Blocking:** Yes (plays full sequence)

**Usage:**
```python
from ninja_core.robot_sound import RobotSoundPlayer

sound = RobotSoundPlayer(hal)

sound.play("happy")
sound.play("thinking")
```

---

#### 3.6.8 `perception.py`

**Module:** `ninja_core.perception`

Background distance monitoring.

##### Class: `DistanceMonitor`

**Constructor:**
```python
def __init__(self, hal: HardwareAbstractionLayer)
```

**Attributes:**
- `sensor` (VL53L0X): Reference to HAL's distance sensor
- `_thread` (Thread): Background polling thread
- `_latest_distance` (int): Most recent reading

**Methods:**

**`get_distance() -> int`**
- Single-shot distance measurement (blocking ~30ms)

**`start_continuous(interval: float = 0.2) -> None`**
- Starts background thread polling at specified interval
- **Parameters:**
  - `interval` (float): Polling interval in seconds

**`get_continuous_distance() -> int`**
- Returns latest distance from background thread (non-blocking)
- **Returns:** `0` if continuous mode not started

**`get_velocity() -> float`**
- Returns estimated approach velocity in mm/s
- **Returns:** Negative value = approaching, Positive = retreating

**`check_emergency_stop(distance_threshold: int = 100, velocity_threshold: float = -30.0, consecutive_frames: int = 5) -> bool`**
- Checks if startle/emergency condition is met.
- **Default Threshold**: 100mm (Distance), -30mm/s (Velocity).
- **Returns**: `True` if condition is met (caller determines action).

**`stop_continuous() -> None`**
- Stops background thread

**Usage:**
```python
from ninja_core.perception import DistanceMonitor

monitor = DistanceMonitor(hal)

# Background monitoring
monitor.start_continuous(interval=0.1)

while True:
    d = monitor.get_continuous_distance()
    print(f"Distance: {d}mm")
    time.sleep(0.5)

monitor.stop_continuous()
```

---

#### 3.6.9 `web_server.py`

**Module:** `ninja_core.web_server`

FastAPI web server with WebSocket and ngrok integration.

##### Data Models

**`SetApiKeyRequest`** (Pydantic BaseModel)
```python
class SetApiKeyRequest(BaseModel):
    api_key: str
```

**`AgentChatRequest`** (Pydantic BaseModel)
```python
class AgentChatRequest(BaseModel):
    message: str
```

##### Class: `AppState`

Global application state container.

**Attributes:**
- `hal` (HardwareAbstractionLayer | None)
- `agent` (NinjaAgent | None)
- `faces` (AnimatedFaces | None)
- `sound` (RobotSoundPlayer | None)
- `movement` (MovementController | None)
- `distance_monitor` (DistanceMonitor | None)
- `first_interaction` (bool): Whether first user request received
- `has_greeted` (bool): Whether welcome greeting played

##### Function: `lifespan(app: FastAPI)`

FastAPI lifespan context manager for startup/shutdown.

**Startup:**
1. Loads config
2. Initializes HAL
3. Attempts to initialize NinjaAgent (catches `MissingAPIKeyError`)
4. Initializes faces, sound, movement, distance monitor
5. Calls `setup_network_and_display(app)` for ngrok

**Shutdown:**
1. Stops all background threads (faces, distance monitor)
2. Shuts down HAL
3. Kills ngrok process

##### Function: `setup_network_and_display(app: FastAPI)`

Sets up ngrok tunnel and displays QR code.

##### Helper Functions

**`handle_first_interaction(app_state: AppState) -> None`**
- Clears QR code and shows idle face on first user request

**`trigger_welcome(app_state: AppState) -> None`**
- Plays happy face + sound for 3 seconds (called on web connect)

**`safety_check(app_state: AppState) -> bool`**
- Returns True if distance <= 50mm

**`execute_action_plan(app_state: AppState, action_plan: dict) -> None`**
- Executes AI agent's action plan (face, sound, movement)
- Runs face and sound in parallel threads
- Waits for movements to complete

##### API Endpoints

**`GET /`**
- Serves main HTML template

**`GET /api/agent/status`**
- Returns `{"active": bool}`

**`POST /api/agent/set_api_key`**
- Body: `SetApiKeyRequest`
- Sets Gemini API key and reinitializes agent

**`POST /api/agent/chat`**
- Body: `AgentChatRequest`
- Processes text chat message
- Returns `{"response": str, "logs": list}`

**`GET /api/movements`**
- Returns list of movement names

**`POST /api/movements/{name}`**
- Executes named movement with obstacle avoidance

**`GET /api/expressions`**
- Returns list of facial expressions

**`POST /api/expressions/{name}`**
- Shows facial expression

**`GET /api/sounds`**
- Returns list of sounds

**`POST /api/sounds/{name}`**
- Plays sound

**`GET /api/distance`**
- Returns current distance in mm

**`WebSocket /ws/distance`**
- Streams distance readings at 5Hz

##### Function: `run_server()`

Main entry point for server.

**Behavior:**
1. Prompts for ngrok authtoken (if not configured)
2. Starts uvicorn on `0.0.0.0:8000`

**Usage:**
```bash
uv run ninja_core server
```

---

#### 3.6.10 Frontend Files

**`templates/index.html`**
- Main web UI template (Jinja2)
- Includes chat interface, control panels, status displays

**`static/main.js`**
- Client-side JavaScript
- Features:
  - WebSocket distance monitoring
  - Web Speech API integration (voice input)
  - Language selector (EN/JP/ZH-TW/ZH-CN)
  - API calls for all robot functions

**`static/style.css`**
- UI styles

---

#### 3.6.10 CLI Commands

**Entry Point:** `uv run ninja_core <command>`

**Commands:**

**`server`**
- Starts the web server with ngrok
- **Example:** `uv run ninja_core server`

**`chat`**
- Interactive terminal chat with AI agent
- Includes obstacle avoidance monitoring
- **Example:** `uv run ninja_core chat`

**`movement-tool`**
- Interactive TUI for recording and editing movement sequences
- **Example:** `uv run ninja_core movement-tool`

**`config import-all`**
- Imports `servo.json` and `buzzer.json` into `config.json`
- **Example:** `uv run ninja_core config import-all`

**`config set-key <service> <key>`**
- Sets an API key
- **Example:** `uv run ninja_core config set-key gemini AIzaSy...`

---

#### 3.6.10 `safe_executor.py` (New Phase 4)

**Module:** `ninja_core.safe_executor`

**Purpose:** Provides a sandboxed environment for executing user-generated or AI-generated Python code safely.

##### Class: `SafeExecutor`

**Constructor:**
```python
def __init__(self, hal: HardwareAbstractionLayer, on_print: Callable[[str], None] = None)
```

**Parameters:**
- `hal`: Hardware Abstraction Layer for accessing `robot` API.
- `on_print`: Callback for capturing `print()` output (e.g., for broadcasting to WebSockets).

**Methods:**

**`execute(code: str, on_complete: Callable[[dict], None] = None) -> dict`**
- Executes Python code in a restricted sandbox.
- **Parameters:**
    - `code`: Python code string.
    - `on_complete`: Async callback fired when execution completes/fails.
- **Returns:** `{"status": "started" | "success" | "error" | "stopped", "message": str}`
- **Safety Features:**
    - Blocks: `os`, `sys`, `subprocess`, `open`, `eval`, `exec`, `__import__`.
    - Provides: `robot`, `time`, `math`, `print`, `check_stop()`.
    - Compiles code before starting the execution thread. Syntax failures return `error_code: "syntax_error"` and `syntax_error` details without calling hardware stop cleanup, because no user code has run yet.

**`stop() -> None`**
- Signals the current execution to stop.

**Usage:**
```python
from ninja_core.safe_executor import SafeExecutor

executor = SafeExecutor(hal, on_print=lambda msg: print(f"[LOG] {msg}"))
result = executor.execute("robot.buzzer.play('happy')")
```

---



#### 3.6.12 `api_wrappers.py` (New Phase 4)

**Module:** `ninja_core.api_wrappers`

**Purpose:** High-level Python API wrappers that simplify robot control for user-generated code. Exposed as `robot` in the SafeExecutor.

##### Class: `RobotWrapper`

**Constructor:**
```python
def __init__(self, hal: HardwareAbstractionLayer)
```

**Attributes:**
- `buzzer` (BuzzerWrapper): Sound control.
- `display` (DisplayWrapper): Screen control.
- `distance` (DistanceWrapper): Sensor reading.
- `servo` (ServoArrayWrapper): Direct servo access (indexable 0-7 or batch).

##### Class: `ServoArrayWrapper`

**Methods:**
- `__getitem__(index)`: Access individual servo (e.g., `robot.servo[0]`).
- `move_all(angles: list, duration: float)`: Move all 8 servos.
- `center()`: Reset all servos to 90°.

##### Class: `BuzzerWrapper`

**Methods:**
- `play(name: str)`: Plays a predefined sound. Valid: `happy`, `sad`, `exciting`, `angry`, `confusing`, etc.
- `tone(freq: int, duration: float)`: Plays raw frequency.

##### Class: `DisplayWrapper`

**Methods:**
- `image(name: str)`: Shows asset image. Valid: `star`, `heart`.
- `clear()`: Clears the display.

##### Class: `DistanceWrapper`

**Methods:**
- `read() -> int`: Returns distance in millimeters.

---

### 3.7 ninja_ble

**Purpose:** Bluetooth Low Energy GATT server for wireless control and AI chat. Enables direct, zero-network-setup communication with the robot.

#### 3.7.1 Architecture

```
┌─────────────────┐     JSON Command      ┌──────────────────┐
│  Mobile Device  │ ──────────────────▶   │  NinjaBLEService │
│  (nRF Connect)  │                       │  (GATT Server)   │
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

#### 3.7.2 BLE Service Specification

| Item | Value |
|---|---|
| **Service Name** | `NinjaRobot` |
| **Service UUID** | `00000001-710e-4a5b-8d75-3e5b444bc3cf` |
| **Transport Contract** | `blockly-v1` events over raw JSON for small payloads and BLE transport v2 chunking for large payloads |

**Characteristics:**
| Name | UUID | Properties | Description |
|---|---|---|---|
| Command | `00000002-710e-4a5b-8d75-3e5b444bc3cf` | Write, WriteWithoutResponse | Receives JSON commands or transport-v2 chunk packets |
| Response | `00000003-710e-4a5b-8d75-3e5b444bc3cf` | Read, Notify | Sends JSON responses and chunked runtime feedback |

#### 3.7.3 JSON Protocol

**Chat Command (AI Chat):**
```json
{"type": "chat", "text": "Tell me a joke"}
```

**Chat Response (AI Response):**
```json
{"type": "chat", "sender": "ninja", "text": "Why did the robot go on vacation?..."}
```

**HAL Command (Hardware Control):**
```json
{"type": "hal", "command": "execute", "payload": {"servos": {"angles": [0,0,0,0,0,0,0,0]}}}
{"type": "hal", "command": "execute", "payload": {"buzzer": {"frequency": 440, "duration": 0.5}}}
```

**Execute Command (Blockly IDE):**
```json
{
  "type": "execute",
  "request_id": "execute-123",
  "manifest": {
    "protocol_version": "blockly-v1",
    "generator_version": "web-blockly-v1",
    "workspace_format": "blockly-json"
  },
  "workspace_state": {"blocks": []},
  "code": "from ninja_core import robot\nrobot.expression('happy')\n"
}
```

**Stop Command:**
```json
{"type": "stop", "request_id": "stop-123", "reason": "user_stop"}
```

**ACK Envelope (Transport v2):**
```json
{"type": "ack", "transfer_id": 7, "phase": "data", "seq": 3, "status": "ok"}
```

**Runtime Event Types:**
- `execute_received`
- `execution_status`
- `execution_log`
- `chat`
- `error`

`error` events may include a `details` object. Blockly syntax errors use this to report `line`, `offset`, `text`, and `message` so the education IDE can display precise feedback.

#### 3.7.4 Key Classes

**`NinjaBLEService`** (`service.py`)
```python
class NinjaBLEService:
    def __init__(self, dispatcher: CommandDispatcher): ...
    async def start(self): ...          # Start GATT server & advertising
    async def stop(self): ...           # Stop server
    async def on_broadcast(self, message: dict): ...  # Send BLE notification
```

**Usage (from `web_server.py`):**
```python
from ninja_ble.service import NinjaBLEService
from ninja_core.dispatcher import CommandDispatcher

dispatcher = CommandDispatcher(hal)
ble_service = NinjaBLEService(dispatcher)
asyncio.create_task(ble_service.start())
```

#### 3.7.5 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `bless` | ≥0.2.6 | BLE GATT server |
| `bleak` | ≥0.21.0, <1.0.0 | BLE backend |
| `dbus-fast` | ≥1.86.0 | BlueZ D-Bus (Linux) |

#### 3.7.6 Testing with nRF Connect

1. Start server: `uv run ninja_core server`
2. Open nRF Connect → Scan → Connect to "NinjaRobot"
3. Subscribe to Response characteristic (`...0003`)
4. Write to Command characteristic (`...0002`):
   ```json
   {"type": "chat", "text": "Hello!"}
   ```
5. Verify notification received with AI response

---

## 4. Configuration System

### 4.1 Configuration Files

**`config.json`** (Main Config)
- **Location:** Project root
- **Format:** JSON
- **Managed by:** `ninja_core.config`
- **Contains:** All hardware settings, movements, API keys

**`servo.json`** (Servo Calibration)
- **Location:** Project root or `pi0servo/`
- **Format:** JSON array of servo objects
- **Managed by:** `pi0servo` calibration tool
- **Imported into:** `config.json` via `config import-all`

**`buzzer.json`** (Buzzer Configuration)
- **Location:** Project root (generated by `pi0buzzer init`)
- **Format:** `{"pin": <int>, "volume": <int 0-255>}`
- **Managed by:** `pi0buzzer init`, `pi0buzzer config`, `pi0buzzer buzzer-tool`
- **Imported into:** `config.json` via `config import-all`

### 4.2 Configuration Workflow

1. **Initial Setup:**
   ```bash
   uv run pi0buzzer init 26
   uv run pi0servo calib 17  # Repeat for all servos
   uv run ninja_core config import-all
   ```

2. **Set API Key:**
   ```bash
   uv run ninja_core config set-key gemini YOUR_KEY
   ```

3. **Verify:**
   ```bash
   cat config.json
   ```

### 4.3 Example `config.json`

```json
{
    "servos": {
        "pins": {},
        "calibration": {
            "17": {
                "min_pulse": 600,
                "center_pulse": 1500,
                "max_pulse": 2400,
                "angle_range": 180
            }
        }
    },
    "buzzer": {
        "pin": 26
    },
    "display": {
        "dc": 18,
        "rst": 19,
        "blk": 20
    },
    "sensors": {},
    "movements": {
        "wave": [
            {"moves": {"17": 45, "22": 0}, "speed": "M"},
            {"moves": {"17": -45, "22": 0}, "speed": "F"}
        ]
    },
    "api_keys": {
        "gemini": "AIzaSy..."
    }
}
```

---

## 5. Testing & Debugging

### 5.1 Hardware Tests

**Test Scripts (in project root):**
- `test_hal.py` - HAL initialization
- `test_perception.py` - Distance sensor
- `test_robot_sound.py` - Sound system
- `test_facial_expressions.py` - Display and facial expressions
- `verify_agent.py` - AI agent logic (no API key needed)

**Run Example:**
```bash
uv run python test_hal.py
```

### 5.2 Component Testing

**Individual Library Tests:**
```bash
# Buzzer
uv run pi0buzzer beep

# Distance Sensor
uv run pi0vl53l0x get --count 10 --interval 0.5

# Display
uv run pi0disp image assets/images/sample_face.jpg
uv run pi0disp demo --num-balls 3

# Servo
uv run pi0servo servo 17 center
```

### 5.3 Debug Mode

**Enable Logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check pigpiod:**
```bash
ps aux | grep pigpiod
sudo systemctl status pigpiod
```

**Check I2C:**
```bash
sudo i2cdetect -y 1
```

**Check SPI:**
```bash
ls /dev/spidev*
```

---

## 6. Contributing Guidelines

### 6.1 Code Style

- **Linter:** `ruff`
- **Format:** `ruff format`
- **Type Hints:** Required for public APIs
- **Docstrings:** Google style

### 6.2 Adding New Hardware

1. Create new library in project root (e.g., `pi0camera/`)
2. Follow existing library structure
3. Add to root `pyproject.toml` dependencies
4. Create HAL integration in `ninja_core/hal.py`
5. Add config model to `ninja_core/config.py`

### 6.3 Adding New Movements

Use the interactive tool:
```bash
uv run ninja_core movement-tool
```

Or manually edit `config.json`:
```json
{
    "movements": {
        "custom_move": [
            {"moves": {"17": 45, "22": -30}, "speed": "M"},
            {"moves": {"17": 0, "22": 0}, "speed": "S"}
        ]
    }
}
```

### 6.4 Pull Request Process

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Run linter: `uv run ruff check .`
5. Update `DevelopmentLog.md`
6. Submit PR with clear description

---

## 7. UI/UX Design Guidelines

### 7.1 Design Philosophy
**"Dark Modern Dashboard"**
The interface is designed to feel premium, futuristic, and highly responsive. It uses a deep dark mode palette with vibrant gradients for actions, soft shadows for depth, and a clean, grid-based layout that adapts seamlessly from mobile to desktop.

### 7.2 Color Palette

#### Backgrounds
| Token | Value | Usage |
| :--- | :--- | :--- |
| `--bg-app` | `#141414` | Main application background (Deep Black/Gray) |
| `--bg-surface` | `#1F2226` | Card and container background (Dark Blue-Gray) |
| `--bg-surface-hover` | `#282C31` | Hover state for interactive surfaces |
| `--bg-input` | `#121212` | Input fields and log background (Darker inset) |

#### Typography
| Token | Value | Usage |
| :--- | :--- | :--- |
| `--text-primary` | `#FFFFFF` | Main headings and body text |
| `--text-secondary` | `#8F95A3` | Subtitles, labels, and status text |
| `--text-disabled` | `#4A4F5A` | Disabled states and placeholders |

#### Accents & Status
| Token | Value | Usage |
| :--- | :--- | :--- |
| `--accent-primary` | `linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%)` | Primary action buttons (Orange/Red Gradient) |
| `--accent-glow` | `rgba(255, 107, 107, 0.4)` | Glow effects for primary actions |
| `--status-success` | `#4CD964` | Online status, success logs (Green) |
| `--status-warning` | `#FFCC00` | Warnings (Yellow) |
| `--status-error` | `#FF3B30` | Errors, Recording state, Power Off (Red) |

### 7.3 Typography
*   **Font Family**: `'Inter', 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif`
*   **Headings**:
    *   `h1`: 24px, Bold (700), Letter-spacing -0.5px.
    *   `h2`: 16px, Medium (500), Uppercase, Letter-spacing 1px, Color: Secondary.
*   **Body**: 14px-16px, Regular.
*   **Monospace**: `'Fira Code', monospace` (for System Log).

### 7.4 Layout System

#### Grid Structure
*   **Container**: `max-width: 1200px`, centered.
*   **Gap**: `24px`.

#### Responsive Behavior
*   **Mobile (< 768px)**:
    *   Single column (`1fr`).
    *   Stacked controls.
    *   Full-width buttons.
    *   Simplified padding (20px).
*   **Desktop (≥ 1024px)**:
    *   3-Column Grid.
    *   **Row 1**: Sensor | Servo | Expressions.
    *   **Row 2**: Sound | Agent (Spans 2 cols, 2 rows).
    *   **Row 3**: Log | System.

### 7.5 Component Library

#### Cards (`.control-section`)
*   **Background**: `--bg-surface`
*   **Border Radius**: `24px`
*   **Shadow**: `10px 10px 20px rgba(0,0,0,0.25), -5px -5px 15px rgba(255,255,255,0.02)`
*   **Border**: `1px solid rgba(255, 255, 255, 0.02)`
*   **Hover**: Slight lift (`translateY(-2px)`), increased shadow.

#### Buttons
*   **Primary**: Gradient background, white text, glow shadow.
*   **Shape**: Rounded (`border-radius: 16px`).
*   **Interaction**: Scale up on hover, scale down on click.

#### Inputs & Selects
*   **Background**: `--bg-input` (Darker than surface).
*   **Shadow**: Inner shadow (`inset 2px 2px 5px rgba(0,0,0,0.5)`).
*   **Border**: None (until focus).
*   **Focus**: Inner glow + Secondary color border.

#### Special Components

##### 1. Microphone Button
*   **Size**: Large (80px x 80px).
*   **Shape**: Circle.
*   **Position**: Centered below chat input.
*   **State - Idle**: Surface color, subtle border.
*   **State - Recording**: Red (`--status-error`), pulsing animation (`scale(1.1)`).

##### 2. Power Off Slider
*   **Concept**: "Slide to Unlock" style interaction to prevent accidental shutdowns.
*   **Track**: Dark inset path.
*   **Thumb**: White circular handle.
*   **Action**: Drag > 90% to trigger shutdown.

##### 3. Header
*   **Logo**: 50px height.
*   **Status**: Dot indicator (Green = Online).
*   **Language Selector**: Full-width on mobile, integrated into header.

### 7.6 Iconography
*   **Type**: SVG Icons.
*   **Style**: Minimalist, Filled or Stroked.
*   **Usage**: Mic icon, Power icon, Status dot.

---

## Appendix A: Pin Reference

| Component | Pin Type | Default GPIO |
|-----------|----------|--------------|
| Servo 1   | PWM      | 20           |
| Servo 2   | PWM      | 21           |
| Servo 3   | PWM      | 22           |
| Servo 4   | PWM      | 23           |
| Servo 5   | PWM      | 24           |
| Servo 6   | PWM      | 25           |
| Servo 7   | PWM      | 26           |
| Servo 8   | PWM      | 27           |
| Buzzer    | PWM      | 17           |
| Display DC | GPIO    | 14           |
| Display RST | GPIO   | 15           |
| Display BLK | PWM    | 26           |
| Display SCL | SPI    | 11 (SPI0 SCLK) |
| Display SDA | SPI    | 10 (SPI0 MOSI) |
| Sensor SCL | I2C     | 3 (I2C1 SCL) |
| Sensor SDA | I2C     | 2 (I2C1 SDA) |

---

## Appendix B: Common Issues

**Issue:** `Could not connect to pigpiod daemon`  
**Solution:** `sudo pigpiod`

**Issue:** `ImportError: No module named 'ninja_utils'`  
**Solution:** `uv pip install -e ./ninja_utils`

**Issue:** Display shows nothing  
**Solution:** Check SPI enabled in `raspi-config`

**Issue:** Distance sensor returns 8190  
**Solution:** Check I2C wiring and run `sudo i2cdetect -y 1`

---

**End of Development Guide**

For user-facing documentation, see [InstallationGuide.md](InstallationGuide.md) and [README.md](README.md).
