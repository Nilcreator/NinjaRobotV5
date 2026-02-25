"""
TextTicker — Scrolling text/marquee animation for ST7789V displays.

Renders text that smoothly scrolls from right to left across the display.
Supports multilingual fonts (English, Japanese, Traditional Chinese).
"""

import importlib.resources
import threading
import time
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


def load_font(language: str = "en", size: int = 32) -> ImageFont.FreeTypeFont:
    """Load a bundled font based on language preference.

    Args:
        language: Language code — "en", "ja", or "zh-tw".
        size: Font size in pixels.

    Returns:
        A PIL FreeTypeFont instance.

    Falls back to default PIL font if bundled fonts not found.
    """
    font_map = {
        "en": "NotoSans-Regular.ttf",
        "ja": "NotoSansJP-Regular.otf",
        "zh-tw": "NotoSansTC-Regular.otf",
    }
    font_file = font_map.get(language, font_map["en"])

    try:
        font_ref = importlib.resources.files("pi0disp.fonts").joinpath(font_file)
        with importlib.resources.as_file(font_ref) as path:
            return ImageFont.truetype(str(path), size)
    except (FileNotFoundError, OSError, ModuleNotFoundError):
        # Fall back to default font
        try:
            return ImageFont.truetype(font_file, size)
        except (OSError, IOError):
            return ImageFont.load_default()


class TextTicker:
    """Smoothly scrolls text across the display from right to left.

    Usage:
        ticker = TextTicker(lcd, "Hello NinjaRobot!", language="en")
        ticker.start()
        time.sleep(10)
        ticker.stop()
    """

    def __init__(
        self,
        lcd,
        text: str,
        font_size: int = 32,
        color: Tuple[int, int, int] = (255, 255, 255),
        bg_color: Tuple[int, int, int] = (0, 0, 0),
        speed: float = 2.0,
        language: str = "en",
    ):
        """Initialize the text ticker.

        Args:
            lcd: The ST7789V display driver instance.
            text: The text to scroll.
            font_size: Font size in pixels.
            color: Text color RGB tuple.
            bg_color: Background color RGB tuple.
            speed: Pixels per frame to scroll (higher = faster).
            language: Font selection — "en", "ja", or "zh-tw".
        """
        self._lcd = lcd
        self._text = text
        self._font_size = font_size
        self._color = color
        self._bg_color = bg_color
        self._speed = speed
        self._language = language

        self._font = load_font(language, font_size)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Pre-render the text to determine its width
        dummy_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), text, font=self._font)
        self._text_width = bbox[2] - bbox[0]
        self._text_height = bbox[3] - bbox[1]

    def start(self) -> None:
        """Start the scrolling animation in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            return  # Already running

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._scroll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the scrolling animation."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def is_running(self) -> bool:
        """Return True if the ticker is currently animating."""
        return self._thread is not None and self._thread.is_alive()

    def _scroll_loop(self) -> None:
        """Main scrolling animation loop."""
        display_w = self._lcd.width
        display_h = self._lcd.height

        # Text scrolls from right edge to beyond left edge
        x_pos = float(display_w)

        # Vertical centering
        y_pos = (display_h - self._text_height) // 2

        while not self._stop_event.is_set():
            # Create frame
            image = Image.new("RGB", (display_w, display_h), self._bg_color)
            draw = ImageDraw.Draw(image)
            draw.text(
                (int(x_pos), y_pos),
                self._text,
                font=self._font,
                fill=self._color,
            )

            try:
                self._lcd.display(image)
            except Exception:
                break  # Exit on display error

            # Move text left
            x_pos -= self._speed
            if x_pos < -self._text_width:
                x_pos = float(display_w)  # Loop back

            # Target ~30 FPS for smooth scrolling
            time.sleep(1 / 30)
