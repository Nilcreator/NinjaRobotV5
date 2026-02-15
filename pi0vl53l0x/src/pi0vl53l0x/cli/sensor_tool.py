"""VL53L0X sensor CLI tool.

Provides commands for standalone sensor testing and calibration:

    pi0vl53l0x get           Read distance measurements
    pi0vl53l0x performance   Measure readings per second
    pi0vl53l0x calibrate     Guided offset calibration
    pi0vl53l0x test          Quick sensor validation
    pi0vl53l0x status        Sensor health report
    pi0vl53l0x config show   Display current config
    pi0vl53l0x config export Export config to file
    pi0vl53l0x config import Import config from file

Note: Requires pigpio daemon running on Raspberry Pi.
"""

from __future__ import annotations

import sys
import time

import click

from pi0vl53l0x.config.config_manager import (
    ConfigManager,
    get_default_config_filepath,
    save_config,
)


def _connect_pigpio() -> object:
    """Connect to the pigpio daemon.

    Returns:
        pigpio.pi instance.

    Raises:
        click.ClickException: If pigpio is not available or
            the daemon is not running.
    """
    try:
        import pigpio  # type: ignore[import-untyped]
    except ImportError:
        raise click.ClickException(
            "pigpio is not installed. Install with: pip install pigpio"
        )

    pi = pigpio.pi()
    if not pi.connected:
        raise click.ClickException(
            "Cannot connect to pigpiod. "
            "Start it with: sudo pigpiod"
        )
    return pi


def _create_sensor(pi: object, ctx: click.Context) -> object:
    """Create a VL53L0X sensor instance.

    Args:
        pi: pigpio.pi instance.
        ctx: Click context with config_file path.

    Returns:
        VL53L0X sensor instance.
    """
    from pi0vl53l0x.core.sensor import VL53L0X

    config_path = ctx.obj.get("config_file")
    config_mgr = ConfigManager(config_path)
    offset = config_mgr.get("offset_mm", 0)

    sensor = VL53L0X(pi)
    if offset:
        sensor.set_offset(offset)
    return sensor


# -------------------------------------------------------------------
# Main CLI group
# -------------------------------------------------------------------


@click.group(
    invoke_without_command=True,
    help="VL53L0X Time-of-Flight distance sensor CLI tool.",
)
@click.pass_context
@click.option(
    "--config-file",
    "-C",
    type=str,
    default=str(get_default_config_filepath()),
    show_default=True,
    help="Path to the configuration file.",
)
@click.option("--debug", "-d", is_flag=True, help="Enable debug mode.")
def cli(ctx: click.Context, debug: bool, config_file: str) -> None:
    """VL53L0X distance sensor CLI tool."""
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config_file
    ctx.obj["debug"] = debug

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# -------------------------------------------------------------------
# get: Read distance measurements
# -------------------------------------------------------------------


@cli.command(help="Read distance measurements.")
@click.pass_context
@click.option(
    "--count",
    "-c",
    type=int,
    default=10,
    show_default=True,
    help="Number of readings.",
)
@click.option(
    "--interval",
    "-i",
    type=float,
    default=1.0,
    show_default=True,
    help="Interval between readings (seconds).",
)
def get(ctx: click.Context, count: int, interval: float) -> None:
    """Read distance measurements from the sensor."""
    pi = _connect_pigpio()
    try:
        sensor = _create_sensor(pi, ctx)
        try:
            for i in range(count):
                distance = sensor.get_range()
                if distance > 0:
                    click.echo(f"{i + 1}/{count}: {distance} mm")
                else:
                    click.echo(f"{i + 1}/{count}: Invalid data")
                if i < count - 1:
                    time.sleep(interval)
        except Exception as exc:
            if ctx.obj["debug"]:
                raise
            click.echo(f"Error: {exc}")
        finally:
            sensor.close()
    finally:
        pi.stop()  # type: ignore[attr-defined]


# -------------------------------------------------------------------
# performance: Measure readings per second
# -------------------------------------------------------------------


@cli.command(help="Measure sensor reading performance.")
@click.pass_context
@click.option(
    "--count",
    "-c",
    type=int,
    default=100,
    show_default=True,
    help="Number of readings to measure.",
)
def performance(ctx: click.Context, count: int) -> None:
    """Measure how many readings per second the sensor can produce."""
    pi = _connect_pigpio()
    try:
        sensor = _create_sensor(pi, ctx)
        try:
            click.echo(
                f"Measuring performance with {count} readings..."
            )
            start_time = time.perf_counter()
            for _ in range(count):
                sensor.get_range()
            end_time = time.perf_counter()

            total_time = end_time - start_time
            avg_ms = (total_time / count) * 1000
            readings_per_sec = count / total_time

            click.echo("---")
            click.echo(f"Total time: {total_time:.4f} s")
            click.echo(f"Average per reading: {avg_ms:.4f} ms")
            click.echo(
                f"Readings per second: {readings_per_sec:.2f} Hz"
            )
            click.echo("---")
        except Exception as exc:
            if ctx.obj["debug"]:
                raise
            click.echo(f"Error: {exc}")
        finally:
            sensor.close()
    finally:
        pi.stop()  # type: ignore[attr-defined]


