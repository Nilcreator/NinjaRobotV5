"""CLI single servo movement command."""

import sys

import click

from ..core import Servo


def create_pi():
    """Create pigpio connection (only on Raspberry Pi)."""
    try:
        import pigpio
        pi = pigpio.pi()
        if not pi.connected:
            click.echo("Error: Could not connect to pigpio daemon.", err=True)
            sys.exit(1)
        return pi
    except ImportError:
        click.echo("Error: pigpio not available.", err=True)
        sys.exit(1)


@click.command("move")
@click.argument("pin", type=int)
@click.argument("angle", type=float)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    help="Path to servo configuration file.",
)
def move(pin: int, angle: float, config: str | None):
    """Move a single servo to an angle.

    PIN: GPIO pin number (e.g., 20)
    ANGLE: Target angle in degrees (-90 to 90)

    Examples:
        pi0servo move 20 45
        pi0servo move 21 -30
        pi0servo move 20 0  # center
    """
    pi = create_pi()

    try:
        # Create servo (with optional config)
        if config:
            from ..config import ConfigManager
            manager = ConfigManager(config)
            manager.load()
            calibration = manager.get_calibration(pin)
            servo = Servo(pi, pin, calibration)
        else:
            servo = Servo(pi, pin)

        click.echo(f"Moving pin {pin} to {angle}°")
        servo.set_angle(angle)
        click.echo("✓ Done")

    finally:
        pi.stop()
