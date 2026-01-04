# NinjaRobot V5 Development Guide

**Version:** 5.1.0  
**Last Updated:** 2026-01-04  
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
| `pi0vl53l0x` | Added `get_data()` method, implements `Sensor` |
| `pi0disp` | Added `execute()` command API, implements `Actuator` |
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
| `ninja_core/ninja_coder.py` | **NEW** - AI Agent for code generation (Gemini 3 Flash) |
| `ninja_core/web_server.py` | Added `/api/code/*` endpoints for remote execution |

### Key Changes (Phase 5 - Web Interface):
| Component | Change |
|---|---|
| `ninja_webapp/` | **NEW** - React SPA (Vite + React 18 + react-router-dom) |
| `ninja_webapp/src/pages/Agent/` | Chat dialog, hardware controls, slidable log panel |
| `ninja_webapp/src/pages/Home/` | Hero image, power-off slider |
| `ninja_core/web_server.py` | SPA serving from `ninja_webapp/dist`, `/api/system/shutdown` |

### Required Setup:
```bash
uv run pi0buzzer init 17
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
├── pi0buzzer/                  # Buzzer control library
│   ├── pyproject.toml
│   ├── README.md
│   └── src/pi0buzzer/
│       ├── __init__.py
│       ├── __main__.py         # CLI entry point
│       └── driver.py           # Buzzer, MusicBuzzer (Actuator ABC)
│
├── pi0vl53l0x/                 # VL53L0X distance sensor library
│   ├── pyproject.toml
│   ├── README.md
│   └── src/pi0vl53l0x/
│       ├── __init__.py
│       ├── __main__.py         # CLI entry point
│       ├── constants.py        # Sensor register addresses
│       ├── driver.py           # VL53L0X (Sensor ABC)
│       └── config_manager.py   # Configuration I/O
│
├── pi0disp/                    # ST7789V display library
│   ├── pyproject.toml
│   ├── README.md
│   └── src/pi0disp/
│       ├── __init__.py
│       ├── __main__.py         # CLI entry point
│       ├── disp/st7789v.py     # ST7789V (Actuator ABC)
│       ├── fonts/              # Bundled Noto fonts
│       ├── utils/              # Image processing
│       └── commands/           # Demo commands
│
├── pi0servo/                   # Servo motor control library
│   ├── pyproject.toml
│   ├── README.md
│   └── src/pi0servo/
│       ├── __init__.py
│       ├── __main__.py         # CLI entry point
│       ├── core/               # PiServo, CalibrableServo, MultiServo
│       ├── helper/             # Thread workers
│       ├── utils/              # Config manager
│       └── command/            # CLI commands
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
        ├── ninja_coder.py      # AI Code Agent (V5 Phase 4)
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
    ├─→ pi0buzzer → pigpio, ninja_utils
    ├─→ pi0vl53l0x → ninja_utils
    ├─→ pi0disp → PIL, numpy, ninja_utils
    ├─→ pi0servo → pigpio, ninja_utils
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
git clone https://github.com/Nilcreator/NinjaRobotV4.git
cd NinjaRobotV4

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

**Purpose:** Control a passive buzzer for sound and music generation

**Dependencies:** `pigpio`, `click`

**Location:** `pi0buzzer/src/pi0buzzer/`

**Hardware Interface:** GPIO PWM

#### 3.2.1 `driver.py`

**Module:** `pi0buzzer.driver`

##### Class: `Buzzer`

Base class for buzzer control.

**Constructor:**
```python
def __init__(self, pi: pigpio.pi, pin: int)
```

**Parameters:**
- `pi` (pigpio.pi): Shared pigpio connection
- `pin` (int): GPIO pin number

**Methods:**

**`play_sound(frequency: int, duration: float) -> None`**
- Plays a tone at the specified frequency for the given duration
- **Parameters:**
  - `frequency` (int): Tone frequency in Hz (50-10000)
  - `duration` (float): Duration in seconds
- **Blocking:** Yes (sleeps for duration)

**`off() -> None`**
- Stops the buzzer immediately

**Usage:**
```python
import pigpio
from pi0buzzer.driver import Buzzer

pi = pigpio.pi()
buzzer = Buzzer(pi, pin=17)

