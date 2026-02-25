# pi0disp — ST7789V Display Driver

Thread-safe SPI driver for ST7789V-based displays with smart delta rendering and PWM brightness control.

## Features

- **Thread-safe SPI** — All SPI operations protected by `threading.Lock()`, safe for concurrent use with `AnimatedFaces` and `web_server.py`
- **Smart delta rendering** — Detects changed pixels via `PIL.ImageChops.difference()`, transmitting only the dirty region (~90% bandwidth savings for animations)
- **PWM brightness** — Smooth backlight control (0-100%) via `pigpio.set_PWM_dutycycle()`
- **Actuator ABC** — Implements `ninja_utils.Actuator` interface for seamless `ninja_core` HAL integration
- **Display profiles** — Pre-configured for ST7789V 2.8" IPS TFT and Waveshare 2.0" IPS LCD
- **Configuration Manager** — `display.json` with interactive setup wizard, CRUD operations, export/import
- **Multilingual text** — Scrolling marquee with bundled Noto fonts (English, Japanese, Traditional Chinese)
- **CLI tools** — 11 commands + interactive `display-tool` menu for standalone Raspberry Pi usage

## Supported Displays

| Display | Size | Resolution | Driver IC |
|---------|------|------------|-----------|
| ST7789V IPS TFT | 2.8 inch | 240×320 | ST7789V |
| Waveshare IPS LCD | 2.0 inch | 240×320 | ST7789V |

## Directory Structure

```
pi0disp/
├── pyproject.toml
├── README.md               ← This file
├── LICENSE                  # MIT License
├── tests/                   # Unit tests (54 tests, no hardware required)
│   ├── conftest.py          # Mock pigpio fixtures
│   ├── test_renderer.py     # ColorConverter, RegionOptimizer tests
│   ├── test_driver.py       # ST7789V driver tests (thread safety, delta rendering)
│   └── test_config.py       # ConfigManager tests
└── src/pi0disp/
    ├── __init__.py           # Exports: ST7789V, ConfigManager, TextTicker
    ├── __main__.py           # CLI entry point (click)
    ├── core/                 # Core driver modules
    │   ├── driver.py         # ST7789V driver (Actuator ABC)
    │   └── renderer.py       # ColorConverter (numpy LUT), RegionOptimizer
    ├── config/               # Configuration management
    │   └── config_manager.py # display.json CRUD + interactive wizard
    ├── effects/              # Visual effects
    │   └── text_ticker.py    # Scrolling marquee animation
    ├── fonts/                # Bundled multilingual fonts
    │   ├── NotoSans-Regular.ttf      # English
    │   ├── NotoSansJP-Regular.otf    # Japanese
    │   └── NotoSansTC-Regular.otf    # Traditional Chinese
    └── cli/                  # CLI subcommands
        ├── init_cmd.py       # First-time setup wizard
        ├── image_cmd.py      # Display image file
        ├── text_cmd.py       # Static/scrolling text
        ├── demo_cmd.py       # Bouncing ball animation
        ├── info_cmd.py       # Driver state + health check
        └── display_tool.py   # Interactive menu tool
```

---

## Installation (Raspberry Pi)

### Prerequisites

- **Raspberry Pi Zero 2W** (or compatible)
- **pigpiod** daemon running (`sudo pigpiod`)
- **SPI enabled** (`sudo raspi-config` → Interface Options → SPI)
- **uv** package manager

### Install

```bash
cd ~/NinjaRobotV5

# Method A: Install with all project packages (recommended)
uv sync

# Method B: Install pi0disp standalone
uv pip install -e ./pi0disp
```

### First-Time Setup

Run the interactive configuration wizard to set your GPIO pin assignments:

```bash
uv run pi0disp init
```

The wizard will guide you through:
1. **Display profile selection** (ST7789V 2.8" or Waveshare 2.0")
2. **DC pin** (default: GPIO 14)
3. **RST pin** (default: GPIO 15)
4. **Backlight pin** (default: GPIO 16)
5. **Rotation** (0°, 90°, 180°, 270°)
6. **Brightness** (0-100%)

This creates a `display.json` configuration file.

For non-interactive setup with defaults:
```bash
uv run pi0disp init --defaults
```

---

## CLI Commands

**Entry Point:** `uv run pi0disp <command>`

### Setup & Configuration

