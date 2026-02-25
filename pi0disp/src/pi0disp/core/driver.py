"""
ST7789V Display Driver — Thread-safe SPI driver with smart delta rendering.

This module provides a high-performance driver for ST7789V-based displays,
implementing the Actuator ABC for seamless ninja_core integration.

Key features:
- Thread-safe SPI via threading.Lock()
- Smart delta rendering (only transmits changed pixels)
- PWM brightness control (0-100%)
- Support for 240×320 displays (ST7789V 2.8" and Waveshare 2.0")

Copyright (c) 2025 Chihkuang Chang / Yoichi Tanibayashi
License: MIT
"""

import threading
import time
from typing import Any, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageChops

try:
    import pigpio
except ImportError:
    pigpio = None  # Not available on PC/Mac

try:
    from ninja_utils import Actuator
except ImportError:
    # Fallback for standalone usage or testing
    from abc import ABC, abstractmethod

    class Actuator(ABC):
        @abstractmethod
        def initialize(self) -> None: ...
        @abstractmethod
        def execute(self, command: dict[str, Any]) -> None: ...
        @abstractmethod
        def off(self) -> None: ...


from .renderer import ColorConverter, RegionOptimizer

# --- ST7789V Commands ---
CMD_SWRESET = 0x01
CMD_SLPIN = 0x10
CMD_SLPOUT = 0x11
CMD_NORON = 0x13
CMD_INVON = 0x21
CMD_DISPOFF = 0x28
CMD_DISPON = 0x29
CMD_CASET = 0x2A
CMD_RASET = 0x2B
CMD_RAMWR = 0x2C
CMD_MADCTL = 0x36
CMD_COLMOD = 0x3A

# MADCTL rotation values
MADCTL_MAP = {
    0: 0x00,
    90: 0x60,
    180: 0xC0,
    270: 0xA0,
}

# SPI chunk size for large data transfers
SPI_CHUNK_SIZE = 4096