buzzer.play_sound(440, 0.5)  # A4 note for 0.5 seconds
buzzer.off()
pi.stop()
```

---

##### Class: `MusicBuzzer`

Extends `Buzzer` with melody playback capabilities.

**Constructor:**
```python
def __init__(self, pi: pigpio.pi, pin: int)
```

**Inherits:** `Buzzer`

**Methods:**

**`play_song(song: list[tuple[int, float]]) -> None`**
- Plays a sequence of notes
- **Parameters:**
  - `song` (list): List of (frequency, duration) tuples
- **Blocking:** Yes

**Usage:**
```python
from pi0buzzer.driver import MusicBuzzer

buzzer = MusicBuzzer(pi, pin=17)

# Define a melody
melody = [
    (262, 0.25),  # C4
    (294, 0.25),  # D4
    (330, 0.25),  # E4
    (262, 0.5),   # C4 (longer)
]

buzzer.play_song(melody)
```

**Pre-defined Songs:** See `pi0buzzer/__main__.py` for built-in melodies

---

#### 3.2.2 CLI Commands

**Entry Point:** `uv run pi0buzzer <command>`

**Commands:**

**`init <pin>`**
- Creates `buzzer.json` with the specified GPIO pin
- **Example:** `uv run pi0buzzer init 17`

**`beep`**
- Plays a short test beep
- **Example:** `uv run pi0buzzer beep`

**`playmusic`**
- Plays a pre-defined melody
- **Example:** `uv run pi0buzzer playmusic`

---

### 3.3 pi0vl53l0x

**Purpose:** Driver for VL53L0X Time-of-Flight distance sensor

**Dependencies:** `pigpio`, `numpy`, `click`, `ninja_utils`

**Location:** `pi0vl53l0x/src/pi0vl53l0x/`

**Hardware Interface:** I2C (default address: 0x29)

#### 3.3.1 `constants.py`

**Module:** `pi0vl53l0x.constants`

Contains all register addresses and configuration constants for the VL53L0X sensor.

**Key Constants:**
- `VL53L0X_REG_SYSRANGE_START = 0x00`
- `VL53L0X_REG_RESULT_RANGE_STATUS = 0x14`
- `DEVICE_ADDRESS = 0x29`

**Refer to this module** when working with low-level sensor operations.

---

#### 3.3.2 `driver.py`

**Module:** `pi0vl53l0x.driver`

##### Class: `VL53L0X`

Main driver for the VL53L0X distance sensor.

**Constructor:**
```python
def __init__(self, pi: pigpio.pi, address: int = 0x29)
```

**Parameters:**
- `pi` (pigpio.pi): Shared pigpio connection
- `address` (int): I2C address (default: 0x29)

**Methods:**

**`initialize() -> None`**
- Performs sensor initialization sequence
- **Must be called** after construction before taking measurements
- **Raises:** `RuntimeError` if sensor not detected

**`get_range() -> int`**
- Takes a single distance measurement
- **Returns:** Distance in millimeters (30-2000mm typical range)
- **Returns:** `8190` if out of range or error
- **Blocking:** ~30ms per reading

**`set_offset(offset_mm: int) -> None`**
- Sets calibration offset
- **Parameters:**
  - `offset_mm` (int): Offset value in mm (-127 to +127)

**`calibrate(true_distance_mm: int, num_samples: int = 10) -> int`**
- Calculates required offset for accurate readings
- **Parameters:**
  - `true_distance_mm` (int): Known actual distance in mm
  - `num_samples` (int): Number of samples to average
- **Returns:** Calculated offset value
- **Side Effect:** Automatically applies the offset via `set_offset()`

**`close() -> None`**
- Cleanup method (currently a no-op, for future use)

**Low-Level I2C Methods:**
- `read_byte(reg: int) -> int`
- `write_byte(reg: int, value: int) -> None`
- `read_word(reg: int) -> int`
- `write_word(reg: int, value: int) -> None`

**Usage:**
```python
import pigpio
from pi0vl53l0x.driver import VL53L0X

pi = pigpio.pi()
sensor = VL53L0X(pi)
sensor.initialize()

# Take 10 readings
for _ in range(10):
    distance = sensor.get_range()
    print(f"Distance: {distance}mm")

# Calibrate with object at 100mm
offset = sensor.calibrate(true_distance_mm=100)
print(f"Calibrated with offset: {offset}mm")

