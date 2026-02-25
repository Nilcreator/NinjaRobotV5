"""Init command — First-time display setup wizard."""

import click

from ..config.config_manager import ConfigManager


@click.command()
@click.option("--defaults", is_flag=True, help="Use all default values (no prompts).")
def init(defaults):
    """Initialize display configuration (first-time setup).

    Walks you through selecting your display module and configuring GPIO pins.
    Creates a display.json file with your settings.
    """
    cm = ConfigManager()
    cm.init_config(interactive=not defaults)
