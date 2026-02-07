"""CLI command execution - run servo commands directly."""

import sys

import click

from ..core import ServoGroup


def create_pi():
    """Create pigpio connection (only on Raspberry Pi)."""
    try:
        import pigpio
        pi = pigpio.pi()
        if not pi.connected:
            click.echo("Error: Could not connect to pigpio daemon.", err=True)
            click.echo("Run 'sudo pigpiod' to start the daemon.", err=True)
            sys.exit(1)
        return pi
    except ImportError:
        click.echo("Error: pigpio not available (not on Raspberry Pi?)", err=True)
        sys.exit(1)


@click.command("cmd")
@click.argument("command")
@click.option(
    "-p", "--pins",
    default="20,21,22,23",
    help="Comma-separated list of GPIO pins to control.",
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    help="Path to servo configuration file.",
)
def cmd(command: str, pins: str, config: str | None):
    """Execute a servo command string.

    COMMAND: Servo command in format [SPEED_]PIN:ANGLE[/PIN:ANGLE...]

    Examples:
        pi0servo cmd "20:45"
        pi0servo cmd "F_20:45/21:-30"
        pi0servo cmd "S_20:C/21:M"
    """
    # Parse pins
    try:
        pin_list = [int(p.strip()) for p in pins.split(",")]
    except ValueError as e:
        raise click.BadParameter(f"Invalid pins format: {e}")

    pi = create_pi()

    try:
        # Create servo group
        group = ServoGroup(
            pi=pi,
            pins=pin_list,
            config_path=config,
        )

        click.echo(f"Executing: {command}")
        success = group.execute_command(command)

        if success:
            click.echo("✓ Command completed")
        else:
            click.echo("✗ Command aborted or failed", err=True)
            sys.exit(1)

    finally:
        pi.stop()
