"""Interactive display tool — Menu-driven display testing and configuration."""

import click


@click.command("display-tool")
def display_tool():
    """Launch the interactive display tool.

    Provides a menu-driven interface for testing and configuring the display.
    """
    click.echo()
    click.echo(click.style("╔══════════════════════════════════════════════════════════════╗", fg="cyan"))
    click.echo(click.style("║               pi0disp Interactive Tool                      ║", fg="cyan"))
    click.echo(click.style("╠══════════════════════════════════════════════════════════════╣", fg="cyan"))
    click.echo(click.style("║  1. Init          - Set up display module & pin config      ║", fg="cyan"))
    click.echo(click.style("║  2. Show Image    - Display an image file                   ║", fg="cyan"))
    click.echo(click.style("║  3. Show Text     - Display text (with optional scroll)     ║", fg="cyan"))
    click.echo(click.style("║  4. Ball Demo     - Run bouncing ball animation             ║", fg="cyan"))
    click.echo(click.style("║  5. Brightness    - Adjust backlight brightness             ║", fg="cyan"))
    click.echo(click.style("║  6. Info          - Show driver state & config              ║", fg="cyan"))
    click.echo(click.style("║  7. Clear         - Clear the display                       ║", fg="cyan"))
    click.echo(click.style("║  8. Config        - Export/import configuration             ║", fg="cyan"))
    click.echo(click.style("║  9. Exit                                                    ║", fg="cyan"))
    click.echo(click.style("╚══════════════════════════════════════════════════════════════╝", fg="cyan"))

    while True:
        try:
            choice = click.prompt("\nSelect an option", type=int, default=9)
        except (EOFError, KeyboardInterrupt):
            click.echo("\nExiting.")
            break

        if choice == 1:
            _do_init()
        elif choice == 2:
            _do_image()
        elif choice == 3:
            _do_text()
        elif choice == 4:
            _do_demo()
        elif choice == 5:
            _do_brightness()
        elif choice == 6:
            _do_info()
        elif choice == 7:
            _do_clear()
        elif choice == 8:
            _do_config()
        elif choice == 9:
            click.echo("Goodbye!")
            break
        else:
            click.echo("Invalid choice. Please enter 1-9.")


def _do_init():
    """Run the init wizard."""
    from ..config.config_manager import ConfigManager
    cm = ConfigManager()
    cm.init_config(interactive=True)


def _do_image():
    """Prompt for path and display image."""
    path = click.prompt("Image path", type=str)
    try:
        import pigpio
        from PIL import Image as PILImage

        from ..config.config_manager import ConfigManager
        from ..core.driver import ST7789V

        cm = ConfigManager()
        cfg = cm.load()
        pi = pigpio.pi()
        if not pi.connected:
            click.echo("Error: pigpio not connected.")
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
        img = PILImage.open(path).convert("RGB")
        lcd.display(img)
        click.echo(f"Displayed: {path}")
        lcd.close()
    except ImportError:
        click.echo("Error: pigpio not available.")
    except Exception as e:
        click.echo(f"Error: {e}")


