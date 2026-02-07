"""Config management CLI commands.

Provides commands for viewing, exporting, and importing servo configurations.

Usage:
    uv run pi0servo config show
    uv run pi0servo config export <path>
    uv run pi0servo config import <path>
"""

import json
from pathlib import Path

import click


@click.group("config")
def config_cmd():
    """Manage servo configuration files."""
    pass


@config_cmd.command("show")
@click.option(
    "-c",
    "--config",
    "config_path",
    default="servo.json",
    help="Path to calibration config file.",
)
@click.option(
    "-p",
    "--pin",
    type=int,
    default=None,
    help="Show only this pin's configuration.",
)
def show_config(config_path: str, pin: int | None):
    """Display current servo configuration."""
    from ..config import ConfigManager

    manager = ConfigManager(config_path)
    manager.load()

    configs = manager.get_all_calibrations()

    if not configs:
        click.echo("No servos configured. Run calibration first.")
        return

    click.echo("=== Servo Configuration ===")

    if pin is not None:
        if pin in configs:
            cal = configs[pin]
            click.echo(f"\nGPIO{pin}:")
            click.echo(f"  pulse_min:    {cal.pulse_min}")
            click.echo(f"  pulse_center: {cal.pulse_center}")
            click.echo(f"  pulse_max:    {cal.pulse_max}")
            click.echo(f"  angle_min:    {cal.angle_min}")
            click.echo(f"  angle_center: {cal.angle_center}")
            click.echo(f"  angle_max:    {cal.angle_max}")
            click.echo(f"  speed:        {cal.speed}%")
        else:
            click.echo(f"GPIO{pin}: Not configured")
    else:
        for pin_num, cal in configs.items():
            click.echo(
                f"  GPIO{pin_num}: "
                f"pulse=[{cal.pulse_min}, {cal.pulse_center}, {cal.pulse_max}] "
                f"speed={cal.speed}%"
            )


@config_cmd.command("export")
@click.argument("output_path", type=click.Path())
@click.option(
    "-c",
    "--config",
    "config_path",
    default="servo.json",
    help="Source config file.",
)
def export_config(output_path: str, config_path: str):
    """Export configuration to a file."""
    from ..config import ConfigManager

    manager = ConfigManager(config_path)
    manager.load()

    # Export to target path
    output = Path(output_path)
    data = manager._to_dict()

    with output.open("w") as f:
        json.dump(data, f, indent=2)

    click.echo(f"✓ Exported to {output_path}")


@config_cmd.command("import")
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "-c",
    "--config",
    "config_path",
    default="servo.json",
    help="Target config file.",
)
@click.option(
    "--merge/--replace",
    default=True,
    help="Merge with existing or replace entirely.",
)
def import_config(input_path: str, config_path: str, merge: bool):
    """Import configuration from a file."""
    from ..config import ConfigManager

    manager = ConfigManager(config_path)

    if merge:
        manager.load()  # Load existing first

    # Load from input
    input_file = Path(input_path)
    with input_file.open() as f:
        data = json.load(f)

    # Apply each calibration
    from ..core import ServoCalibration

    for pin_str, cal_data in data.items():
        pin = int(pin_str)
        cal = ServoCalibration(
            pulse_min=cal_data.get("pulse_min", 500),
            pulse_max=cal_data.get("pulse_max", 2500),
            pulse_center=cal_data.get("pulse_center", 1500),
            angle_min=cal_data.get("angle_min", -90.0),
            angle_max=cal_data.get("angle_max", 90.0),
            angle_center=cal_data.get("angle_center", 0.0),
            speed=cal_data.get("speed", 80),
        )
        manager.set_calibration(pin, cal)

    manager.save()
    click.echo(f"✓ Imported from {input_path}")
    click.echo(f"  Mode: {'merge' if merge else 'replace'}")
