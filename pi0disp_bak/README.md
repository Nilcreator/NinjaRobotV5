# pi0disp

A Python library for controlling ST7789V-based displays on Raspberry Pi.

---

## V5 Changes

> [!NOTE]
> As of V5, this library implements the `Actuator` interface from `ninja_utils.interfaces`.

### Key Changes:
- **Implements `Actuator` ABC**: `initialize()`, `execute()`, `off()` methods.
- **Command-based API**: `execute({"image": img})`, `execute({"clear": True})`, `execute({"backlight": False})`.

### Example (V5):
```python
from pi0disp.disp.st7789v import ST7789V
from PIL import Image
import pigpio

pi = pigpio.pi()
display = ST7789V(pi=pi, dc_pin=14, rst_pin=15, backlight_pin=16)

display.execute({"clear": True})  # Clear screen
img = Image.open("face.jpg")
display.execute({"image": img})   # Show image
display.off()                     # Turn off
display.close()
pi.stop()
```

---

# `pi0disp` Library Testing Guide

This guide provides instructions for connecting your ST7789V display and testing the `pi0disp` library's core functions.

### Phase 1: Hardware & System Setup

First, ensure your hardware is connected correctly and the necessary system services are running.

1.  **Hardware Connections (ST7789V Display):**
    *   **VCC** -> 3.3V
    *   **GND** -> Ground (GND)
    *   **SCL** (or **CLK**) -> SPI0 SCLK (GPIO 11)
    *   **SDA** (or **MOSI**) -> SPI0 MOSI (GPIO 10)
    *   **RST** -> GPIO 19
    *   **DC** -> GPIO 18
    *   **BLK** (Backlight) -> GPIO 20

2.  **Enable SPI Interface:**
    If you have not already done so, enable the SPI interface:
    ```bash
    sudo raspi-config
    ```
    Navigate to `3 Interface Options` -> `I4 SPI` and select `<Yes>`. Reboot if prompted.

3.  **Start pigpio Daemon:**
    The display driver requires the `pigpio` service to be running.
    ```bash
    sudo pigpiod
    ```

### Phase 2: Library Installation

Install the new `pi0disp` library in editable mode. This command will also update any existing libraries if they have changed. Run this from the `NinjaRobotV4` root directory:

```bash
uv pip install -e ./pi0disp
```

### Phase 3: Asset Preparation

The test scripts require a font file and a sample image.

2.  **Prepare a Sample Image:**
    A sample image is already included in the project at `assets/images/sample_face.jpg`.

### Phase 4: Running the Tests

Now, run the command-line tools to test the display functions.

1.  **Test 1: Image Display**
    This test will display your chosen image and cycle through several gamma corrections.

    *   **Command:** (Replace the path with the actual path to your image)
        ```bash
        uv run pi0disp image assets/images/sample_face.jpg
        ```
    *   **Expected Output:** You should see your image appear on the display. Every 3 seconds, the brightness/contrast will change as different gamma values are applied, before the script finishes.

2.  **Test 2: Ball Animation**
    This test runs a physics-based animation to check performance and rendering.

    *   **Command:**
        ```bash
        uv run pi0disp ball_anime --num-balls 5
        ```
    *   **Expected Output:** You will see 5 colored balls bouncing around the screen. In the top-left corner, an "FPS" counter will show the current frames per second.
    *   To stop the animation, press **Ctrl+C**.

---

If both tests complete successfully, your `pi0disp` library is working correctly.