def _do_text():
    """Prompt for text and display it."""
    text_content = click.prompt("Text to display", type=str)
    scroll = click.confirm("Enable scrolling?", default=False)
    lang = click.prompt("Language (en/ja/zh-tw)", type=str, default="en")

    try:
        import time

        import pigpio
        from PIL import Image, ImageDraw

        from ..config.config_manager import ConfigManager
        from ..core.driver import ST7789V
        from ..effects.text_ticker import TextTicker, load_font

        cm = ConfigManager()
        cfg = cm.load()
        pi = pigpio.pi()
        if not pi.connected:
            click.echo("Error: pigpio not connected.")
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

        if scroll:
            ticker = TextTicker(lcd, text_content, language=lang)
            click.echo("Scrolling... (Ctrl+C to stop)")
            ticker.start()
            try:
                time.sleep(15)
            except KeyboardInterrupt:
                pass
            ticker.stop()
        else:
            font = load_font(lang, 32)
            image = Image.new("RGB", (lcd.width, lcd.height), (0, 0, 0))
            draw = ImageDraw.Draw(image)
            bbox = draw.textbbox((0, 0), text_content, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (lcd.width - tw) // 2
            y = (lcd.height - th) // 2
            draw.text((x, y), text_content, font=font, fill=(255, 255, 255))
            lcd.display(image)
            click.echo(f"Displayed: \"{text_content}\"")

        lcd.close()
    except ImportError:
        click.echo("Error: pigpio not available.")
    except Exception as e:
        click.echo(f"Error: {e}")


def _do_demo():
    """Run ball demo with prompts."""
    num_balls = click.prompt("Number of balls", type=int, default=3)
    duration = click.prompt("Duration (seconds)", type=float, default=10.0)

    try:
        import pigpio

        from ..config.config_manager import ConfigManager
        from ..core.driver import ST7789V
        from .demo_cmd import _run_ball_demo

        cm = ConfigManager()
        cfg = cm.load()
        pi = pigpio.pi()
        if not pi.connected:
            click.echo("Error: pigpio not connected.")
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

        click.echo(f"Running demo ({num_balls} balls, {duration}s)...")
        _run_ball_demo(lcd, num_balls, 30, duration)
        lcd.clear()
        lcd.close()
        click.echo("Demo complete.")
    except ImportError:
        click.echo("Error: pigpio not available.")
    except KeyboardInterrupt:
        click.echo("\nDemo stopped.")
    except Exception as e:
        click.echo(f"Error: {e}")


def _do_brightness():
    """Prompt for brightness and apply."""
    percent = click.prompt("Brightness (0-100%)", type=int, default=100)
    try:
        import pigpio

        from ..config.config_manager import ConfigManager
        from ..core.driver import ST7789V

        cm = ConfigManager()
        cfg = cm.load()
        pi = pigpio.pi()
        if not pi.connected:
            click.echo("Error: pigpio not connected.")
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
        lcd.set_brightness(percent)
        click.echo(f"Brightness set to {max(0, min(100, percent))}%")
        lcd.close()
    except ImportError:
        click.echo("Error: pigpio not available.")
    except Exception as e:
        click.echo(f"Error: {e}")


def _do_info():
    """Show display info."""
    from .info_cmd import info
    ctx = click.Context(info)
    ctx.invoke(info)


def _do_clear():
    """Clear the display."""
    try:
        import pigpio

        from ..config.config_manager import ConfigManager
        from ..core.driver import ST7789V

        cm = ConfigManager()
        cfg = cm.load()
        pi = pigpio.pi()
        if not pi.connected:
            click.echo("Error: pigpio not connected.")
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
        lcd.clear()
        click.echo("Display cleared.")
        lcd.close()
    except ImportError:
        click.echo("Error: pigpio not available.")
    except Exception as e:
        click.echo(f"Error: {e}")


def _do_config():
    """Config management submenu."""
    click.echo("\n  1. Show config")
    click.echo("  2. Export config")
    click.echo("  3. Import config")
    choice = click.prompt("  Choice", type=int, default=1)

    from ..config.config_manager import ConfigManager
    cm = ConfigManager()
    cm.load()

    if choice == 1:
        cfg = cm.load()
        click.echo("\n📋 Current Configuration:")
        for k, v in cfg.items():
            click.echo(f"  {k}: {v}")
    elif choice == 2:
        path = click.prompt("Export path", type=str)
        cm.export_config(path)
        click.echo(f"Exported to {path}")
    elif choice == 3:
        path = click.prompt("Import path", type=str)
        try:
            cm.import_config(path)
            click.echo(f"Imported from {path}")
        except FileNotFoundError:
            click.echo(f"File not found: {path}")
