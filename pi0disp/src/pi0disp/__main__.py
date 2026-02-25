"""
pi0disp CLI — Command-line interface for ST7789V display control.

Usage:
    uv run pi0disp init           # First-time setup
    uv run pi0disp display-tool   # Interactive menu
    uv run pi0disp image <path>   # Display an image
    uv run pi0disp text "Hello"   # Display text
    uv run pi0disp demo           # Ball animation demo
    uv run pi0disp info           # Show driver info
    uv run pi0disp clear          # Clear display
    uv run pi0disp brightness 50  # Set brightness
    uv run pi0disp config show    # Show config
"""

import click

from .cli.demo_cmd import demo
from .cli.display_tool import display_tool
from .cli.image_cmd import image
from .cli.info_cmd import info
from .cli.init_cmd import init
from .cli.text_cmd import text


@click.group()
def cli():
    """pi0disp — ST7789V Display Driver CLI."""
    pass


# Register subcommands
cli.add_command(init)
cli.add_command(display_tool, name="display-tool")
cli.add_command(image)
cli.add_command(text)
cli.add_command(demo)
cli.add_command(info)


@cli.command()
def clear():
    """Clear the display (fill with black)."""
    try:
        import pigpio

        from .config.config_manager import ConfigManager
        from .core.driver import ST7789V

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
        lcd.clear()
        click.echo("Display cleared.")
        lcd.close()
    except ImportError:
        click.echo("Error: pigpio not available. Run on Raspberry Pi.")
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.argument("percent", type=int)
def brightness(percent):
    """Set display brightness (0-100%)."""
    try:
        import pigpio

        from .config.config_manager import ConfigManager
        from .core.driver import ST7789V

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
        lcd.set_brightness(percent)
        click.echo(f"Brightness set to {max(0, min(100, percent))}%")
        lcd.close()
    except ImportError:
        click.echo("Error: pigpio not available. Run on Raspberry Pi.")
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.group()
def config():
    """Manage display configuration."""
    pass


@config.command()
def show():
    """Show current configuration."""
    from .config.config_manager import ConfigManager

    cm = ConfigManager()
    cfg = cm.load()
    click.echo(click.style("\n📋 Display Configuration:", bold=True))
    for key, value in cfg.items():
        click.echo(f"  {key}: {value}")
    click.echo()


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    from .config.config_manager import ConfigManager

    cm = ConfigManager()
    cm.load()
    # Try to convert to int
    try:
        value = int(value)
    except ValueError:
        pass
    cm.set(key, value)
    click.echo(f"Set {key} = {value}")


@config.command("export")
@click.argument("path")
def config_export(path):
    """Export configuration to a file."""
    from .config.config_manager import ConfigManager

    cm = ConfigManager()
    cm.load()
    cm.export_config(path)
    click.echo(f"Configuration exported to {path}")


@config.command("import")
@click.argument("path")
def config_import(path):
    """Import configuration from a file."""
    from .config.config_manager import ConfigManager

    cm = ConfigManager()
    cm.import_config(path)
    click.echo(f"Configuration imported from {path}")


if __name__ == "__main__":
    cli()
