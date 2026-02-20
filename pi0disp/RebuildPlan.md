# pi0disp Library V2 — Complete Rebuild Plan

**Document Version:** 2.0  
**Date Created:** 2026-02-06  
**Last Refined:** 2026-02-20  
**Status:** Ready for Implementation  
**Approach:** Full rewrite from scratch (old code backed up to `pi0disp_bak/`)

---

## Table of Contents

1. [Analysis of the Old Library](#1-analysis-of-the-old-library-pi0disp_bak)
2. [Vulnerability Deep Dive](#2-vulnerability-deep-dive)
3. [New Architecture](#3-new-architecture)
4. [Public API Specification](#4-public-api-specification)
5. [Smart Delta Rendering](#5-smart-delta-rendering)
6. [PWM Brightness Control](#6-pwm-brightness-control)
7. [Multi-Display Support](#7-multi-display-support)
8. [Effects Module](#8-effects-module)
9. [Config Manager](#9-config-manager)
10. [CLI Commands](#10-cli-commands)
11. [Backward Compatibility](#11-backward-compatibility)
12. [Implementation Phases](#12-implementation-phases)
13. [Testing & Verification](#13-testing--verification)
14. [Appendix A: File Inventory](#appendix-a-file-inventory)
15. [Appendix B: Related Documents](#appendix-b-related-documents)

---

## 1. Analysis of the Old Library (`pi0disp_bak`)

### 1.1 File Structure & Summary

```
pi0disp_bak/src/pi0disp/        ~1,800 lines total
├── __init__.py                  # Empty
├── __main__.py                  # Click CLI group (ball_anime, image)
├── disp/
│   ├── __init__.py              # Empty
│   └── st7789v.py               # 312 lines — Core SPI driver (Actuator ABC)
├── utils/
│   ├── __init__.py              # Empty
│   ├── performance_core.py      # 446 lines — MemoryPool, LUT, RegionOptimizer, etc.
│   └── image_processor.py       # ~80 lines — ImageProcessor (resize, gamma)
├── commands/
│   ├── __init__.py              # Empty
│   ├── ball_anime.py            # 531 lines — Physics bouncing ball demo
│   └── image.py                 # ~50 lines — Image display + gamma cycling
└── fonts/                       # Font resources
    ├── NotoSans-Regular.ttf
    ├── NotoSansJP-Regular.otf
    └── NotoSansTC-Regular.otf
```

### 1.2 Core Execution Flow

When ninja_core calls `lcd.display(image)`:
1. A new PIL `Image` is sized to (width × height)
2. The **entire** image is converted to a numpy array
3. LookupTable-based RGB → RGB565 conversion (~153 KB for 240×320)
4. The **entire** RGB565 buffer is blasted across SPI in chunks
5. Adaptive chunking adjusts SPI transfer sizes dynamically

### 1.3 Integration Points in ninja_core

The old driver is consumed by **5 modules** in ninja_core:

| Module | How It Uses the Display |
|--------|------------------------|
| `hal.py` | Constructs `ST7789V(pi, channel, dc_pin, rst_pin, backlight_pin)`, calls `off()`, `close()` |
| `facial_expressions.py` | Calls `lcd.display(image)` in a **background thread** at ~60 FPS |
| `dispatcher.py` | Calls `display.execute({"image": img})` via Actuator ABC |
| `api_wrappers.py` | `DisplayWrapper.image(name)` → `execute({"image": img})`, `.clear()` |
| `web_server.py` | Calls `display.display(qr)` for QR code, accesses `.width` / `.height` |

### 1.4 ninja_core Config Model

```python
# ninja_core/src/ninja_core/config.py
class DisplayConfig(BaseModel):
    dc: Optional[int] = Field(14, description="The DC pin.")
    rst: Optional[int] = Field(15, description="The RST pin.")
    blk: Optional[int] = Field(16, description="The BLK pin.")
```

---

## 2. Vulnerability Deep Dive

> **Summary:** 6 vulnerabilities identified across the old library

### V1 — 🔴 CRITICAL: No Thread Safety (SPI Race Condition)

| Severity | Location | Impact |
|----------|----------|--------|
| **CRITICAL** | `st7789v.py` — all SPI methods | Display corruption, SPI bus errors |

**Root Cause:** `AnimatedFaces._animation_loop()` runs `lcd.display(image)` in a **background thread** at ~60 FPS. Simultaneously, `web_server.py` calls `display.display(qr)` from the asyncio/main thread, and `dispatcher.py` calls `display.execute()` from WebSocket handlers.

There is **no locking mechanism** on SPI writes. Concurrent `pi.spi_write()` calls will interleave bytes, corrupting the display data and potentially crashing the SPI bus.

**Fix:** Add a `threading.Lock()` protecting all SPI operations (`_write_command`, `_write_data`, `write_pixels`, `display`, `display_region`).

---

### V2 — 🔴 CRITICAL: Full-Frame SPI Bottleneck

| Severity | Location | Impact |
|----------|----------|--------|
| **CRITICAL** | `st7789v.display()` | ~115 KB per frame at 60 FPS = 6.9 MB/s SPI traffic |

**Root Cause:** `display()` has no internal state tracking. Even if only the eyes blink (< 5% of pixels change), the entire 240×320×2 = 153,600 bytes are transmitted.

**Impact:** Blocking `spi_write` stalls the Python GIL, preventing `asyncio` from polling sensors in real-time.

**Fix:** Implement Smart Delta Rendering. Cache the previous frame, use `PIL.ImageChops.difference()` to find the changed bounding box, and only transmit the changed region via `_write_partial_frame()`.

---

### V3 — 🟡 MEDIUM: GC Stutter from Object Instantiation

| Severity | Location | Impact |
|----------|----------|--------|
| **MEDIUM** | `facial_expressions.py:_animation_loop()` | Visible frame stutters |

**Root Cause:** Every frame creates a new `PIL.Image` + `ImageDraw` object, then discards them. Rapid allocation/deallocation saturates RAM and triggers Python's Garbage Collector, causing visible pauses.

**Fix:** Provide a `get_canvas()` → pre-allocated Image + Draw pair that can be cleared and reused. (This is primarily a ninja_core concern, but the driver should support efficient partial updates.)

---

### V4 — 🟡 MEDIUM: No Backlight Brightness Control

| Severity | Location | Impact |
|----------|----------|--------|
| **MEDIUM** | `st7789v.py:__init__()` | Backlight is only ON/OFF (digital) |

**Root Cause:** Backlight pin is controlled via `pi.write(pin, 0/1)` — digital toggle only. No PWM support means no brightness adjustment.

**Fix:** Use `pi.set_PWM_dutycycle(backlight_pin, value)` for 0-100% brightness control. Default to 100% at startup.

---

### V5 — 🟢 LOW: Over-Engineered Utility Layer

| Severity | Location | Impact |
|----------|----------|--------|
| **LOW** | `performance_core.py` (446 lines) | Unnecessary complexity |

**Details:** `MemoryPool` is never effectively used (the rendering loop creates new PIL objects anyway). `AdaptiveChunking` adds complexity but marginal benefit since SPI burst size is dictated by the `pigpio` daemon's internal buffer.

**Fix:** Retain only `ColorConverter` (RGB565 conversion via LUT) and `RegionOptimizer` (dirty-rect merging). Remove `MemoryPool`, `PerformanceMonitor`, and `AdaptiveChunking`.

---

### V6 — 🟢 LOW: No Error Recovery on SPI Failure

| Severity | Location | Impact |
|----------|----------|--------|
| **LOW** | `st7789v.py:_write_command()`, `_write_data()` | Uncaught SPI errors crash the driver |

**Fix:** Wrap SPI write calls in try/except, log errors gracefully. Add `health_check()` method.

---

## 3. New Architecture

### 3.1 Development Directive

**MANDATORY**: Build the new `pi0disp` library from scratch. You may reference the old `pi0disp_bak` for:
- SPI command constants (`CMD_SWRESET`, `CMD_MADCTL`, etc.)
- MADCTL rotation values (`{0: 0x00, 90: 0x60, 180: 0xC0, 270: 0xA0}`)
- RGB565 LookupTable conversion logic

**Do NOT copy-paste legacy driver code.**

### 3.2 File Structure

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
│   │   ├── __init__.py
│   │   ├── driver.py              # ST7789V class (Actuator ABC, thread-safe SPI)
│   │   └── renderer.py            # ColorConverter (RGB565 LUT), RegionOptimizer
│   │
│   ├── effects/
│   │   ├── __init__.py
│   │   └── text_ticker.py         # Scrolling text / marquee animation
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── config_manager.py      # Pin config persistence (display.json)
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── display_tool.py        # Interactive display tool (menu)
│   │   ├── init_cmd.py            # Init / first-time setup wizard
│   │   ├── image_cmd.py           # Image display command
│   │   ├── text_cmd.py            # Text display / scroll command
│   │   ├── demo_cmd.py            # Ball animation demo
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

### 3.3 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| RGB565 conversion | numpy LUT (keep numpy) | 60 FPS facial animation performance |
| Thread safety | `threading.Lock()` in driver | SPI concurrent access from AnimatedFaces + web_server |
| Delta rendering | `PIL.ImageChops.difference()` + bbox | Reduce SPI traffic by ~90% for facial animations |
| Backlight | PWM brightness (0-100%) via pigpio | User-adjustable brightness |
| Fonts | Bundled multilingual (EN/JA/ZH-TW) | Standalone text display without external deps |
| Display support | ST7789V 2.8" (240×320) + Waveshare 2.0" (240×320) | Both displays use same resolution |
| pigpio | **Optional** dependency (RPi-only) | Not installable on PC/Mac |
| Config | Project-relative `display.json` | Matches pi0servo/pi0vl53l0x pattern |
| SPI chunk size | Fixed 4096 bytes | Simpler than adaptive; pigpio daemon handles buffering |
| Previous frame cache | `Image.copy()` stored in driver | Enables automatic delta rendering |

---

## 4. Public API Specification

### 4.1 ST7789V Class

```python
from ninja_utils import Actuator

class ST7789V(Actuator):
    """Thread-safe SPI driver for ST7789V displays with smart delta rendering."""

    def __init__(
        self,
        pi: Optional[pigpio.pi] = None,
        channel: int = 0,
        dc_pin: int = 14,
        rst_pin: int = 15,
        backlight_pin: int = 16,
        speed_hz: int = 32_000_000,
        width: int = 240,
        height: int = 320,
        rotation: int = 0,
    ) -> None: ...

    # --- Core Display Methods ---
    def display(self, image: Image.Image) -> None:
        """Displays an image with automatic smart delta rendering.
        Resizes to fit if needed. Thread-safe (acquires SPI lock).
        """

    def display_region(self, image: Image.Image, x0: int, y0: int, x1: int, y1: int) -> None:
        """Displays a portion of an image in the specified region. Thread-safe."""

    def clear(self, color: tuple[int, int, int] = (0, 0, 0)) -> None:
        """Fills the display with a solid color. Thread-safe."""

    # --- Brightness Control ---
    def set_brightness(self, percent: int) -> None:
        """Sets backlight brightness (0-100%). Uses PWM."""

    # --- Configuration ---
    def set_rotation(self, rotation: int) -> None:
        """Sets display rotation (0, 90, 180, 270 degrees)."""

    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...

    # --- Power Management ---
    def sleep(self) -> None:
        """Puts display into low-power sleep mode."""

    def wake(self) -> None:
        """Wakes display from sleep mode."""

    def close(self) -> None:
        """Releases all resources (SPI, GPIO). Thread-safe."""

    # --- Health ---
    def health_check(self) -> bool:
        """Returns True if SPI handle and pigpio are valid."""

    # --- Actuator ABC Interface (ninja_core compatibility) ---
    def initialize(self) -> None:
        """Wakes display, sets brightness to 100%."""

    def execute(self, command: dict[str, Any]) -> None:
        """Execute display command dict.

        Supported keys:
            - "image" (PIL.Image.Image): Display an image
            - "clear" (bool): Clear the display
            - "backlight" (bool): Turn backlight on/off
            - "brightness" (int): Set brightness 0-100%
        """

    def off(self) -> None:
        """Turns off display (DISPOFF + backlight off)."""
```

### 4.2 Properties & Attributes Summary

| Attribute | Type | Access | Description |
|-----------|------|--------|-------------|
| `width` | `int` | read-only | Current display width (respects rotation) |
| `height` | `int` | read-only | Current display height (respects rotation) |
| `pi` | `pigpio.pi` | read-only | pigpio connection handle |
| `spi_handle` | `int` | internal | SPI bus handle |

---

## 5. Smart Delta Rendering

The core performance feature. The driver automatically detects changed pixels and updates only the dirty region.

### 5.1 Algorithm

```python
from PIL import ImageChops

class ST7789V:
    def __init__(self, ...):
        self._previous_image: Optional[Image.Image] = None
        self._spi_lock = threading.Lock()

    def display(self, image: Image.Image) -> None:
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))

        with self._spi_lock:
            if self._previous_image is None:
                # First frame — full update
                self._write_full_frame(image)
            else:
                # Delta rendering
                diff = ImageChops.difference(self._previous_image, image)
                bbox = diff.getbbox()  # (left, upper, right, lower) or None

                if bbox is None:
                    return  # No changes — skip SPI entirely

                # Expand bbox by 1 pixel for anti-aliasing safety
                x0 = max(0, bbox[0] - 1)
                y0 = max(0, bbox[1] - 1)
                x1 = min(self.width, bbox[2] + 1)
                y1 = min(self.height, bbox[3] + 1)

                region = image.crop((x0, y0, x1, y1))
                self._write_partial_frame(region, x0, y0, x1 - 1, y1 - 1)

            self._previous_image = image.copy()
```

### 5.2 Expected Performance Impact

| Scenario | Old (Full Frame) | New (Delta) | Reduction |
|----------|-------------------|-------------|-----------|
| Idle face (blinking) | 115 KB/frame | ~5-10 KB/frame | **~90-95%** |
| Speaking (mouth moving) | 115 KB/frame | ~15-20 KB/frame | **~83%** |
| Full expression change | 115 KB/frame | 115 KB/frame | 0% (expected) |
| Static QR code | 115 KB/frame | 0 KB (skipped) | **100%** |

---

## 6. PWM Brightness Control

### 6.1 Implementation

```python
def set_brightness(self, percent: int) -> None:
    """Sets backlight brightness using PWM.

    Args:
        percent: Brightness level, 0 (off) to 100 (full).
    """
    percent = max(0, min(100, percent))
    # pigpio PWM range is 0-255
    duty_cycle = int(percent * 255 / 100)
    self.pi.set_PWM_dutycycle(self.backlight_pin, duty_cycle)
```

### 6.2 Integration with Actuator ABC

The `execute()` method gains a new key:

```python
def execute(self, command: dict) -> None:
    if "brightness" in command:
        self.set_brightness(command["brightness"])
    # ... existing image/clear/backlight handling
```

---

## 7. Multi-Display Support

### 7.1 Supported Displays

| Display | Size | Resolution | Driver IC | Color Offset | Notes |
|---------|------|-----------|-----------|--------------|-------|
| ST7789V IPS TFT | 2.8 inch | 240×320 | ST7789V | May need x_offset/y_offset | Default |
| Waveshare IPS LCD | 2.0 inch | 240×320 | ST7789V | (0, 0) | Production display |

### 7.2 Display Profiles

```python
DISPLAY_PROFILES = {
    "st7789v_2inch8": {
        "name": "ST7789V 2.8-inch IPS TFT 240×320",
        "width": 240, "height": 320,
        "x_offset": 0, "y_offset": 0,
        "speed_hz": 32_000_000,
    },
    "waveshare_2inch": {
        "name": "Waveshare 2.0-inch IPS LCD 240×320",
        "width": 240, "height": 320,
        "x_offset": 0, "y_offset": 0,
        "speed_hz": 32_000_000,
    },
}

DEFAULT_PINS = {
    "dc_pin": 14,
    "rst_pin": 15,
    "backlight_pin": 16,
}
```

### 7.3 Constructor Usage

```python
# ST7789V 2.8-inch (default)
lcd = ST7789V(pi=pi, width=240, height=320)

# Waveshare 2.0-inch (same resolution)
lcd = ST7789V(pi=pi, width=240, height=320)

# With ninja_core HAL (reads from config.json)
lcd = ST7789V(
    pi=self.pi,
    dc_pin=config.display.dc,
    rst_pin=config.display.rst,
    backlight_pin=config.display.blk,
    width=240,
    height=320,
)
```

### 7.4 MADCTL & Rotation

Both displays use the same MADCTL values for rotation. Color offsets may differ between display modules (some have a 40px or 80px X/Y offset in the ST7789V framebuffer):

```python
def set_rotation(self, rotation: int) -> None:
    madctl_map = {
        0:   0x00,
        90:  0x60,
        180: 0xC0,
        270: 0xA0,
    }
    # Apply display-profile-specific offsets here
```

---

## 8. Effects Module

### 8.1 Text Ticker (Scrolling Marquee)

```python
class TextTicker:
    """Smoothly scrolls text across the display from right to left."""

    def __init__(self, lcd: ST7789V, text: str, font_size: int = 32,
                 color: tuple = (255, 255, 255),
                 bg_color: tuple = (0, 0, 0),
                 speed: float = 2.0,
                 language: str = "en"):
        """
        Args:
            lcd: The display driver instance.
            text: The text to scroll.
            font_size: Font size in pixels.
            color: Text color RGB tuple.
            bg_color: Background color RGB tuple.
            speed: Pixels per frame to scroll (higher = faster).
            language: Font selection — "en", "ja", or "zh-tw".
        """

    def start(self) -> None:
        """Starts the scrolling animation in a background thread."""

    def stop(self) -> None:
        """Stops the scrolling animation."""

    def is_running(self) -> bool:
        """Returns True if the ticker is currently animating."""
```

### 8.2 Font Selection Logic

```python
import importlib.resources

def _load_font(language: str, size: int) -> ImageFont.FreeTypeFont:
    """Loads a bundled font based on language preference."""
    font_map = {
        "en": "NotoSans-Regular.ttf",
        "ja": "NotoSansJP-Regular.otf",
        "zh-tw": "NotoSansTC-Regular.otf",
    }
    font_file = font_map.get(language, font_map["en"])
    with importlib.resources.path("pi0disp.fonts", font_file) as path:
        return ImageFont.truetype(str(path), size)
```

---

## 9. Config Manager

### 9.1 Standalone Config (`display.json`)

```json
{
    "display_profile": "waveshare_2inch",
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

> **Note:** Both supported displays share the same 240×320 resolution.

This file is created by `uv run pi0disp init` or via the interactive display-tool. If it does not exist, all values fall back to the defaults above.

### 9.2 ConfigManager Class

Follows the same pattern as `pi0servo.ConfigManager`:

```python
class ConfigManager:
    """Manages display configuration persistence."""

    def __init__(self, config_file: str = "display.json"): ...
    def load(self) -> dict: ...
    def save(self) -> None: ...
    def get(self, key: str, default=None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def export_config(self, path: str) -> None: ...
    def import_config(self, path: str) -> dict: ...

    def init_config(self, interactive: bool = True) -> dict:
        """Initialize display configuration.

        When interactive=True, prompts the user step by step:
          1. Select display profile (ST7789V 2.8-inch / Waveshare 2.0-inch)
          2. Set DC pin (default: 14)
          3. Set RST pin (default: 15)
          4. Set BLK pin (default: 16)
          5. Set rotation (default: 0)
          6. Set brightness (default: 100)

        When interactive=False, creates display.json with all defaults.
        Saves the result to display.json and returns the config dict.
        """
```

### 9.3 Init Flow (User Experience)

```
$ uv run pi0disp init

╔══════════════════════════════════════════════════════════════╗
║               pi0disp — Display Initialization               ║
╚══════════════════════════════════════════════════════════════╝

Select your display module:
  1. ST7789V 2.8-inch IPS TFT 240×320
  2. Waveshare 2.0-inch IPS LCD 240×320
Choice [1]: 1

--- Pin Configuration (BCM GPIO numbers) ---

  DC pin  [14]: 14
  RST pin [15]: 15
  BLK pin [16]: 16

--- Display Settings ---

  Rotation (0/90/180/270) [0]: 90
  Brightness (0-100%)     [100]: 100

✅ Configuration saved to display.json

  Display:    ST7789V 2.8-inch IPS TFT 240×320
  Resolution: 240 × 320
  Pins:       DC=14, RST=15, BLK=16
  Rotation:   90°
  Brightness: 100%
```

### 9.3 ninja_core Config Sync

```bash
# Import display config into ninja_core's config.json
uv run ninja_core config import
# Found display config at 'display.json'. Importing...
```

The existing `DisplayConfig` in `config.py` (dc, rst, blk) should be extended to include `width`, `height`, `rotation`, and `brightness`.

---

## 10. CLI Commands

### 10.1 Command Overview

```bash
# Initialize display (first-time setup)
uv run pi0disp init
uv run pi0disp init --defaults              # Skip prompts, use all defaults

# Interactive tool
uv run pi0disp display-tool

# Display an image
uv run pi0disp image <path/to/image.png>

# Display & scroll text
uv run pi0disp text "Hello NinjaRobot!" --scroll --lang ja

# Clear the display
uv run pi0disp clear

# Ball animation demo
uv run pi0disp demo --num-balls 5 --fps 30

# Display driver info
uv run pi0disp info

# Config management
uv run pi0disp config show
uv run pi0disp config set brightness 80
uv run pi0disp config export <path>
uv run pi0disp config import <path>

# Brightness control
uv run pi0disp brightness 50
```

### 10.2 Interactive Display Tool Menu

```
╔══════════════════════════════════════════════════════════════╗
║               pi0disp Interactive Tool                      ║
╠══════════════════════════════════════════════════════════════╣
║  1. Init          - Set up display module & pin config      ║
║  2. Show Image    - Display an image file                   ║
║  3. Show Text     - Display text (with optional scroll)     ║
║  4. Ball Demo     - Run bouncing ball animation             ║
║  5. Brightness    - Adjust backlight brightness             ║
║  6. Info          - Show driver state & config              ║
║  7. Clear         - Clear the display                       ║
║  8. Config        - Export/import configuration             ║
║  9. Exit                                                    ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 11. Backward Compatibility

### 11.1 API Compatibility Matrix

**Zero changes required in ninja_core.** All existing call patterns preserved:

| ninja_core Usage | Old API | New API | Status |
|------------------|---------|---------|--------|
| `hal.py:37` | `"pi0disp.disp.st7789v"` / `"ST7789V"` | `"pi0disp.core.driver"` / `"ST7789V"` | ⚠️ Update DRIVER_REGISTRY |
| `hal.py:231` | `ST7789V(pi, channel, dc_pin, rst_pin, backlight_pin)` | Same constructor signature | ✅ Compatible |
| `facial_expressions.py:106` | `lcd.display(image)` | Same method | ✅ Compatible |
| `facial_expressions.py:20` | `lcd.width`, `lcd.height` | Same properties | ✅ Compatible |
| `web_server.py:261` | `display.display(qr)` | Same method | ✅ Compatible |
| `dispatcher.py:165` | `display.execute({"image": img})` | Same + new keys | ✅ Compatible |
| `api_wrappers.py:98` | `display.execute({"image": img})` | Same method | ✅ Compatible |
| `api_wrappers.py:107` | `display.execute({"clear": True})` | Same method | ✅ Compatible |
| `hal.py:277-278` | `display.off()`, `display.close()` | Same methods | ✅ Compatible |

### 11.2 DRIVER_REGISTRY Update Required

```python
# hal.py — ONE line change
DRIVER_REGISTRY = {
    "display": {
        "module": "pi0disp.core.driver",  # was: "pi0disp.disp.st7789v"
        "class": "ST7789V",               # unchanged
    },
}
```

### 11.3 Backward-Compatible Import

```python
# pi0disp/__init__.py
from .core.driver import ST7789V
from .config.config_manager import ConfigManager
```

---

## 12. Implementation Phases

### Phase 1: Project Scaffold & Renderer (PC/Mac)

| Task | Deliverable |
|------|-------------|
| Create `pyproject.toml` with dependencies | `pyproject.toml` |
| Create `__init__.py` with exports | `__init__.py` |
| Implement `ColorConverter` (RGB→RGB565 via numpy LUT) | `core/renderer.py` |
| Implement `RegionOptimizer` (clamp, merge dirty rects) | `core/renderer.py` |
| Write unit tests for renderer | `tests/test_renderer.py` |
| Lint with `uv run ruff check` | Clean lint |

**Dependencies:** `click`, `numpy`, `pillow`, `ninja_utils`, `pigpio` (optional)

**Verification:** `cd pi0disp && uv run pytest tests/test_renderer.py -v`

---

### Phase 2: Core Driver (PC/Mac with mock pigpio)

| Task | Deliverable |
|------|-------------|
| Implement `ST7789V` class with thread-safe SPI | `core/driver.py` |
| SPI command/data methods with Lock | `_write_command()`, `_write_data()` |
| Hardware init sequence | `_init_display()` |
| Smart Delta Rendering in `display()` | `display()`, `_write_full_frame()`, `_write_partial_frame()` |
| `display_region()` for manual partial updates | `display_region()` |
| `set_rotation()` with MADCTL | `set_rotation()` |
| PWM brightness via `set_brightness()` | `set_brightness()` |
| `close()` with resource cleanup | `close()` |
| `sleep()` / `wake()` power management | `sleep()`, `wake()` |
| Actuator ABC: `initialize()`, `execute()`, `off()` | Actuator interface |
| `health_check()` | `health_check()` |
| Context manager (`__enter__`/`__exit__`) | Context manager |
| Write unit tests with mocked pigpio | `tests/test_driver.py` |
| Lint with `uv run ruff check` | Clean lint |

**Verification:** `cd pi0disp && uv run pytest tests/test_driver.py -v`

---

### Phase 3: Config Manager (PC/Mac)

| Task | Deliverable |
|------|-------------|
| Implement `ConfigManager` (load/save/get/set/export/import) | `config/config_manager.py` |
| Implement `init_config()` with interactive prompts | `config/config_manager.py` |
| Implement display profile selection (ST7789V 2.8" / Waveshare 2.0") | `config/config_manager.py` |
| Create default `display.json` | `display.json` |
| Write unit tests | `tests/test_config.py` |

**Verification:** `cd pi0disp && uv run pytest tests/test_config.py -v`

---

### Phase 4: Effects Module (PC/Mac)

| Task | Deliverable |
|------|-------------|
| Implement `TextTicker` scrolling marquee | `effects/text_ticker.py` |
| Multilingual font loading via `importlib.resources` | Font loader in effects |
| Bundle fonts in `fonts/` directory | `NotoSans*.ttf/otf` |

**Verification:** Manual test on Raspberry Pi in Phase 6.

---

### Phase 5: CLI Commands (PC/Mac)

| Task | Deliverable |
|------|-------------|
| Create `__main__.py` Click CLI group | `__main__.py` |
| `init` command (first-time setup wizard) | `cli/init_cmd.py` |
| `image` command (display image) | `cli/image_cmd.py` |
| `text` command (display/scroll text) | `cli/text_cmd.py` |
| `demo` command (ball animation) | `cli/demo_cmd.py` |
| `clear` command | Part of `__main__.py` |
| `info` command (driver state) | `cli/info_cmd.py` |
| `config` command group (show/set/export/import) | Part of `__main__.py` |
| `brightness` command | Part of `__main__.py` |
| `display-tool` interactive menu (includes Init option) | `cli/display_tool.py` |

**Verification:** `uv run pi0disp --help` (structure check on PC/Mac).

---

### Phase 6: Hardware Validation & Integration (Raspberry Pi)

| Task | Deliverable |
|------|-------------|
| Test on ST7789V 2.8-inch IPS TFT (240×320) | Hardware validation |
| Test on Waveshare 2.0-inch IPS LCD (240×320) | Hardware validation |
| Test PWM brightness (0%, 50%, 100%) | Brightness verification |
| Run ball_anime demo at 30 FPS | Animation performance |
| Test text ticker with multilingual text | Font rendering |
| Verify ninja_core integration (`uv run ninja_core server`) | Full system test |
| Verify facial expressions at ~60 FPS | AnimatedFaces integration |
| Update DRIVER_REGISTRY in `hal.py` | ninja_core compatibility |
| Update `DevelopmentLog.md` | Documentation |
| Update `DevelopmentGuide.md` | API reference |
| Lint entire library | `uv run ruff check pi0disp/` |

**Verification:** See Testing & Verification section below.

---

## 13. Testing & Verification

### 13.1 Automated Tests (PC/Mac)

```bash
cd pi0disp && uv run pytest tests/ -v
```

| Test File | What It Tests |
|-----------|---------------|
| `test_renderer.py` | RGB→RGB565 conversion accuracy, region clamping, region merging |
| `test_driver.py` | Constructor, display(), delta rendering logic, rotation, brightness, close(), execute(), thread-safety |
| `test_config.py` | load/save/get/set/export/import, missing file handling |

All tests use mocked `pigpio.pi()` (same pattern as `pi0servo` and `pi0vl53l0x` tests).

### 13.2 Manual Hardware Tests (Raspberry Pi)

| Test | Command | Pass Criteria |
|------|---------|---------------|
| Init setup | `uv run pi0disp init` | Prompts for display & pins, saves `display.json` |
| Image display | `uv run pi0disp image assets/images/sample_face.jpg` | Image visible, correct colors |
| Clear display | `uv run pi0disp clear` | Screen turns black |
| Ball demo | `uv run pi0disp demo --num-balls 5` | Smooth animation, ~30 FPS |
| Text display | `uv run pi0disp text "Hello!" --lang en` | Text renders correctly |
| Text scroll | `uv run pi0disp text "ニンジャロボット" --scroll --lang ja` | Smooth scroll |
| Brightness | `uv run pi0disp brightness 50` | Noticeably dimmer |
| Info | `uv run pi0disp info` | Shows config and driver state |
| Config export | `uv run pi0disp config export /tmp/display_backup.json` | JSON file created |
| Integration | `uv run ninja_core server` | Facial expressions work, QR code displays |
| **Reboot test** | Reboot → `uv run pi0disp info` | Display initializes correctly |

### 13.3 Thread Safety Verification

```python
# Manual test: Simulate concurrent display access
import threading
from pi0disp import ST7789V

lcd = ST7789V()
image1 = Image.new("RGB", (240, 240), "red")
image2 = Image.new("RGB", (240, 240), "blue")

def t1():
    for _ in range(100):
        lcd.display(image1)

def t2():
    for _ in range(100):
        lcd.display(image2)

# Both threads should complete without SPI corruption
threading.Thread(target=t1).start()
threading.Thread(target=t2).start()
```

---

## Appendix A: File Inventory

### A.1 Files to Create (New)

| Path | Purpose | Phase |
|------|---------|-------|
| `pyproject.toml` | Package config, dependencies | 1 |
| `display.json` | Default pin configuration | 1 |
| `README.md` | Library documentation | 6 |
| `LICENSE` | MIT License | 1 |
| `src/pi0disp/__init__.py` | Exports: ST7789V, ConfigManager | 1 |
| `src/pi0disp/__main__.py` | CLI entry point | 5 |
| `src/pi0disp/core/__init__.py` | Core module exports | 1 |
| `src/pi0disp/core/driver.py` | ST7789V class | 2 |
| `src/pi0disp/core/renderer.py` | ColorConverter, RegionOptimizer | 1 |
| `src/pi0disp/effects/__init__.py` | Effects module exports | 4 |
| `src/pi0disp/effects/text_ticker.py` | Scrolling text marquee | 4 |
| `src/pi0disp/config/__init__.py` | Config module exports | 3 |
| `src/pi0disp/config/config_manager.py` | Pin config persistence | 3 |
| `src/pi0disp/cli/__init__.py` | CLI module exports | 5 |
| `src/pi0disp/cli/display_tool.py` | Interactive tool menu (w/ Init) | 5 |
| `src/pi0disp/cli/init_cmd.py` | Init / setup wizard CLI | 5 |
| `src/pi0disp/cli/image_cmd.py` | Image display CLI | 5 |
| `src/pi0disp/cli/text_cmd.py` | Text display CLI | 5 |
| `src/pi0disp/cli/demo_cmd.py` | Ball animation demo | 5 |
| `src/pi0disp/cli/info_cmd.py` | Status display | 5 |
| `src/pi0disp/fonts/NotoSans-Regular.ttf` | English font | 4 (copy) |
| `src/pi0disp/fonts/NotoSansJP-Regular.otf` | Japanese font | 4 (copy) |
| `src/pi0disp/fonts/NotoSansTC-Regular.otf` | Traditional Chinese font | 4 (copy) |
| `tests/test_renderer.py` | Renderer unit tests | 1 |
| `tests/test_driver.py` | Driver unit tests | 2 |
| `tests/test_config.py` | Config unit tests | 3 |

### A.2 ninja_core Files to Update (Phase 6)

| File | Change | Impact |
|------|--------|--------|
| `ninja_core/src/ninja_core/hal.py` | Update DRIVER_REGISTRY module path | 1 line change |
| `DevelopmentLog.md` | Log the rebuild | Documentation |
| `DevelopmentGuide.md` | Update pi0disp API section | Documentation |
| `ProjectUpgradePlan.md` | Mark Phase 5-6 complete | Documentation |

---

## Appendix B: Related Documents

| Document | Purpose |
|----------|---------|
| [ProjectUpgradePlan.md](../ProjectUpgradePlan.md) | Overall driver upgrade roadmap |
| [DevelopmentGuide.md](../DevelopmentGuide.md) | API reference |
| [pi0servo/RebuildPlan.md](../pi0servo/RebuildPlan.md) | Reference architecture (completed) |
| [pi0vl53l0x/RebuildPlan.md](../pi0vl53l0x/RebuildPlan.md) | Reference architecture (completed) |
| [Waveshare 2.0-inch LCD Module](https://www.waveshare.com/wiki/2inch_LCD_Module) | Hardware reference |

---

**Document maintained by:** Development Team  
**Last updated:** 2026-02-20