| Command | Description |
|---------|-------------|
| `pi0disp init` | Interactive display setup wizard |
| `pi0disp init --defaults` | Non-interactive setup with defaults |
| `pi0disp config show` | Show current configuration |
| `pi0disp config set <key> <value>` | Set a configuration value |
| `pi0disp config export <path>` | Export config to a file |
| `pi0disp config import <path>` | Import config from a file |
| `pi0disp info` | Show driver state, config, and health check |
| `pi0disp info --health-check` | Include hardware connectivity test |

### Display Operations

| Command | Description |
|---------|-------------|
| `pi0disp image <path>` | Display an image (auto-resized to fit) |
| `pi0disp text "Hello"` | Display static text |
| `pi0disp text "Hello" --scroll` | Scrolling marquee text |
| `pi0disp text "こんにちは" --lang ja` | Japanese text with Noto font |
| `pi0disp text "你好" --lang zh-tw` | Traditional Chinese text |
| `pi0disp demo` | Bouncing ball animation demo |
| `pi0disp demo --num-balls 5` | Demo with 5 balls |
| `pi0disp clear` | Clear display (fill black) |
| `pi0disp brightness <0-100>` | Set backlight brightness |
| `pi0disp display-tool` | Interactive menu (9 options) |

### Command Examples

```bash
# First-time setup
uv run pi0disp init

# Display an image file
uv run pi0disp image ~/photos/robot_face.png

# Show scrolling Japanese text
uv run pi0disp text "忍者ロボットへようこそ！" --lang ja --scroll --speed 3

# Run bouncing ball demo (3 balls, 10 seconds)
uv run pi0disp demo --num-balls 3 --duration 10

# Adjust brightness to 50%
uv run pi0disp brightness 50

# Check configuration and health
uv run pi0disp info --health-check

# Export config for backup
uv run pi0disp config export ~/display_backup.json

# Launch interactive menu
uv run pi0disp display-tool
```

---

## Python API

### ST7789V Driver

The main display driver class. Implements `ninja_utils.Actuator` ABC.

**Module:** `pi0disp.core.driver`

```python
import pigpio
from PIL import Image
from pi0disp import ST7789V

# Create pigpio connection
pi = pigpio.pi()

# Initialize display (with defaults or custom pins)
lcd = ST7789V(
    pi=pi,
    channel=0,          # SPI channel (0 or 1)
    dc_pin=14,          # Data/Command GPIO
    rst_pin=15,         # Reset GPIO
    backlight_pin=16,   # Backlight GPIO
    speed_hz=32_000_000,# SPI clock speed
    width=240,          # Display width
    height=320,         # Display height
    rotation=0,         # 0, 90, 180, or 270
)

# Display an image (auto-resized, delta rendering)
img = Image.open("robot_face.png").convert("RGB")
lcd.display(img)

# Set brightness (0-100%)
lcd.set_brightness(80)

# Clear display
lcd.clear()
lcd.clear(color=(255, 0, 0))  # Fill with red

# Display a sub-region
lcd.display_region(img, x0=0, y0=0, x1=120, y1=160)

# Change rotation
lcd.set_rotation(90)

# Power management
lcd.sleep()    # Enter low-power mode
lcd.wake()     # Exit low-power mode

# Health check
is_ok = lcd.health_check()

# Cleanup
lcd.close()
pi.stop()
```

**Context Manager:**
```python
with ST7789V(pi=pi) as lcd:
    lcd.display(Image.open("face.png").convert("RGB"))
    lcd.set_brightness(50)
# Automatically closed on exit
```

#### ST7789V Method Reference

| Method | Returns | Description |
|--------|---------|-------------|
| `display(image)` | `None` | Display image with smart delta rendering (thread-safe) |
| `display_region(image, x0, y0, x1, y1)` | `None` | Display a sub-region (thread-safe) |
| `clear(color=(0,0,0))` | `None` | Fill display with solid color |
| `set_brightness(percent)` | `None` | Set backlight PWM (0-100%) |
| `set_rotation(degrees)` | `None` | Set rotation (0, 90, 180, 270) |
| `sleep()` | `None` | Enter low-power sleep mode |
| `wake()` | `None` | Wake from sleep mode |
| `health_check()` | `bool` | Verify SPI connection is alive |
| `close()` | `None` | Release SPI handle, GPIO, and backlight |
| `initialize()` | `None` | Actuator ABC: wake display |
| `execute(command)` | `None` | Actuator ABC: dispatch command dict |
| `off()` | `None` | Actuator ABC: sleep + backlight off |

