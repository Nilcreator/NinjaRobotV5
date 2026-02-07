"""CLI command execution - run servo commands directly."""

import sys

import click

from ..config import ConfigManager
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
    type=click.Path(),
    default="servo.json",
    help="Path to servo configuration file.",
)
@click.option(
    "-d", "--debug",
    is_flag=True,
    help="Enable debug output.",
)
def cmd(command: str, pins: str, config: str, debug: bool):
    """Execute a servo command string.

    COMMAND: Servo command in format [SPEED_]PIN:ANGLE[/PIN:ANGLE...]

    Speed modes:\n
        F_ = Fast (100% velocity)\n
        M_ = Medium (75% velocity, default)\n
        S_ = Slow (50% velocity)\n

    Special angles:\n
        C = Center (0°)\n
        M = Min (-90°)\n
        X = Max (90°)\n

    Examples:\n
        pi0servo cmd "20:45"             # Move pin 20 to 45°\n
        pi0servo cmd "F_20:45/21:-30"    # Fast move two servos\n
        pi0servo cmd "S_20:C/21:M"       # Slow, move to special positions\n
    """
    # Parse pins
    try:
        pin_list = [int(p.strip()) for p in pins.split(",")]
    except ValueError as e:
        raise click.BadParameter(f"Invalid pins format: {e}")

    pi = create_pi()

    try:
        # Load calibrations from config file
        manager = ConfigManager(config)
        manager.load()

        # Build calibrations dict for pins referenced in command
        calibrations = {}
        for pin in pin_list:
            calibrations[pin] = manager.get_calibration(pin)

        if debug:
            click.echo(f"Pins: {pin_list}")
            click.echo(f"Config: {config}")
            click.echo(f"Calibrations: {calibrations}")

        # Create servo group with calibrations
        group = ServoGroup(
            pi=pi,
            pins=pin_list,
            calibrations=calibrations,
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
