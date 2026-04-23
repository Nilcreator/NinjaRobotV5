"""Unit tests for pi0disp.effects.text_ticker helpers."""

from pi0disp.effects.text_ticker import (
    TextTicker,
    render_centered_text_image,
    resolve_font_language,
)


class FakeDisplay:
    """Simple stand-in for ST7789V dimensions."""

    width = 240
    height = 320

    def display(self, image):
        self.last_image = image


def test_resolve_font_language_supports_auto_detection():
    assert resolve_font_language("auto", "Hello NinjaRobot") == "en"
    assert resolve_font_language("auto", "こんにちは") == "ja"
    assert resolve_font_language("zh-tw", "你好") == "zh-tw"


def test_render_centered_text_image_returns_display_sized_frame():
    image = render_centered_text_image(FakeDisplay(), "Hello", font_size=24)

    assert image.size == (240, 320)
    assert image.getbbox() is not None


def test_text_ticker_uses_resolved_language_for_auto_text():
    ticker = TextTicker(FakeDisplay(), "こんにちは", language="auto")

    assert ticker._language == "ja"