sensor.close()
pi.stop()
```

---

#### 3.3.3 `config_manager.py`

**Module:** `pi0vl53l0x.config_manager`

##### Function: `load_config(path: str = "sensor_config.json") -> dict`

Loads sensor configuration from JSON file.

**Returns:** `{"offset": int}` or `{}`

##### Function: `save_config(config: dict, path: str = "sensor_config.json") -> None`

Saves sensor configuration to JSON file.

---

#### 3.3.4 CLI Commands

**Entry Point:** `uv run pi0vl53l0x <command>`

**Commands:**

**`get --count N --interval T`**
- Takes N distance readings at T second intervals
- **Example:** `uv run pi0vl53l0x get --count 10 --interval 1.0`

**`performance --count N`**
- Measures sensor sampling rate
- **Example:** `uv run pi0vl53l0x performance --count 100`

**`calibrate --distance D`**
- Interactive calibration tool
- **Example:** `uv run pi0vl53l0x calibrate --distance 100`

---

### 3.4 pi0disp

**Purpose:** High-performance driver for ST7789V 240x240 SPI display

**Dependencies:** `pigpio`, `numpy`, `Pillow`, `click`, `ninja_utils`

**Location:** `pi0disp/src/pi0disp/`

**Hardware Interface:** SPI0 (SCLK, MOSI) + GPIO (DC, RST, BLK)

#### 3.4.1 `disp/st7789v.py`

**Module:** `pi0disp.disp.st7789v`

##### Class: `ST7789V`

Main display driver class.

**Constructor:**
```python
def __init__(
    self,
    pi: pigpio.pi,
    channel: int = 0,
    dc_pin: int = 14,
    rst_pin: int = 15,
    backlight_pin: int = 16,
    width: int = 240,
    height: int = 240
)
```

**Parameters:**
- `pi` (pigpio.pi): Shared pigpio connection
- `channel` (int): SPI channel (0 or 1)
- `dc_pin` (int): Data/Command GPIO pin
- `rst_pin` (int): Reset GPIO pin
- `backlight_pin` (int): Backlight GPIO pin
- `width`, `height` (int): Display dimensions

**Methods:**

**`display(image: PIL.Image.Image) -> None`**
- Displays a full-screen image
- **Parameters:**
  - `image` (PIL.Image): RGB image (will be resized to 240x240)
- **Performance:** ~50ms for full update at 40MHz SPI

**`display_region(image: PIL.Image.Image, x: int, y: int, width: int, height: int) -> None`**
- Updates a rectangular region (for animations)
- **Parameters:**
  - `image` (PIL.Image): Source image
  - `x`, `y` (int): Top-left corner
  - `width`, `height` (int): Region size

**`close() -> None`**
- Turns off backlight and releases GPIO

**Usage:**
```python
import pigpio
from PIL import Image
from pi0disp.disp.st7789v import ST7789V

pi = pigpio.pi()
display = ST7789V(pi, channel=0, dc_pin=14, rst_pin=15, backlight_pin=16)

# Display an image
img = Image.open("face.jpg")
display.display(img)

# Cleanup
display.close()
pi.stop()
```

---

#### 3.4.2 `utils/performance_core.py`

**Module:** `pi0disp.utils.performance_core`

Contains optimization classes for high-performance rendering:

##### Class: `MemoryPool`
- Manages reusable memory buffers to reduce allocations

##### Class: `LookupTableCache`
- Caches color conversion and gamma correction lookup tables

##### Class: `RegionOptimizer`
- Merges overlapping dirty regions for efficient updates

##### Class: `PerformanceMonitor`
- Tracks FPS and frame times

##### Class: `AdaptiveChunking`
- Dynamically adjusts SPI transfer chunk sizes

##### Class: `ColorConverter`
- Fast RGB565 conversion

**Usage:** These are primarily internal utility classes used by `ST7789V`.

---

#### 3.4.3 `utils/image_processor.py`

**Module:** `pi0disp.utils.image_processor`

##### Class: `ImageProcessor`

Static utility methods for image manipulation.

**Methods:**

**`resize_with_aspect_ratio(image: PIL.Image.Image, target_size: tuple[int, int]) -> PIL.Image.Image`**
- Resizes image maintaining aspect ratio
- Centers on black background if needed

**`apply_gamma(image: PIL.Image.Image, gamma: float) -> PIL.Image.Image`**
- Applies gamma correction
- **Parameters:**
  - `gamma` (float): Gamma value (0.5-2.0, default 1.0 = no change)

**Usage:**
```python
from PIL import Image
from pi0disp.utils.image_processor import ImageProcessor

