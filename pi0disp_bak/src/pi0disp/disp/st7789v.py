#
# (c) 2025 Yoichi Tanibayashi
#
"""
ST7789V Display Driver for Raspberry Pi.

This module provides a high-performance driver for ST7789V-based displays,
optimized for Raspberry Pi environments. It leverages the `performance_core`
module to achieve high frame rates with low CPU usage.

V5 Changes:
- Implements Actuator ABC from ninja_utils.interfaces
- Added initialize() and execute() methods for standardized interface
"""

import time
from typing import Any, Optional, Tuple, Union

import numpy as np
import pigpio
from PIL import Image

from ninja_utils import Actuator
from ..utils.performance_core import create_optimizer_pack

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


class ST7789V(Actuator):
    """
    An optimized driver for ST7789V-based SPI displays implementing the Actuator interface.

    This class manages low-level communication with the display controller,
    providing methods for initialization, configuration, and high-performance
    image rendering using techniques like partial updates and memory pooling.
    
    Note: Display initialization uses blocking time.sleep() calls during hardware
    reset. This is acceptable as it only occurs once at startup.
    """

    def __init__(
        self,
        pi: Optional[pigpio.pi] = None,
        channel: int = 0,
        rst_pin: int = 15,
        dc_pin: int = 14,
        backlight_pin: int = 16,
        speed_hz: int = 32_000_000,
        width: int = 240,
        height: int = 320,
        rotation: int = 90,
    ):
        """
        Initializes the display driver.

        Args:
            pi: An existing pigpio.pi connection. If None, a new one is created.
            channel: SPI channel (0 or 1).
            rst_pin: GPIO pin for Reset.
            dc_pin: GPIO pin for Data/Command select.
            backlight_pin: GPIO pin for the backlight.
            speed_hz: SPI clock speed in Hz.
            width: The native width of the display.
            height: The native height of the display.
            rotation: Initial rotation (0, 90, 180, or 270 degrees).
        """
        self._native_width = width
        self._native_height = height
        self.width = width
        self.height = height
        self._rotation = rotation

        # Initialize the optimizer pack
        self._optimizers = create_optimizer_pack()

        # Initialize pigpio
        self._is_external_pi = pi is not None
        self.pi = pi if self._is_external_pi else pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon. Is it running?")

        self.rst_pin = rst_pin
        self.dc_pin = dc_pin
        self.backlight_pin = backlight_pin

        # Configure GPIO pins
        for pin in [self.rst_pin, self.dc_pin, self.backlight_pin]:
            self.pi.set_mode(pin, pigpio.OUTPUT)

        # Open SPI handle
        self.spi_handle = self.pi.spi_open(channel, speed_hz, 0)
        if self.spi_handle < 0:
            raise RuntimeError(f"Failed to open SPI bus: handle={self.spi_handle}")

        self._last_window: Optional[Tuple[int, int, int, int]] = None

        self._init_display()
        self.set_rotation(self._rotation)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _write_command(self, command: int):
        """Sends a command byte to the display."""
        self.pi.write(self.dc_pin, 0)  # D/C pin low for command
        self.pi.spi_write(self.spi_handle, [command])

    def _write_data(self, data: Union[int, bytes, list]):
        """Sends a data byte or buffer to the display."""
        self.pi.write(self.dc_pin, 1)  # D/C pin high for data
        if isinstance(data, int):
            self.pi.spi_write(self.spi_handle, [data])
        else:
            self.pi.spi_write(self.spi_handle, data)

    def _init_display(self):
        """Performs the hardware initialization sequence for the ST7789V."""
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
        self._write_data(0x55)  # 16 bits per pixel
        self._write_command(CMD_INVON)
        self._write_command(CMD_NORON)
        self._write_command(CMD_DISPON)
        time.sleep(0.1)

        self.pi.write(self.backlight_pin, 1)

    def set_rotation(self, rotation: int):
        """
        Sets the display rotation.

        Args:
            rotation: The desired rotation in degrees (0, 90, 180, 270).
        """
        madctl_values = {0: 0x00, 90: 0x60, 180: 0xC0, 270: 0xA0}
        if rotation not in madctl_values:
            raise ValueError("Rotation must be 0, 90, 180, or 270.")

        self._write_command(CMD_MADCTL)
        self._write_data(madctl_values[rotation])

        # Swap width and height for portrait/landscape modes
        if rotation in (90, 270):
            self.width, self.height = self._native_height, self._native_width
        else:
            self.width, self.height = self._native_width, self._native_height

        self._rotation = rotation
        self._last_window = None  # Invalidate window cache

    def set_window(self, x0: int, y0: int, x1: int, y1: int):
        """
        Sets the active drawing window on the display.

        This is a low-level function; prefer `display` or `display_region`.
        Caches the window dimensions to avoid redundant SPI commands.
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

    def write_pixels(self, pixel_bytes: bytes):
        """
        Writes a raw buffer of pixel data to the current window.
        Uses adaptive chunking to optimize transfer speed.
        """
        chunk_size = self._optimizers["adaptive_chunking"].get_chunk_size()
        data_len = len(pixel_bytes)

        self.pi.write(self.dc_pin, 1)  # Set D/C high for data

        if data_len <= chunk_size:
            self.pi.spi_write(self.spi_handle, pixel_bytes)
        else:
            for i in range(0, data_len, chunk_size):
                self.pi.spi_write(self.spi_handle, pixel_bytes[i : i + chunk_size])

    def display(self, image: Image.Image):
        """
        Displays a full PIL Image on the screen.
        The image is automatically resized to fit the display.
        """
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))

        pixel_bytes = self._optimizers["color_converter"].rgb_to_rgb565_bytes(
            np.array(image)
        )

        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.write_pixels(pixel_bytes)

    def display_region(self, image: Image.Image, x0: int, y0: int, x1: int, y1: int):
        """
        Displays a portion of a PIL image within the specified region.
        This is the core function for partial/dirty rectangle updates.
        """
        # Clamp region to be within display boundaries
        region = self._optimizers["region_optimizer"].clamp_region(
            (x0, y0, x1, y1), self.width, self.height
        )

        if region[2] <= region[0] or region[3] <= region[1]:
            return  # Skip zero- or negative-sized regions

        # Crop the image to the specified region and convert to pixel data
        region_img = image.crop(region)
        pixel_bytes = self._optimizers["color_converter"].rgb_to_rgb565_bytes(
            np.array(region_img)
        )

        # Set window and write data
        self.set_window(region[0], region[1], region[2] - 1, region[3] - 1)
        self.write_pixels(pixel_bytes)

    def close(self):
        """Cleans up resources (turns off backlight, closes SPI handle)."""
        try:
            self.pi.write(self.backlight_pin, 0)
            if hasattr(self, "spi_handle") and self.spi_handle >= 0:
                self.pi.spi_close(self.spi_handle)
        finally:
            if not self._is_external_pi and self.pi.connected:
                self.pi.stop()

    def dispoff(self):
        """DISPOFF."""
        self._write_command(CMD_DISPOFF)
        self.pi.write(self.backlight_pin, 0)

    def sleep(self):
        """Puts the display into sleep mode."""
        self._write_command(CMD_SLPIN)
        self.pi.write(self.backlight_pin, 0)

    def wake(self):
        """Wakes the display from sleep mode."""
        self._write_command(CMD_SLPOUT)
        self.pi.write(self.backlight_pin, 1)

    # --- Actuator Interface Methods ---

    def initialize(self) -> None:
        """Initialize the display (Actuator interface).
        
        Note: The display is already initialized in __init__, so this method
        simply ensures the display is awake and ready.
        """
        self.wake()

    def execute(self, command: dict[str, Any]) -> None:
        """Execute a display command (Actuator interface).
        
        Args:
            command: A dictionary containing one of:
                - "image" (PIL.Image): An image to display.
                - "clear" (bool): If True, clear the display.
                - "backlight" (bool): Turn backlight on/off.
        
        Example:
            display.execute({"image": my_image})
            display.execute({"clear": True})
            display.execute({"backlight": False})
        """
        if "image" in command:
            self.display(command["image"])
        elif command.get("clear"):
            # Clear by displaying a black image
            black_image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
            self.display(black_image)
        elif "backlight" in command:
            self.pi.write(self.backlight_pin, 1 if command["backlight"] else 0)

    def off(self) -> None:
        """Turn off the display (Actuator interface)."""
        self.dispoff()

