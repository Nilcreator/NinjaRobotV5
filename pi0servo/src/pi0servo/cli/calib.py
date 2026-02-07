"""CLI calibration command - show and set servo calibration."""

import sys

import click

from ..config import ConfigManager
from ..core import ServoCalibration


@click.command("calib")
@click.argument("pin", type=int, required=False)
@click.option(
    "-c", "--config",
    type=click.Path(),
    default="servo.json",
    help="Path to configuration file.",
)
@click.option(
    "--min", "pulse_min",
    type=int,
    help="Set minimum pulse width (µs).",
)
@click.option(
    "--max", "pulse_max",
    type=int,
    help="Set maximum pulse width (µs).",
)
@click.option(
    "--center", "pulse_center",
    type=int,
    help="Set center pulse width (µs).",
)
@click.option(
    "--speed",
    type=int,
    help="Set speed limit (0-100%).",
)
@click.option(
    "--show", is_flag=True,
    help="Show current calibration.",
)
def calib(
    pin: int | None,
    config: str,
    pulse_min: int | None,
    pulse_max: int | None,
    pulse_center: int | None,
    speed: int | None,
    show: bool,
):
    """View or set servo calibration.

    PIN: GPIO pin number (optional, shows all if not specified)

    Examples:
        pi0servo calib                    # Show all
        pi0servo calib 20 --show          # Show pin 20
        pi0servo calib 20 --speed 100     # Set speed to 100%
        pi0servo calib 20 --min 600       # Set min pulse
    """
    manager = ConfigManager(config)
    manager.load()

    # Show mode
    if show or (pin is None and all(v is None for v in [pulse_min, pulse_max, pulse_center, speed])):
        if pin is not None:
            cal = manager.get_calibration(pin)
            _print_calibration(pin, cal)
        else:
            all_cals = manager.get_all_calibrations()
            if not all_cals:
                click.echo("No calibrations stored.")
            else:
                for p, cal in sorted(all_cals.items()):
                    _print_calibration(p, cal)
        return

    # Set mode requires pin
    if pin is None:
        click.echo("Error: PIN required when setting calibration.", err=True)
        sys.exit(1)

    # Get current or default
    cal = manager.get_calibration(pin)

    # Apply updates
    updates = {}
    if pulse_min is not None:
        updates["pulse_min"] = pulse_min
    if pulse_max is not None:
        updates["pulse_max"] = pulse_max
    if pulse_center is not None:
        updates["pulse_center"] = pulse_center
    if speed is not None:
        if speed < 0 or speed > 100:
            click.echo("Error: Speed must be 0-100.", err=True)
            sys.exit(1)
        updates["speed"] = speed

    # Create new calibration with updates
    new_cal = ServoCalibration(
        pulse_min=updates.get("pulse_min", cal.pulse_min),
        pulse_max=updates.get("pulse_max", cal.pulse_max),
        pulse_center=updates.get("pulse_center", cal.pulse_center),
        angle_min=cal.angle_min,
        angle_max=cal.angle_max,
        angle_center=cal.angle_center,
        speed=updates.get("speed", cal.speed),
    )

    manager.set_calibration(pin, new_cal)
    if manager.save():
        click.echo(f"✓ Saved calibration for pin {pin}")
        _print_calibration(pin, new_cal)
    else:
        click.echo("✗ Failed to save calibration.", err=True)
        sys.exit(1)


def _print_calibration(pin: int, cal: ServoCalibration):
    """Print calibration info for a pin."""
    click.echo(f"Pin {pin}:")
    click.echo(f"  Pulse: {cal.pulse_min} / {cal.pulse_center} / {cal.pulse_max}")
    click.echo(f"  Angle: {cal.angle_min}° / {cal.angle_center}° / {cal.angle_max}°")
    click.echo(f"  Speed: {cal.speed}%")