class ST7789V(Actuator):
    """Thread-safe SPI driver for ST7789V displays with smart delta rendering.

    This driver supports both standalone use and integration with ninja_core
    via the Actuator ABC interface.

    Usage (standalone):
        lcd = ST7789V(width=240, height=320)
        lcd.display(my_pil_image)
        lcd.set_brightness(80)
        lcd.close()

    Usage (ninja_core via HAL):
        lcd = ST7789V(pi=shared_pi, dc_pin=14, rst_pin=15, backlight_pin=16)
        lcd.execute({"image": my_image})
        lcd.execute({"brightness": 50})
    """

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
        rotation: int = 90,
    ) -> None:
        """Initialize the display driver.

        Args:
            pi: An existing pigpio.pi connection. If None, a new one is created.
            channel: SPI channel (0 or 1).
            dc_pin: GPIO pin for Data/Command select (BCM).
            rst_pin: GPIO pin for Reset (BCM).
            backlight_pin: GPIO pin for the backlight (BCM).
            speed_hz: SPI clock speed in Hz.
            width: The native width of the display.
            height: The native height of the display.
            rotation: Initial rotation (0, 90, 180, or 270 degrees).
        """
        self._native_width = width
        self._native_height = height
        self._width = width
        self._height = height
        self._rotation = rotation

        # Thread safety for SPI operations
        self._spi_lock = threading.Lock()

        # Delta rendering state
        self._previous_image: Optional[Image.Image] = None

        # Rendering utilities
        self._color_converter = ColorConverter()
        self._region_optimizer = RegionOptimizer()

        # Initialize pigpio
        self._is_external_pi = pi is not None
        if pigpio is not None:
            self.pi = pi if self._is_external_pi else pigpio.pi()
            if not self.pi.connected:
                raise RuntimeError(
                    "Could not connect to pigpio daemon. Is it running?"
                )
        else:
            self.pi = pi  # May be a mock for testing

        self.rst_pin = rst_pin
        self.dc_pin = dc_pin
        self.backlight_pin = backlight_pin

        # Configure GPIO pins
        if self.pi is not None:
            for pin in [self.rst_pin, self.dc_pin, self.backlight_pin]:
                self.pi.set_mode(pin, pigpio.OUTPUT if pigpio else 1)

            # Open SPI handle
            self.spi_handle = self.pi.spi_open(channel, speed_hz, 0)
            if isinstance(self.spi_handle, int) and self.spi_handle < 0:
                raise RuntimeError(
                    f"Failed to open SPI bus: handle={self.spi_handle}"
                )

            self._last_window: Optional[Tuple[int, int, int, int]] = None

            # Hardware initialization
            self._init_display()
            self.set_rotation(self._rotation)
        else:
            self.spi_handle = -1
            self._last_window = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # --- Properties ---

    @property
    def width(self) -> int:
        """Current display width (respects rotation)."""
        return self._width

    @property
    def height(self) -> int:
        """Current display height (respects rotation)."""
        return self._height

    # --- Low-Level SPI Communication ---

    def _write_command(self, command: int) -> None:
        """Send a command byte to the display. Must hold _spi_lock."""
        self.pi.write(self.dc_pin, 0)  # D/C pin low for command
        self.pi.spi_write(self.spi_handle, [command])

    def _write_data(self, data: Union[int, bytes, list]) -> None:
        """Send data byte(s) to the display. Must hold _spi_lock."""
        self.pi.write(self.dc_pin, 1)  # D/C pin high for data
        if isinstance(data, int):
            self.pi.spi_write(self.spi_handle, [data])
        else:
            self.pi.spi_write(self.spi_handle, data)

    def _write_pixels(self, pixel_bytes: bytes) -> None:
        """Write raw pixel data in chunks. Must hold _spi_lock."""
        self.pi.write(self.dc_pin, 1)  # D/C pin high for data
        data_len = len(pixel_bytes)
        if data_len <= SPI_CHUNK_SIZE:
            self.pi.spi_write(self.spi_handle, pixel_bytes)
        else:
            for i in range(0, data_len, SPI_CHUNK_SIZE):
                self.pi.spi_write(
                    self.spi_handle, pixel_bytes[i: i + SPI_CHUNK_SIZE]
                )

    # --- Hardware Initialization ---

    def _init_display(self) -> None:
        """Perform the hardware initialization sequence for ST7789V."""
        with self._spi_lock:
            # Hardware reset
            self.pi.write(self.rst_pin, 1)
            time.sleep(0.01)
            self.pi.write(self.rst_pin, 0)
            time.sleep(0.01)
            self.pi.write(self.rst_pin, 1)
            time.sleep(0.150)

            # Initialization sequence
            self._write_command(CMD_SWRESET)
            time.sleep(0.150)
            self._write_command(CMD_SLPOUT)
            time.sleep(0.5)
            self._write_command(CMD_COLMOD)
            self._write_data(0x55)  # 16 bits per pixel (RGB565)
            self._write_command(CMD_INVON)
            self._write_command(CMD_NORON)
            self._write_command(CMD_DISPON)
            time.sleep(0.1)

            # Turn on backlight at full brightness
            self.pi.write(self.backlight_pin, 1)

    # --- Display Window ---

    def _set_window(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """Set the active drawing window. Must hold _spi_lock.

        Caches the window to avoid redundant SPI commands.
        """
        window = (x0, y0, x1, y1)
        if self._last_window == window:
            return

        self._write_command(CMD_CASET)
        self._write_data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
        self._write_command(CMD_RASET)
        self._write_data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
        self._write_command(CMD_RAMWR)

        self._last_window = window

    # --- Core Display Methods ---

    def display(self, image: Image.Image) -> None:
        """Display an image with automatic smart delta rendering.

        Resizes the image to fit if needed. Thread-safe (acquires SPI lock).
        Only transmits the changed region compared to the previous frame.

        Args:
            image: A PIL Image to display.
        """
        if image.size != (self._width, self._height):
            image = image.resize((self._width, self._height))

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
                x1 = min(self._width, bbox[2] + 1)
                y1 = min(self._height, bbox[3] + 1)

                region = image.crop((x0, y0, x1, y1))
                self._write_partial_frame(region, x0, y0, x1 - 1, y1 - 1)

            self._previous_image = image.copy()

    def _write_full_frame(self, image: Image.Image) -> None:
        """Write entire frame to display. Must hold _spi_lock."""
        pixel_bytes = self._color_converter.rgb_to_rgb565_bytes(
            np.array(image)
        )
        self._set_window(0, 0, self._width - 1, self._height - 1)
        self._write_pixels(pixel_bytes)

    def _write_partial_frame(
        self, region: Image.Image, x0: int, y0: int, x1: int, y1: int
    ) -> None:
        """Write a partial frame to display. Must hold _spi_lock."""
        pixel_bytes = self._color_converter.rgb_to_rgb565_bytes(
            np.array(region)
        )
        self._set_window(x0, y0, x1, y1)
        self._write_pixels(pixel_bytes)

    def display_region(
        self, image: Image.Image, x0: int, y0: int, x1: int, y1: int
    ) -> None:
        """Display a portion of an image in the specified region. Thread-safe.

        Args:
            image: A PIL Image to display (should be full-size or pre-cropped).
            x0, y0, x1, y1: Region coordinates (inclusive).
        """
        clamped = self._region_optimizer.clamp_region(
            (x0, y0, x1, y1), self._width, self._height
        )
        if clamped[2] <= clamped[0] or clamped[3] <= clamped[1]:
            return  # Skip zero-area regions

        region_img = image.crop(clamped)
        pixel_bytes = self._color_converter.rgb_to_rgb565_bytes(
            np.array(region_img)
        )

        with self._spi_lock:
            self._set_window(
                clamped[0], clamped[1], clamped[2] - 1, clamped[3] - 1
            )
            self._write_pixels(pixel_bytes)

    def clear(self, color: Tuple[int, int, int] = (0, 0, 0)) -> None:
        """Fill the display with a solid color. Thread-safe.

        Args:
            color: RGB color tuple (default: black).
        """
        image = Image.new("RGB", (self._width, self._height), color)
        self.display(image)

    # --- Brightness Control ---

    def set_brightness(self, percent: int) -> None:
        """Set backlight brightness using PWM.

        Args:
            percent: Brightness level, 0 (off) to 100 (full).
        """
        percent = max(0, min(100, percent))
        # pigpio PWM range is 0-255
        duty_cycle = int(percent * 255 / 100)
        if self.pi is not None:
            self.pi.set_PWM_dutycycle(self.backlight_pin, duty_cycle)

    # --- Rotation ---

    def set_rotation(self, rotation: int) -> None:
        """Set display rotation.

        Args:
            rotation: The desired rotation in degrees (0, 90, 180, or 270).

        Raises:
            ValueError: If rotation is not 0, 90, 180, or 270.
        """
        if rotation not in MADCTL_MAP:
            raise ValueError("Rotation must be 0, 90, 180, or 270.")

        with self._spi_lock:
            self._write_command(CMD_MADCTL)
            self._write_data(MADCTL_MAP[rotation])

        # Swap width and height for portrait/landscape modes
        if rotation in (90, 270):
            self._width = self._native_height
            self._height = self._native_width
        else:
            self._width = self._native_width
            self._height = self._native_height

        self._rotation = rotation
        self._last_window = None  # Invalidate window cache
        self._previous_image = None  # Invalidate delta cache

    # --- Power Management ---

    def sleep(self) -> None:
        """Put the display into low-power sleep mode."""
        with self._spi_lock:
            self._write_command(CMD_SLPIN)
        if self.pi is not None:
            self.pi.write(self.backlight_pin, 0)

    def wake(self) -> None:
        """Wake the display from sleep mode."""
        with self._spi_lock:
            self._write_command(CMD_SLPOUT)
            time.sleep(0.5)  # Wait for exit sleep
        if self.pi is not None:
            self.pi.write(self.backlight_pin, 1)

    def close(self) -> None:
        """Release all resources (SPI, GPIO). Thread-safe."""
        with self._spi_lock:
            try:
                if self.pi is not None:
                    self.pi.write(self.backlight_pin, 0)
                    if hasattr(self, "spi_handle") and self.spi_handle >= 0:
                        self.pi.spi_close(self.spi_handle)
                        self.spi_handle = -1
            finally:
                if (
                    not self._is_external_pi
                    and self.pi is not None
                    and hasattr(self.pi, "connected")
                    and self.pi.connected
                ):
                    self.pi.stop()

    # --- Health Check ---

    def health_check(self) -> bool:
        """Return True if SPI handle and pigpio are valid."""
        if self.pi is None:
            return False
        if not hasattr(self.pi, "connected") or not self.pi.connected:
            return False
        if not hasattr(self, "spi_handle") or self.spi_handle < 0:
            return False
        return True

    # --- Actuator ABC Interface (ninja_core compatibility) ---

    def initialize(self) -> None:
        """Wake display and set brightness to 100% (Actuator interface)."""
        self.wake()
        self.set_brightness(100)

    def execute(self, command: dict[str, Any]) -> None:
        """Execute a display command dict (Actuator interface).

        Supported keys:
            - "image" (PIL.Image.Image): Display an image
            - "clear" (bool): Clear the display
            - "backlight" (bool): Turn backlight on/off
            - "brightness" (int): Set brightness 0-100%

        Args:
            command: Command dictionary.
        """
        if "image" in command:
            self.display(command["image"])
        elif command.get("clear"):
            self.clear()
        elif "brightness" in command:
            self.set_brightness(command["brightness"])
        elif "backlight" in command:
            if self.pi is not None:
                self.pi.write(
                    self.backlight_pin, 1 if command["backlight"] else 0
                )

    def off(self) -> None:
        """Turn off display (DISPOFF + backlight off) (Actuator interface)."""
        with self._spi_lock:
            self._write_command(CMD_DISPOFF)
        if self.pi is not None:
            self.pi.write(self.backlight_pin, 0)
