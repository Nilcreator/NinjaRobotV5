"""Text command — Display or scroll text on the screen."""

import time

import click


@click.command()
@click.argument("text_content")
@click.option("--scroll", is_flag=True, help="Enable scrolling marquee.")
@click.option("--lang", default="en", help="Font language: en, ja, zh-tw.")
@click.option("--size", default=32, type=int, help="Font size in pixels.")
@click.option("--color", default="255,255,255", help="Text color R,G,B.")
@click.option("--bg", default="0,0,0", help="Background color R,G,B.")
@click.option("--speed", default=2.0, type=float, help="Scroll speed (pixels/frame).")
@click.option("--duration", default=10.0, type=float, help="Scroll duration (seconds).")
def text(text_content, scroll, lang, size, color, bg, speed, duration):
    """Display text on the ST7789V display.

    TEXT_CONTENT is the text string to display.
    """
    try:
        import pigpio

        from ..config.config_manager import ConfigManager
        from ..core.driver import ST7789V
        from ..effects.text_ticker import TextTicker, render_centered_text_image

        cm = ConfigManager()
        cfg = cm.load()
        pi = pigpio.pi()
        if not pi.connected:
            click.echo("Error: Could not connect to pigpio daemon.")
            return

        lcd = ST7789V(
            pi=pi,
            dc_pin=cfg.get("dc_pin", 14),
            rst_pin=cfg.get("rst_pin", 15),
            backlight_pin=cfg.get("backlight_pin", 16),
            width=cfg.get("width", 240),
            height=cfg.get("height", 320),
            rotation=cfg.get("rotation", 0),
        )

        # Parse colors
        text_color = tuple(int(c) for c in color.split(","))
        bg_color = tuple(int(c) for c in bg.split(","))

        if scroll:
            # Scrolling marquee
            ticker = TextTicker(
                lcd, text_content,
                font_size=size,
                color=text_color,
                bg_color=bg_color,
                speed=speed,
                language=lang,
            )
            click.echo(f"Scrolling: \"{text_content}\" (Ctrl+C to stop)")
            ticker.start()
            try:
                time.sleep(duration)
            except KeyboardInterrupt:
                pass
            ticker.stop()
        else:
            # Static text
            image = render_centered_text_image(
                lcd,
                text_content,
                font_size=size,
                color=text_color,
                bg_color=bg_color,
                language=lang,
            )
            lcd.display(image)
            click.echo(f"Displayed: \"{text_content}\"")

        lcd.close()
    except ImportError as e:
        click.echo(f"Error: Missing dependency — {e}")
        click.echo("  Hint: Run 'sudo apt install python3-pigpio && sudo pigpiod' on Raspberry Pi.")
    except Exception as e:
        click.echo(f"Error: {e}")
