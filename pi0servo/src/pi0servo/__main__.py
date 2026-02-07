"""pi0servo CLI entry point.

Usage:
    python -m pi0servo [OPTIONS] COMMAND [ARGS]...

Commands:
    cmd      Execute a servo command string
    move     Move a single servo to an angle
    calib    View or set servo calibration
    status   Show servo system status
"""

import click

from . import __version__
from .cli import calib, cmd, move, status


@click.group()
@click.version_option(__version__, prog_name="pi0servo")
def cli():
    """pi0servo - Servo control library for Raspberry Pi."""
    pass


# Register commands
cli.add_command(cmd)
cli.add_command(move)
cli.add_command(calib)
cli.add_command(status)


if __name__ == "__main__":
    cli()