img = Image.open("photo.jpg")
img = ImageProcessor.resize_with_aspect_ratio(img, (240, 240))
img = ImageProcessor.apply_gamma(img, 1.5)  # Brighten
```

---

#### 3.4.4 CLI Commands

**Entry Point:** `uv run pi0disp <command>`

**Commands:**

**`image <path>`**
- Displays an image with gamma cycling
- **Example:** `uv run pi0disp image assets/images/sample_face.jpg`

**`ball_anime --num-balls N`**
- Runs a physics-based bouncing ball animation
- **Example:** `uv run pi0disp ball_anime --num-balls 5`

---

### 3.5 pi0servo

**Purpose:** Multi-servo control with calibration and interpolation

**Dependencies:** `pigpio`, `click`, `blessed`, `ninja_utils`

**Location:** `pi0servo/src/pi0servo/`

**Hardware Interface:** GPIO PWM (500-2500μs pulse width)

#### 3.5.1 `core/piservo.py`

**Module:** `pi0servo.core.piservo`

##### Class: `PiServo`

Base servo control class.

**Constructor:**
```python
def __init__(
    self,
    pi: pigpio.pi,
    pin: int,
    min_pulse: int = 500,
    max_pulse: int = 2500,
    angle_range: int = 180
)
```

**Parameters:**
- `pi` (pigpio.pi): Shared pigpio connection
- `pin` (int): GPIO pin number
- `min_pulse`, `max_pulse` (int): Pulse width in microseconds
- `angle_range` (int): Total rotation range in degrees

**Methods:**

**`set_angle(angle: float) -> None`**
- Moves servo to specified angle
- **Parameters:**
  - `angle` (float): Target angle (-90 to +90 for 180° servo)

**`get_angle() -> float`**
- Returns current servo angle

**`off() -> None`**
- Stops PWM signal (servo relaxes)

**Usage:**
```python
import pigpio
from pi0servo.core.piservo import PiServo

pi = pigpio.pi()
servo = PiServo(pi, pin=20)

servo.set_angle(0)    # Center
servo.set_angle(45)   # Right
servo.set_angle(-45)  # Left
servo.off()

pi.stop()
```

---

#### 3.5.2 `core/calibrable_servo.py`

**Module:** `pi0servo.core.calibrable_servo`

##### Class: `CalibrableServo`

Extends `PiServo` with calibration data support.

**Constructor:**
```python
def __init__(
    self,
    pi: pigpio.pi,
    pin: int,
    calib_data: dict | None = None
)
```

**Parameters:**
- `pi` (pigpio.pi): Shared pigpio connection
- `pin` (int): GPIO pin number
- `calib_data` (dict): Calibration dict with keys: `min_pulse`, `center_pulse`, `max_pulse`, `angle_range`

**Additional Methods:**

**`set_calibration(calib_data: dict) -> None`**
- Updates calibration parameters

**`get_calibration() -> dict`**
- Returns current calibration data

---

#### 3.5.3 `core/multi_servo.py`

**Module:** `pi0servo.core.multi_servo`

##### Class: `MultiServo`

Controls multiple servos simultaneously.

**Constructor:**
```python
def __init__(
    self,
    pi: pigpio.pi,
    pins: list[int],
    conf_file: str = "servo.json"
)
```

**Parameters:**
- `pi` (pigpio.pi): Shared pigpio connection
- `pins` (list[int]): List of GPIO pin numbers
- `conf_file` (str): Path to calibration JSON file

**Methods:**

**`move_all_angles(angles: list[float]) -> None`**
- Moves all servos to specified angles
- **Parameters:**
  - `angles` (list[float]): Angles for each servo (same order as `pins`)

**`get_all_angles() -> list[float]`**
- Returns current angles for all servos

**`move_all_angles_sync(angles: list[float], duration: float = 0.5) -> None`**
- Smoothly interpolates all servos to target angles over duration
- **Parameters:**
  - `angles` (list[float]): Target angles
  - `duration` (float): Movement duration in seconds

**`off() -> None`**
- Turns off all servos

**Usage:**
```python
import pigpio
from pi0servo.core.multi_servo import MultiServo

pi = pigpio.pi()
multi = MultiServo(pi, pins=[20, 21, 22], conf_file="servo.json")

# Move all servos instantly
multi.move_all_angles([0, 45, -30])

# Smooth synchronized movement
multi.move_all_angles_sync([90, 0, -45], duration=1.0)

multi.off()
pi.stop()
```

---

#### 3.5.4 `helper/thread_multi_servo.py`

**Module:** `pi0servo.helper.thread_multi_servo`

##### Class: `ThreadMultiServo`

Thread-safe asynchronous wrapper around `MultiServo`.

**Constructor:**
```python
def __init__(
    self,
    pi: pigpio.pi,
    pins: list[int],
    conf_file: str = "servo.json"
)
```

**Methods:**

**`move_all_angles_async(angles: list[float]) -> None`**
- Queues a movement command (non-blocking)

**`stop_thread() -> None`**
- Stops the worker thread (must be called before program exit)

**Usage:**
```python
from pi0servo.helper.thread_multi_servo import ThreadMultiServo

