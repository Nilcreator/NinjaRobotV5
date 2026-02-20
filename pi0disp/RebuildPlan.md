# pi0disp Library V2 Detailed Rebuild Plan

This document serves as the definitive engineering guideline for building the new `pi0disp` library from scratch. It provides a deeper understanding of the legacy implementation, an analysis of its critical vulnerabilities, and strictly defined architectural boundaries for the new library.

---

## 1. Analysis of the Old Library (`pi0disp_bak`)

The legacy `pi0disp_bak` library was a synchronous, object-heavy driver designed for the ST7789V SPI display. 

### 1.1 File Structure & Logic
- **`disp/st7789v.py`**: The core driver class. It manipulated GPIO states manually using `pigpio` to manage the DC, RST, and BLK pins and wrote pixel buffers over SPI.
- **`utils/performance_core.py`**: An over-engineered set of optimization tools containing a `MemoryPool`, `RegionOptimizer`, and `AdaptiveChunking` logic.
- **`utils/image_processor.py`**: High-level image resizing tools.
- **`commands/`**: Fragmented test scripts (`ball_anime.py`, `image.py`) that lacked a cohesive CLI entry point.

### 1.2 Core Execution Flow
The driver exposed a `display(Image.Image)` method. Whenever the robot needed to update its face (e.g., from `facial_expressions.py`), it generated a brand new 240x320 or 240x240 Pillow (`PIL.Image`) object, converted the *entire* image into a Numpy array, translated the array into an RGB565 byte array, and then blasted the full 100+ KB payload across the SPI bus.

---

## 2. Vulnerability Deep Dive

The legacy architecture introduced two catastrophic performance vulnerabilities that prevented fluid, responsive robotic behavior.

### 2.1 The "Full Frame" SPI Bottleneck
- **How it was introduced**: `st7789v.display()` lacked any internal tracking of the display's current state. Even if 99% of the screen was stationary (e.g., a static face with only blinking eyes), the driver forced a full-screen redraw.
- **The Impact**: Transmitting ~115KB of SPI data per frame at 60 FPS consumes ~6.9 MB/s of bandwidth. The blocking `spi_write` operations stalled the Python GIL (Global Interpreter Lock), preventing `asyncio` from polling critical sensors like the `pi0vl53l0x` distance sensor in real-time.
- **The Solution**: Implement "Smart Delta Rendering." The driver must cache the previous frame's pixel data and calculate a bounding box of only the *changed* pixels, vastly reducing the SPI payload.

### 2.2 Garbage Collection (GC) Stutter
- **How it was introduced**: The `performance_core.MemoryPool` was useless because the core rendering loop continuously instantiated new `PIL.Image` and `ImageDraw` objects.
- **The Impact**: Rapid instantiation and destruction of large image matrices saturated the RAM, forcing Python to pause the entire program to run the Garbage Collector, resulting in visible visual "stutters."
- **The Solution**: Move to persistent, pre-allocated canvas objects.

---

## 3. Detailed Rebuild Plan for New `pi0disp`

### 3.1 Development Directive
**MANDATORY**: The developer must build the new `pi0disp` library entirely from scratch. You may reference the old `pi0disp_bak` library to understand SPI command bytes (like `CMD_MADCTL` or `CMD_RAMWR`) and color offset math, but **under no circumstances should legacy driver code be copied and pasted**. The new library must be a clean, modern implementation.

### 3.2 Architecture & Solution

#### Target File Structure
```text
pi0disp/
├── pyproject.toml              # Managed via uv
├── README.md                   
├── src/
│   └── pi0disp/
│       ├── __init__.py
│       ├── __main__.py         # Unified CLI Entry point
│       ├── driver.py           # The new, lean ST7789V class (implements Actuator interface)
│       └── effects.py          # Contains text animation / news ticker logic
```

#### Smart Delta Rendering (Execution Logic Example)
The new driver must abstract away differential updates. Here is a conceptual blueprint demonstrating how the new design resolves the "Full Frame" vulnerability:

```python
import numpy as np
from PIL import ImageChops

class ST7789V:
    def __init__(self, ...):
        self._previous_image = None

    def display(self, image: Image.Image) -> None:
        """Smart display function that only updates changed pixels."""
        if self._previous_image is None or self._previous_image.size != image.size:
            # First frame, or size changed: Full update
            self._write_full_frame(image)
        else:
            # Calculate minimal bounding box of changes
            diff = ImageChops.difference(self._previous_image, image)
            bbox = diff.getbbox()
            
            if bbox:
                # bbox = (left, upper, right, lower)
                cropped_img = image.crop(bbox)
                self._write_partial_frame(cropped_img, bbox)
                
        # Cache the current frame for the next delta calculation
        self._previous_image = image.copy()
```

### 3.3 New Features Specification

#### a. Universal Display Support
The new driver must support the default 240x240/240x320 ST7789V IPS configurations natively. Furthermore, it must explicitly verify compatibility and color channels with the **Waveshare 2.0-inch SPI LCD Module** (Resolution: 240x320, Driver IC: ST7789V/ST7789VW). The codebase should easily handle rotation (0, 90, 180, 270) to adapt to either screen size.

#### b. Customizable Pinout via Config
SPI hardware pins on the Raspberry Pi Zero 2W (MOSI, SCLK, CE0) are fixed, but the control pins must be fully customizable upon initialization.
- The `ST7789V.__init__()` must accept `dc_pin`, `rst_pin`, and `backlight_pin` as explicit keyword arguments.
- The `ninja_core.hal` will read these assignments from the master `config.json` and inject them during object instantiation.

#### c. Animated Text Function ("News Ticker")
A dedicated method or helper class (e.g., in `effects.py`) must be implemented to accept a user-defined string and smoothly scroll it across the display from right to left (marquee style).
- Ensure the animation loop employs non-blocking `asyncio` sweeps or is heavily optimized to maintain high framerates.
- The text animation should auto-generate frames and pipe them into the Smart Delta `display()` function.

#### d. Unified CLI Tool
Mimicking the `pi0servo` and `pi0vl53l0x` designs, create a single Command Line Interface powered by `click` or `argparse` executed via `uv run pi0disp`.
- `uv run pi0disp clear` – Empties the screen (blacks it out).
- `uv run pi0disp image <path/to/image.png>` – Renders an image.
- `uv run pi0disp text "Testing!" --scroll` – Triggers the new Animated Text marquee logic.
- `uv run pi0disp info` – Prints current driver state and initialization config.
