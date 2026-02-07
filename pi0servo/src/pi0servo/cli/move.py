"""CLI single servo movement command."""

import sys
import time

import click

from ..config import ConfigManager
from ..core import Servo


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
        click.echo("Error: pigpio not available.", err=True)
        sys.exit(1)


# Special position keywords
POSITION_KEYWORDS = {
    "min": -90.0,
    "m": -90.0,
    "center": 0.0,
    "c": 0.0,
    "max": 90.0,
    "x": 90.0,
}


@click.command("move")
@click.argument("pin", type=int)
@click.argument("angle", type=str)  # Use str to avoid Click's option parsing of negative numbers
@click.option(
    "-c", "--config",
    type=click.Path(),
    default="servo.json",
    help="Path to servo configuration file.",
)
@click.option(
    "-s", "--sleep",
    type=float,
    default=1.0,
    help="Time to hold position before turning off (seconds).",
)
@click.option(
    "-d", "--debug",
    is_flag=True,
    help="Enable debug output.",
)
def move(pin: int, angle: str, config: str, sleep: float, debug: bool):
    """Move a single servo to an angle or position.

    PIN: GPIO pin number (e.g., 20)
    ANGLE: Target angle (-90 to 90) or keyword (min, center, max)

    Examples:\n
        pi0servo move 20 45       # Move to 45°\n
        pi0servo move 20 -90      # Move to -90°\n
        pi0servo move 20 center   # Move to center (0°)\n
        pi0servo move 20 min      # Move to minimum (-90°)\n
    """
    # Parse angle - support keywords and numeric values
    angle_lower = angle.lower()
    if angle_lower in POSITION_KEYWORDS:
        angle_val = POSITION_KEYWORDS[angle_lower]
    else:
        try:
            angle_val = float(angle)
        except ValueError:
            raise click.BadParameter(
                f"Invalid angle '{angle}'. Use a number (-90 to 90) or keyword (min, center, max)."
            )

    # Validate angle range
    if angle_val < -90.0 or angle_val > 90.0:
        raise click.BadParameter(f"Angle {angle_val} out of range (-90 to 90).")

    pi = create_pi()

    try:
        # Load calibration if available
        calibration = None
        manager = ConfigManager(config)
        manager.load()
        calibration = manager.get_calibration(pin)

        if debug:
            click.echo(f"Config: {config}")
            click.echo(f"Calibration: {calibration}")

        # Create servo
        servo = Servo(pi, pin, calibration)

        click.echo(f"Moving GPIO{pin} to {angle_val}°")
        servo.set_angle(angle_val)

        # Hold position
        time.sleep(sleep)
        click.echo("✓ Done")

    finally:
        pi.stop()
