"""CLI status command - show servo system status."""


import click


@click.command("status")
@click.option(
    "-c", "--config",
    type=click.Path(),
    default="servo.json",
    help="Path to configuration file.",
)
@click.option(
    "-p", "--pins",
    default="20,21,22,23",
    help="Comma-separated list of GPIO pins.",
)
def status(config: str, pins: str):
    """Show servo system status.

    Displays pigpio connection status and configured servos.

    Examples:
        pi0servo status
        pi0servo status -p 20,21
    """
    from ..config import ConfigManager

    # Check pigpio
    click.echo("=== Pi0Servo Status ===\n")

    click.echo("pigpio daemon:")
    try:
        import pigpio
        pi = pigpio.pi()
        if pi.connected:
            click.echo("  ✓ Connected")
            pi.stop()
        else:
            click.echo("  ✗ Not connected")
            click.echo("  Run 'sudo pigpiod' to start")
    except ImportError:
        click.echo("  ✗ pigpio not installed")
        click.echo("  (This is normal on PC/Mac)")

    # Parse pins
    click.echo("\nConfigured pins:")
    try:
        pin_list = [int(p.strip()) for p in pins.split(",")]
    except ValueError:
        click.echo("  Error: Invalid pins format")
        return

    # Load config
    manager = ConfigManager(config)
    loaded = manager.load()

    for pin in pin_list:
        cal = manager.get_calibration(pin)
        has_custom = loaded and pin in manager._data
        marker = "✓" if has_custom else "○"
        click.echo(f"  {marker} Pin {pin}: speed={cal.speed}%")

    click.echo(f"\nConfig file: {config}")
    click.echo(f"  {'✓ Exists' if manager.exists() else '○ Not found (using defaults)'}")