# -------------------------------------------------------------------
# calibrate: Guided offset calibration
# -------------------------------------------------------------------


@cli.command(help="Guided offset calibration.")
@click.pass_context
@click.option(
    "--distance",
    "-D",
    type=int,
    default=100,
    show_default=True,
    help="Target distance in mm.",
)
@click.option(
    "--count",
    "-c",
    type=int,
    default=10,
    show_default=True,
    help="Number of samples.",
)
def calibrate(ctx: click.Context, distance: int, count: int) -> None:
    """Run guided offset calibration.

    Place a target at the specified distance from the sensor,
    then this command measures the offset.
    """
    pi = _connect_pigpio()
    try:
        sensor = _create_sensor(pi, ctx)
        try:
            click.echo(
                f"Place a target at {distance}mm from the sensor."
            )
            click.echo("Press Enter when ready...")
            input()

            offset = sensor.calibrate(
                target_distance_mm=distance,
                num_samples=count,
            )

            click.echo(f"Calculated offset: {offset} mm")

            # Save to config
            config_path = ctx.obj["config_file"]
            save_config(config_path, {"offset_mm": offset})
            click.echo(f"Offset saved to {config_path}")
        except Exception as exc:
            if ctx.obj["debug"]:
                raise
            click.echo(f"Error: {exc}")
        finally:
            sensor.close()
    finally:
        pi.stop()  # type: ignore[attr-defined]


# -------------------------------------------------------------------
# test: Quick sensor validation
# -------------------------------------------------------------------


@cli.command(help="Quick sensor validation (init + 5 readings).")
@click.pass_context
def test(ctx: click.Context) -> None:
    """Quick sensor validation: initialize and take 5 readings."""
    pi = _connect_pigpio()
    try:
        click.echo("Initializing sensor...")
        sensor = _create_sensor(pi, ctx)
        click.echo("  OK - Sensor initialized")

        try:
            click.echo("Taking 5 test readings:")
            for i in range(5):
                distance = sensor.get_range()
                status = "OK" if 0 < distance < 8190 else "WARN"
                click.echo(f"  [{status}] Reading {i + 1}: {distance} mm")
                time.sleep(0.5)

            click.echo("\nSensor test PASSED")
        except Exception as exc:
            click.echo(f"\nSensor test FAILED: {exc}")
            sys.exit(1)
        finally:
            sensor.close()
    except click.ClickException:
        raise
    except Exception as exc:
        click.echo(f"Initialization FAILED: {exc}")
        sys.exit(1)
    finally:
        pi.stop()  # type: ignore[attr-defined]


# -------------------------------------------------------------------
# status: Sensor health report
# -------------------------------------------------------------------


@cli.command(help="Sensor health report.")
@click.pass_context
def status(ctx: click.Context) -> None:
    """Display sensor health report: model ID, connection, test reading."""
    pi = _connect_pigpio()
    try:
        click.echo("=== VL53L0X Status Report ===")
        click.echo()

        sensor = _create_sensor(pi, ctx)
        try:
            # Health check
            healthy = sensor.health_check()
            click.echo(
                f"  Health Check: {'PASS' if healthy else 'FAIL'}"
            )

            # Test reading
            try:
                distance = sensor.get_range()
                click.echo(f"  Test Reading: {distance} mm")
            except Exception as exc:
                click.echo(f"  Test Reading: FAILED ({exc})")

            # Config info
            config_mgr = ConfigManager(ctx.obj["config_file"])
            offset = config_mgr.get("offset_mm", 0)
            click.echo(f"  Offset: {offset} mm")
            click.echo(f"  Config: {config_mgr.path}")

            click.echo()
            overall = "OK" if healthy else "DEGRADED"
            click.echo(f"  Overall: {overall}")
        finally:
            sensor.close()
    except click.ClickException:
        raise
    except Exception as exc:
        click.echo(f"  Status check FAILED: {exc}")
        sys.exit(1)
    finally:
        pi.stop()  # type: ignore[attr-defined]


# -------------------------------------------------------------------
# config: Configuration management subgroup
# -------------------------------------------------------------------


@cli.group(help="Configuration management commands.")
def config() -> None:
    """Manage VL53L0X configuration."""


@config.command("show", help="Display current configuration.")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Display current configuration contents."""
    import json

    config_mgr = ConfigManager(ctx.obj["config_file"])
    click.echo(json.dumps(config_mgr.config, indent=2))


@config.command("export", help="Export config to a file.")
@click.argument("file")
@click.pass_context
def config_export(ctx: click.Context, file: str) -> None:
    """Export current configuration to a backup file."""
    config_mgr = ConfigManager(ctx.obj["config_file"])
    config_mgr.export_config(file)
    click.echo(f"Config exported to {file}")


@config.command("import", help="Import config from a file.")
@click.argument("file")
@click.pass_context
def config_import(ctx: click.Context, file: str) -> None:
    """Import configuration from a file."""
    config_mgr = ConfigManager(ctx.obj["config_file"])
    config_mgr.import_config(file)
    config_mgr.save()
    click.echo(f"Config imported from {file}")


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    cli(obj={})  # pylint: disable=no-value-for-parameter