#### Actuator ABC Interface

For `ninja_core` HAL integration, the driver implements the `Actuator` ABC:

```python
# Via ninja_core HAL (e.g., from web_server.py or dispatcher.py)
lcd.execute({"image": my_pil_image})     # Display an image
lcd.execute({"brightness": 50})           # Set brightness
lcd.execute({"backlight": 80})            # Alias for brightness
lcd.execute({"clear": True})              # Clear display
lcd.execute({"rotation": 90})             # Set rotation
```

---

### ConfigManager

Manages display settings via a project-relative `display.json` file.

**Module:** `pi0disp.config.config_manager`

```python
from pi0disp import ConfigManager

cm = ConfigManager()            # Uses default display.json path
cfg = cm.load()                  # Load (or create defaults)
print(cfg["dc_pin"])             # → 14

cm.set("brightness", 80)        # Update a value
cm.save()                        # Persist to disk

cm.export_config("backup.json")  # Export to file
cm.import_config("backup.json")  # Import from file
```

#### ConfigManager Method Reference

| Method | Returns | Description |
|--------|---------|-------------|
| `load()` | `dict` | Load config from `display.json` (defaults if missing) |
| `save()` | `None` | Save current config to disk |
| `get(key, default)` | `Any` | Get a config value |
| `set(key, value)` | `None` | Set a value and save |
| `export_config(path)` | `None` | Export config to a file |
| `import_config(path)` | `dict` | Import config from a file |
| `init_config(interactive)` | `dict` | Interactive or default setup wizard |
| `config_path` | `str` | Property: path to `display.json` |

#### Default Configuration

```json
{
    "display_profile": "ST7789V 2.8-inch IPS TFT",
    "dc_pin": 14,
    "rst_pin": 15,
    "backlight_pin": 16,
    "width": 240,
    "height": 320,
    "rotation": 0,
    "brightness": 100,
    "spi_speed_mhz": 32
}
```

---

### TextTicker

Scrolling marquee text animation with multilingual font support.

**Module:** `pi0disp.effects.text_ticker`

```python
from pi0disp import ST7789V
from pi0disp.effects.text_ticker import TextTicker
import time

lcd = ST7789V(pi=pi)

# Create a ticker with Japanese text
ticker = TextTicker(
    lcd=lcd,
    text="忍者ロボットへようこそ！",
    font_size=32,
    color=(0, 255, 128),      # Green text
    bg_color=(0, 0, 0),       # Black background
    speed=2.0,                 # Pixels per frame
    language="ja",             # Use NotoSansJP font
)

# Start scrolling (runs in background thread)
ticker.start()

time.sleep(10)  # Let it scroll for 10 seconds

# Stop and cleanup
ticker.stop()
lcd.close()
```

#### TextTicker Method Reference

| Method | Returns | Description |
|--------|---------|-------------|
| `start()` | `None` | Start scrolling in a background thread (daemon) |
| `stop()` | `None` | Stop the animation and join the thread |
| `is_running()` | `bool` | Check if the ticker is currently animating |

#### Supported Languages

| Code | Font | Example |
|------|------|---------|
| `en` | NotoSans-Regular.ttf | Hello World |
| `ja` | NotoSansJP-Regular.otf | こんにちは |
| `zh-tw` | NotoSansTC-Regular.otf | 你好世界 |

---

### Renderer Utilities

Internal utilities for optimized display rendering.

**Module:** `pi0disp.core.renderer`

#### ColorConverter

Fast RGB → RGB565 color conversion using numpy lookup tables (LUT).

```python
from pi0disp.core.renderer import ColorConverter
import numpy as np

cc = ColorConverter()

# Convert an RGB image array to RGB565 bytes
rgb_array = np.array(image)  # shape: (height, width, 3)
pixel_bytes = cc.rgb_to_rgb565_bytes(rgb_array)
```

#### RegionOptimizer

Optimizes rectangular dirty regions for partial display updates.

```python
from pi0disp.core.renderer import RegionOptimizer

# Clamp a region to display boundaries
clamped = RegionOptimizer.clamp_region((−10, −5, 250, 350), width=240, height=320)
# → (0, 0, 240, 320)

# Merge overlapping/nearby regions to reduce SPI transfers
regions = [(0, 0, 50, 50), (45, 0, 100, 50), (200, 200, 240, 240)]
merged = RegionOptimizer.merge_regions(regions, max_regions=2)
```

