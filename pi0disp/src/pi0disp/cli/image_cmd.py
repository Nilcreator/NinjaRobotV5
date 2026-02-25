"""Image command — Display an image file on the screen."""

import click
from PIL import Image as PILImage


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--rotation", "-r", type=int, default=None, help="Override rotation.")
def image(path, rotation):
    """Display an image file on the ST7789V display.

    PATH is the path to the image file (PNG, JPG, BMP, etc.).
    """
    try:
        import pigpio

        from ..config.config_manager import ConfigManager
        from ..core.driver import ST7789V

        cm = ConfigManager()
        cfg = cm.load()
        pi = pigpio.pi()
        if not pi.connected:
            click.echo("Error: Could not connect to pigpio daemon.")
            return

        rot = rotation if rotation is not None else cfg.get("rotation", 0)
        lcd = ST7789V(
            pi=pi,
            dc_pin=cfg.get("dc_pin", 14),
            rst_pin=cfg.get("rst_pin", 15),
            backlight_pin=cfg.get("backlight_pin", 16),
            width=cfg.get("width", 240),
            height=cfg.get("height", 320),
            rotation=rot,
        )

        img = PILImage.open(path).convert("RGB")
        lcd.display(img)
        click.echo(f"Displayed: {path} ({img.size[0]}×{img.size[1]})")

        # Keep display on, release SPI
        lcd.close()
    except ImportError:
        click.echo("Error: pigpio not available. Run on Raspberry Pi.")
    except Exception as e:
        click.echo(f"Error: {e}")
