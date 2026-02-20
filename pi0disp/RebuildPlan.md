# pi0disp Library Health Report & V2 Rebuild Plan

## 1. Current Health Report & Vulnerability Evaluation

After a comprehensive line-by-line audit of the existing `pi0disp` library and its integration with `ninja_core` (specifically `hal.py` and `facial_expressions.py`), several critical vulnerabilities and architectural bottlenecks were identified.

> **Note on Prompt Clarification:** The request mentioned achieving "reliable distance detection" in the new `pi0disp` library. As `pi0disp` is solely an LCD display driver (while `pi0vl53l0x` handles distance), I have tailored this enhancement plan to focus strictly on your primary goal: **sophisticated and animated facial expressions**.

### 1.1 SPI Bandwidth Bottleneck (The "Full Frame" Problem)
Currently, `ninja_core/facial_expressions.py` explicitly calls `display(image)` at ~60 FPS. The `ST7789V.display()` method converts the entire 240x240 image to RGB565 and blasts the full 115KB payload over the SPI bus every single frame. This requires ~6.9 MB/s of bandwidth, which severely impacts the Raspberry Pi Zero 2W's CPU and blocks other critical sensor polling.

### 1.2 Garbage Collection & Memory Allocation Pressure
In `facial_expressions.py`, the `_animation_loop` creates a brand new `Image.new("RGB")` and a new `ImageDraw.Draw` object 60 times a second. Simultaneously, the `performance_core.py` module in `pi0disp` contains complex abstractions (like `MemoryPool` and `RegionOptimizer`) that are completely **bypassed** and ignored during this full-frame update. This rapid allocation triggers frequent Python Garbage Collection (GC) pauses, causing animations to stutter.

### 1.3 Blocking I/O vs. Asyncio
The current facial expression engine runs in a synchronous `threading.Thread` loop using `time.sleep(1/60)` and blocking `pigpio.spi_write()` calls. This violates the overarching V5 "Asyncio First" principle, increasing the risk of threading deadlocks or SPI resource contention with other drivers.

---

## 2. Redundancy Removal

To make `pi0disp` lean and laser-focused on sophisticated animation rendering, the following redundancies will be eliminated:

1.  **`utils/image_processor.py`**: **DELETE**. It provides high-level resizing tools never utilized by the robot's core systems.
2.  **`utils/performance_core.py`**: **REPLACE**. The hyper-complex, unused `MemoryPool`, `AdaptiveChunking`, and `RegionOptimizer` will be completely removed. We will replace them with a single, highly efficient Numpy-based "Delta Rectangle" calculator.
3.  **`commands/ball_anime.py` & `commands/image.py`**: **MERGE**. These standalone test scripts will be collapsed into a modern, unified `disp-tool` CLI via `cli()` in `__main__.py` (matching the robust pattern established in `pi0servo` and `pi0vl53l0x`).

---

## 3. Enhancement Plan: Sophisticated Facial Expressions

To support fluid, sophisticated facial expressions without locking up the robot's brain, the V2 library will introduce the following core features:

### 3.1 Smart Delta Updates (Bounding Box Rendering)
Instead of relying on the caller to specify regions, the `ST7789V.display()` function will automatically cache the `previous_frame` (as a Numpy array). By executing a fast diff (`np.where(current != previous)`), the driver will automatically crop down to the exact minimal bounding box of changed pixels (e.g., just the blinking eyelid) and perform a `display_region()` update. This will reduce SPI traffic by over 90%.

### 3.2 Actuator ABC Full Compliance
The new library will remain 100% compatible with `ninja_core.hal` by strictly adhering to the `Actuator` interface from `ninja_utils`, while exposing `initialize()`, `execute()`, and `off()` as first-class citizens.

### 3.3 Async-Ready Drawing (Ninja Core Update)
While the `pi0disp` driver itself handles the SPI payload, the rendering loop in `facial_expressions.py` will be rewritten to reuse a single persistent `PIL.Image` canvas, vastly reducing GC pauses and allowing integration into the main `asyncio` event loop.

---

## 4. Phased Implementation Plan

### Phase 1: Project Scaffolding & Cleanup
- Delete `utils/image_processor.py` and `utils/performance_core.py`.
- Delete `commands/ball_anime.py` and `commands/image.py`.
- Initialize `__main__.py` with the boilerplate for `disp-tool` (Click CLI).

### Phase 2: Core Driver Optimization (`st7789v.py`)
- Refactor `ST7789V` to include the **Smart Delta Update** mechanism.
- Implement highly efficient Numpy-to-RGB565 conversion natively without the bloated dependencies.
- Ensure 100% API compatibility with `ninja_core.hal` (maintain `set_window`, `display`, `display_region`, `execute`).

### Phase 3: CLI Tooling (`pi0disp/__main__.py`)
- Build the `disp-tool` CLI to allow standalone testing without Ninja Core.
- Commands: `uv run pi0disp clear`, `uv run pi0disp image <file>`, `uv run pi0disp test-fps`.

### Phase 4: `ninja_core` Integration Validation
- Refactor `ninja_core/src/ninja_core/facial_expressions.py`.
- Migrate away from `threading.Thread` and `Image.new()` per frame.
- Implement persistent canvas drawing and `asyncio.sleep` to guarantee zero stutter.

### Phase 5: Linting, Validation & Documentation
- Run `uv run ruff check pi0disp/`.
- Perform manual hardware validation on Raspberry Pi 2W to confirm FPS improvements.
- Update `DevelopmentLog.md` and `README.md` to reflect V2 specs.