---

## Raspberry Pi Testing Guide

Follow these steps to validate pi0disp on your Raspberry Pi:

### Step 1: Verify Prerequisites

```bash
# Ensure SPI is enabled
ls /dev/spidev0.0
# → Should show the device file

# Ensure pigpiod is running
pigs t
# → Should return a timestamp number

# Ensure pi0disp is installed
uv run pi0disp --help
# → Should show the list of commands
```

### Step 2: Initial Setup

```bash
uv run pi0disp init
```

Follow the prompts to select your display profile and configure GPIO pins.

### Step 3: Test Display

```bash
# Clear the screen (should turn off any previous content)
uv run pi0disp clear

# Display a test image
uv run pi0disp image assets/images/sample_face.jpg
```

You should see the image rendered on the display.

### Step 4: Test Brightness

```bash
# Set to 50%
uv run pi0disp brightness 50

# Set to 100% (full brightness)
uv run pi0disp brightness 100

# Set to 0% (backlight off)
uv run pi0disp brightness 0
```

### Step 5: Test Text Rendering

```bash
# Static English text
uv run pi0disp text "Hello NinjaRobot"

# Scrolling Japanese text
uv run pi0disp text "忍者ロボットへようこそ！" --lang ja --scroll

# Scrolling Chinese text
uv run pi0disp text "你好世界" --lang zh-tw --scroll --speed 3
```

### Step 6: Test Animation

```bash
# Run bouncing ball demo
uv run pi0disp demo --num-balls 3

# Press Ctrl+C to stop
```

### Step 7: Check Health & Configuration

```bash
# View current configuration
uv run pi0disp info --health-check

# Or check config only
uv run pi0disp config show
```

### Step 8: Test Interactive Menu

```bash
uv run pi0disp display-tool
```

Choose from 9 options to exercise all functionality interactively.

### Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| `Error: pigpio not available` | Not on Raspberry Pi or pigpiod not running | Run `sudo pigpiod` |
| `Error: Could not connect to pigpio daemon` | pigpiod crashed or not started | `sudo systemctl restart pigpiod` |
| Display shows nothing | Wrong SPI or GPIO pin config | Re-run `uv run pi0disp init` |
| Display garbled/inverted | Wrong rotation setting | `uv run pi0disp config set rotation 0` |
| `ModuleNotFoundError: pi0disp` | Package not installed | `cd ~/NinjaRobotV5 && uv sync` |
| White screen / no backlight | Backlight pin wrong | Check wiring, re-run `uv run pi0disp init` |

---

## Development (PC/Mac)

No hardware is required for development — all hardware calls are mocked in tests.

```bash
cd pi0disp

# Install dev dependencies
uv sync --group dev

# Run unit tests (54 tests, ~27 seconds)
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/

# Auto-fix lint errors
uv run ruff check src/ tests/ --fix
```

### Test Coverage

| Suite | Tests | Coverage |
|-------|-------|----------|
| `test_renderer.py` | 12 | ColorConverter (RGB565 accuracy for R/G/B/W/K), RegionOptimizer (clamp, merge, max_regions) |
| `test_driver.py` | 22 | Construction, delta rendering, brightness, rotation, Actuator ABC, power management, thread safety, context manager |
| `test_config.py` | 10 | Load/save, get/set, export/import, init_config, corrupted JSON, display profiles |
| **Total** | **54** | |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  CLI (__main__.py)               │
│  init │ image │ text │ demo │ info │ display-tool│
├───────────────────┬─────────────────────────────┤
│   ConfigManager   │       TextTicker            │
│ (config_manager)  │   (text_ticker.py)          │
├───────────────────┴─────────────────────────────┤
│               ST7789V Driver (driver.py)        │
│        Actuator ABC │ Thread-safe SPI Lock      │
│        Delta Render │ PWM Brightness            │
├─────────────────────────────────────────────────┤
│           Renderer (renderer.py)                │
│     ColorConverter (numpy LUT) │ RegionOptimizer│
├─────────────────────────────────────────────────┤
│            pigpio (SPI / GPIO / PWM)            │
└─────────────────────────────────────────────────┘
```

## License

MIT License — © 2025 Chihkuang Chang