multi = ThreadMultiServo(pi, pins=[20, 21, 22])

# Non-blocking movement
multi.move_all_angles_async([0, 45, -30])
# Program continues immediately

multi.stop_thread()
```

---

#### 3.5.5 CLI Commands

**Entry Point:** `uv run pi0servo <command>`

**Commands:**

**`servo <pin> <angle|min|center|max>`**
- Moves a single servo
- **Example:** `uv run pi0servo servo 20 center`
- **Example:** `uv run pi0servo servo 20 45`

**`calib <pin>`**
- Interactive TUI calibration tool
- **Keybindings:**
  - `v`, `c`, `x` - Select Min/Center/Max target
  - `Up`/`Down` - Large adjustments (±10μs)
  - `w`/`s` - Fine adjustments (±1μs)
  - `Enter`/`Space` - Save current position
  - `q` - Quit and save to `servo.json`

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

**Purpose:** The central nervous system for routing commands from multiple sources (Web, BLE) to appropriate handlers (HAL, Agent).

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
3. **`execute`** -> Code execution (Phase 4 SafeExecutor). Currently logs code and returns pending status.
4. **`ping`** -> Returns pong.

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
- **Returns:** `{"status": "running" | "success" | "error", "message": str}`
- **Safety Features:**
    - Blocks: `os`, `sys`, `subprocess`, `open`, `eval`, `exec`, `__import__`.
    - Provides: `robot`, `time`, `math`, `print`, `check_stop()`.

**`stop() -> None`**
- Signals the current execution to stop.

**Usage:**
```python
from ninja_core.safe_executor import SafeExecutor

executor = SafeExecutor(hal, on_print=lambda msg: print(f"[LOG] {msg}"))
result = executor.execute("robot.buzzer.play('happy')")
```

---

#### 3.6.11 `ninja_coder.py` (New Phase 4)

**Module:** `ninja_core.ninja_coder`

**Purpose:** AI-powered code generation, translation, and debugging agent. Uses `gemini-3-flash-preview` for fast coding tasks.

##### Class: `NinjaCoderAgent`

**Constructor:**
```python
def __init__(self, config: NinjaConfig)
```

**Methods:**

**`async translate_code(code: str) -> str`**
- Rewrites user code to match the V5 Robot API.
- **Use Case:** Converts `robot.buzzer.play("startup")` → tone sequence.
- **Returns:** Translated Python code string.

**`async generate_code(query: str) -> str`**
- Generates Python code from natural language description.
- **Returns:** Generated Python code string.

**`async analyze_code(code: str) -> str`**
- Analyzes code for bugs and improvements.
- **Returns:** Human-readable analysis text.

**`async analyze_error(code: str, error_msg: str) -> str`**
- Explains an execution error and suggests a fix.
- **Returns:** Diagnostic text with corrected code.

**Sound Mapping (built into system prompt):**
| Invalid Input | Translated Output |
|---------------|-------------------|
| `"startup"` | Tone sequence (C5→E5→G5) |
| `"success"` | `play("happy")` |
| `"error"` | `play("sad")` |
| `"alert"` | `play("scary")` |

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
- `servo` (MultiServo): Direct servo access.

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

**Characteristics:**
| Name | UUID | Properties | Description |
|---|---|---|---|
| Command | `00000002-710e-4a5b-8d75-3e5b444bc3cf` | Write, WriteWithoutResponse | Receives JSON commands |
| Response | `00000003-710e-4a5b-8d75-3e5b444bc3cf` | Read, Notify | Sends JSON responses (AI, status) |

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

**`buzzer.json`** (Buzzer Pin)
- **Location:** Project root or `pi0buzzer/`
- **Format:** `{"pin": <int>}`
- **Managed by:** `pi0buzzer init`
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
| Servo 1   | PWM      | 5            |
| Servo 2   | PWM      | 17           |
| Servo 3   | PWM      | 21           |
| Servo 4   | PWM      | 22           |
| Servo 5   | PWM      | 23           |
| Servo 6   | PWM      | 24           |
| Servo 7   | PWM      | 25           |
| Servo 8   | PWM      | 27           |
| Buzzer    | PWM      | 26           |
| Display DC | GPIO    | 18           |
| Display RST | GPIO   | 19           |
| Display BLK | PWM    | 20           |
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
