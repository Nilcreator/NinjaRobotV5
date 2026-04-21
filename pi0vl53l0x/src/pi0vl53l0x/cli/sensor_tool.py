"""VL53L0X sensor CLI tool.

Provides both individual CLI commands for scripting and an interactive
menu-driven TUI for guided sensor operations.

Usage:
    uv run pi0vl53l0x get                      # Single reading
    uv run pi0vl53l0x get --count 10            # Multiple readings
    uv run pi0vl53l0x sensor-tool               # Interactive TUI

Note: Requires pigpio daemon running on Raspberry Pi.
"""

from __future__ import annotations

import json
import statistics
import time

import click

from pi0vl53l0x.config.config_manager import (
    ConfigManager,
)

# Optional blessed for TUI
try:
    from blessed import Terminal

    HAS_BLESSED = True
except ImportError:
    HAS_BLESSED = False


# -------------------------------------------------------------------
# Shared helpers
# -------------------------------------------------------------------


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
            "pigpio is not installed. Install with:\n"
            "  Standalone: uv sync --extra pi\n"
            "  NinjaRobotV5: uv sync  (pigpio is a main dependency)\n"
            "  Manual: pip install pigpio"
        )

    pi = pigpio.pi()
    if not pi.connected:
        raise click.ClickException(
            "Cannot connect to pigpiod. "
            "Start it with: sudo pigpiod"
        )
    return pi


def _create_sensor(pi: object, config_file: str | None = None) -> object:
    """Create and initialize a VL53L0X sensor.

    Args:
        pi: pigpio.pi instance.
        config_file: Optional config file path.

    Returns:
        VL53L0X sensor instance.

    Raises:
        click.ClickException: If sensor initialization fails.
    """
    from pi0vl53l0x.core.sensor import VL53L0X

    try:
        sensor = VL53L0X(pi, config_file_path=config_file)
        return sensor
    except Exception as exc:
        raise click.ClickException(f"Sensor init failed: {exc}")


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
    default=None,
    help="Path to config file (default: vl53l0x.json).",
)
@click.option("--debug", "-d", is_flag=True, help="Enable debug mode.")
def cli(ctx: click.Context, debug: bool, config_file: str | None) -> None:
    """VL53L0X distance sensor CLI tool."""
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config_file
    ctx.obj["debug"] = debug

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ===================================================================
# Individual CLI Commands (for scripting / non-interactive use)
# ===================================================================


@cli.command()
@click.option(
    "-c",
    "--count",
    default=1,
    show_default=True,
    help="Number of readings.",
)
@click.option(
    "-i",
    "--interval",
    default=0.5,
    show_default=True,
    help="Interval between readings in seconds.",
)
@click.pass_context
def get(ctx: click.Context, count: int, interval: float) -> None:
    """Take distance readings."""
    pi = _connect_pigpio()
    try:
        sensor = _create_sensor(pi, ctx.obj.get("config_file"))
        for n in range(count):
            data = sensor.get_data()
            dist = data["distance_mm"]
            valid = "✓" if data["is_valid"] else "⚠"
            raw = data.get("raw_value", "N/A")
            click.echo(f"  {valid} {dist} mm  (raw: {raw} mm)")
            if n < count - 1:
                time.sleep(interval)
        sensor.close()
    finally:
        pi.stop()  # type: ignore[attr-defined]


@cli.command()
@click.option(
    "-c",
    "--count",
    default=100,
    show_default=True,
    help="Number of samples.",
)
@click.pass_context
def performance(ctx: click.Context, count: int) -> None:
    """Measure readings per second (benchmark)."""
    pi = _connect_pigpio()
    try:
        sensor = _create_sensor(pi, ctx.obj.get("config_file"))
        click.echo(f"Running {count} readings...")

        distances: list[int] = []
        errors = 0
        start = time.time()

        for _ in range(count):
            try:
                distances.append(sensor.get_range())
            except Exception:
                errors += 1

        elapsed = time.time() - start
        hz = len(distances) / elapsed if elapsed > 0 else 0

        click.echo(f"  Readings:  {len(distances)} / {count}")
        click.echo(f"  Errors:    {errors}")
        click.echo(f"  Time:      {elapsed:.2f}s")
        click.echo(f"  Speed:     {hz:.1f} Hz")
        if distances:
            click.echo(
                f"  Mean:      {statistics.mean(distances):.0f} mm"
            )
            click.echo(f"  Min:       {min(distances)} mm")
            click.echo(f"  Max:       {max(distances)} mm")
            if len(distances) >= 2:
                click.echo(
                    f"  Std Dev:   "
                    f"{statistics.stdev(distances):.1f} mm"
                )
        sensor.close()
    finally:
        pi.stop()  # type: ignore[attr-defined]


@cli.command()
@click.option(
    "-d",
    "--distance",
    required=True,
    type=int,
    help="Target distance in mm.",
)
@click.option(
    "-c",
    "--count",
    default=10,
    show_default=True,
    help="Number of calibration samples.",
)
@click.pass_context
def calibrate(ctx: click.Context, distance: int, count: int) -> None:
    """Calibrate sensor offset at a known distance."""
    pi = _connect_pigpio()
    try:
        sensor = _create_sensor(pi, ctx.obj.get("config_file"))
        click.echo(
            f"Calibrating at {distance}mm with {count} samples..."
        )
        offset = sensor.calibrate(distance, count)
        click.echo(f"  Calculated offset: {offset} mm")
        sensor.set_offset(offset)

        manager = ConfigManager(ctx.obj.get("config_file"))
        manager.set("offset_mm", offset)
        manager.save()
        click.echo(f"  ✓ Offset saved to {manager.path}")
        sensor.close()
    finally:
        pi.stop()  # type: ignore[attr-defined]


@cli.command()
@click.pass_context
def test(ctx: click.Context) -> None:
    """Quick sensor test (5 readings)."""
    pi = _connect_pigpio()
    try:
        sensor = _create_sensor(pi, ctx.obj.get("config_file"))
        click.echo("VL53L0X Quick Test")
        click.echo(f"  Offset: {sensor.offset_mm} mm")

        for i in range(5):
            try:
                dist = sensor.get_range()
                click.echo(f"  [{i + 1}] {dist} mm")
            except Exception as e:
                click.echo(f"  [{i + 1}] Error: {e}")
            time.sleep(0.3)
        click.echo("  ✓ Test complete")
        sensor.close()
    finally:
        pi.stop()  # type: ignore[attr-defined]


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Full sensor health and diagnostics report."""
    pi = _connect_pigpio()
    try:
        sensor = _create_sensor(pi, ctx.obj.get("config_file"))
        click.echo("VL53L0X Status Report")

        healthy = sensor.health_check()
        click.echo(
            f"  Health:   {'✓ OK' if healthy else '✗ FAILED'}"
        )
        click.echo(f"  Offset:   {sensor.offset_mm} mm")

        try:
            dist = sensor.get_range()
            click.echo(f"  Reading:  {dist} mm")
        except Exception as e:
            click.echo(f"  Reading:  Error: {e}")

        manager = ConfigManager(ctx.obj.get("config_file"))
        cfg = manager.config
        if cfg:
            click.echo("  Config:")
            for key, val in cfg.items():
                click.echo(f"    {key}: {val}")
        else:
            click.echo("  Config:   (defaults)")

        sensor.close()
    finally:
        pi.stop()  # type: ignore[attr-defined]


@cli.group()
def config() -> None:
    """Configuration management (show/export/import)."""


@config.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Show current sensor configuration."""
    manager = ConfigManager(ctx.obj.get("config_file"))
    cfg = manager.config
    if cfg:
        click.echo(json.dumps(cfg, indent=2))
    else:
        click.echo("(empty — using defaults)")
    click.echo(f"Config file: {manager.path}")


@config.command("export")
@click.argument("path")
@click.pass_context
def config_export(ctx: click.Context, path: str) -> None:
    """Export configuration to a file."""
    manager = ConfigManager(ctx.obj.get("config_file"))
    manager.export_config(path)
    click.echo(f"✓ Config exported to {path}")


@config.command("import")
@click.argument("path")
@click.pass_context
def config_import(ctx: click.Context, path: str) -> None:
    """Import configuration from a file."""
    manager = ConfigManager(ctx.obj.get("config_file"))
    manager.import_config(path)
    manager.save()
    click.echo(f"✓ Config imported from {path}")


# ===================================================================
# sensor-tool: Interactive TUI
# ===================================================================


@cli.command("sensor-tool")
@click.option(
    "-c",
    "--config",
    "config_path",
    default=None,
    help="Path to sensor config file (default: vl53l0x.json).",
)
def sensor_tool(config_path: str | None) -> None:
    """Interactive VL53L0X distance sensor tool (TUI)."""
    if not HAS_BLESSED:
        click.echo("❌ 'blessed' library required for interactive mode.")
        click.echo("   Install with: pip install blessed")
        return

    # --- Connect to pigpio ---
    try:
        pi = _connect_pigpio()
    except click.ClickException as e:
        click.echo(f"❌ {e.message}")
        return

    # --- Initialize sensor & config ---
    try:
        from pi0vl53l0x.core.sensor import VL53L0X

        manager = ConfigManager(config_path)
        offset = manager.get("offset_mm", 0)

        sensor = VL53L0X(pi)
        if offset:
            sensor.set_offset(offset)

        term = Terminal()
        running = True

        click.echo(term.green("✓ Sensor initialized (VL53L0X)"))
        click.echo(term.green(f"  Offset: {offset} mm"))
        click.echo(term.green(f"  Config: {manager.path}"))

        # ==============================================================
        # Menu functions
        # ==============================================================

        def show_menu() -> None:
            """Display main menu."""
            click.echo(term.clear())
            click.echo(term.bold("╔" + "═" * 62 + "╗"))
            click.echo(
                term.bold("║")
                + term.cyan("            pi0vl53l0x Interactive Tool")
                + " " * 22
                + term.bold("║")
            )
            click.echo(term.bold("╠" + "═" * 62 + "╣"))
            click.echo(
                term.bold("║")
                + "  1. Single Read      - Take one distance measurement        "
                + term.bold("║")
            )
            click.echo(
                term.bold("║")
                + "  2. Continuous Read  - Stream readings at interval          "
                + term.bold("║")
            )
            click.echo(
                term.bold("║")
                + "  3. Performance      - Measure readings per second          "
                + term.bold("║")
            )
            click.echo(
                term.bold("║")
                + "  4. Calibrate        - Guided offset calibration            "
                + term.bold("║")
            )
            click.echo(
                term.bold("║")
                + "  5. Health Check     - Verify sensor connection             "
                + term.bold("║")
            )
            click.echo(
                term.bold("║")
                + "  6. Status           - Full sensor diagnostics              "
                + term.bold("║")
            )
            click.echo(
                term.bold("║")
                + "  7. Config           - Show/export/import settings          "
                + term.bold("║")
            )
            click.echo(
                term.bold("║")
                + "  8. Reinitialize     - Reset sensor (recovery)             "
                + term.bold("║")
            )
            click.echo(
                term.bold("║")
                + "  q. Exit                                                    "
                + term.bold("║")
            )
            click.echo(term.bold("╚" + "═" * 62 + "╝"))
            click.echo()

        def tui_single_read() -> None:
            """Take single distance readings."""
            click.echo("\n" + term.cyan("=== Single Read Mode ==="))
            click.echo("Press Enter for a reading. Type 'q' to return.\n")

            while True:
                cmd = input("> ").strip().lower()
                if cmd in ("q", "b", "quit", "back"):
                    break

                try:
                    data = sensor.get_data()
                    dist = data["distance_mm"]
                    valid = data["is_valid"]
                    raw = data.get("raw_value", "N/A")

                    if valid:
                        click.echo(
                            term.green(f"  ✓ {dist} mm")
                            + f"  (raw: {raw} mm)"
                        )
                    else:
                        click.echo(
                            term.yellow(f"  ⚠ {dist} mm (invalid)")
                            + f"  (raw: {raw} mm)"
                        )
                except Exception as e:
                    click.echo(term.red(f"  ✗ Error: {e}"))

        def tui_continuous_read() -> None:
            """Stream distance readings at a set interval."""
            click.echo("\n" + term.cyan("=== Continuous Read Mode ==="))

            click.echo(term.yellow("Number of readings (0 = unlimited):"))
            try:
                count = int(input("> ").strip() or "0")
            except ValueError:
                click.echo(term.red("Invalid number"))
                input("\nPress Enter to continue...")
                return

            click.echo(term.yellow("Interval in ms (default 500):"))
            try:
                interval_ms = int(input("> ").strip() or "500")
            except ValueError:
                click.echo(term.red("Invalid interval"))
                input("\nPress Enter to continue...")
                return

            interval_s = interval_ms / 1000.0
            click.echo(
                f"\nStreaming every {interval_ms}ms. "
                "Press Ctrl+C to stop.\n"
            )

            readings = 0
            try:
                while count == 0 or readings < count:
                    try:
                        dist = sensor.get_range()
                        readings += 1
                        bar_len = min(dist // 20, 40)
                        bar = "█" * bar_len
                        click.echo(
                            f"  [{readings:4d}] "
                            + term.green(f"{dist:5d} mm ")
                            + term.cyan(bar)
                        )
                    except Exception as e:
                        readings += 1
                        click.echo(
                            f"  [{readings:4d}] "
                            + term.red(f"Error: {e}")
                        )
                    time.sleep(interval_s)
            except KeyboardInterrupt:
                click.echo(
                    term.yellow(
                        f"\n  Stopped after {readings} readings."
                    )
                )

            input("\nPress Enter to continue...")

        def tui_performance() -> None:
            """Measure readings per second."""
            click.echo("\n" + term.cyan("=== Performance Test ==="))

            click.echo(term.yellow("Number of samples (default 100):"))
            try:
                num = int(input("> ").strip() or "100")
            except ValueError:
                click.echo(term.red("Invalid number"))
                input("\nPress Enter to continue...")
                return

            click.echo(
                f"\nRunning {num} readings as fast as possible...\n"
            )

            distances: list[int] = []
            errors = 0
            start = time.time()

            for _i in range(num):
                try:
                    dist = sensor.get_range()
                    distances.append(dist)
                except Exception:
                    errors += 1

            elapsed = time.time() - start
            hz = len(distances) / elapsed if elapsed > 0 else 0

            click.echo(term.bold("Results:"))
            click.echo(f"  Readings:  {len(distances)} / {num}")
            click.echo(f"  Errors:    {errors}")
            click.echo(f"  Time:      {elapsed:.2f}s")
            click.echo(term.green(f"  Speed:     {hz:.1f} Hz"))

            if distances:
                click.echo(
                    f"  Mean:      "
                    f"{statistics.mean(distances):.0f} mm"
                )
                click.echo(f"  Min:       {min(distances)} mm")
                click.echo(f"  Max:       {max(distances)} mm")
                if len(distances) >= 2:
                    click.echo(
                        f"  Std Dev:   "
                        f"{statistics.stdev(distances):.1f} mm"
                    )

            input("\nPress Enter to continue...")

        def tui_calibrate() -> None:
            """Guided offset calibration."""
            click.echo("\n" + term.cyan("=== Calibration ==="))
            click.echo(
                "Place a flat target at a known distance "
                "from the sensor.\n"
                "The sensor will take multiple readings "
                "and calculate the offset.\n"
            )

            click.echo(
                term.yellow("Target distance in mm (e.g. 200):")
            )
            try:
                target = int(input("> ").strip())
                if target <= 0:
                    click.echo(term.red("Distance must be positive"))
                    input("\nPress Enter to continue...")
                    return
            except ValueError:
                click.echo(term.red("Invalid distance"))
                input("\nPress Enter to continue...")
                return

            click.echo(
                term.yellow("Number of samples (default 20):")
            )
            try:
                samples = int(input("> ").strip() or "20")
            except ValueError:
                click.echo(term.red("Invalid number"))
                input("\nPress Enter to continue...")
                return

            click.echo(
                f"\nMeasuring {samples} samples "
                f"at {target}mm target..."
            )

            try:
                new_offset = sensor.calibrate(target, samples)

                click.echo(
                    term.green(
                        f"\n  ✓ Calculated offset: {new_offset} mm"
                    )
                )
                click.echo(
                    f"  (Current offset: {sensor.offset_mm} mm)"
                )

                click.echo(
                    term.yellow("\nApply this offset? (y/n):")
                )
                if input("> ").strip().lower() == "y":
                    sensor.set_offset(new_offset)
                    manager.set("offset_mm", new_offset)
                    manager.save()
                    click.echo(
                        term.green("  ✓ Offset applied and saved")
                    )
                else:
                    click.echo("  Offset not applied.")

            except Exception as e:
                click.echo(
                    term.red(f"  ✗ Calibration failed: {e}")
                )

            input("\nPress Enter to continue...")

        def tui_health_check() -> None:
            """Quick sensor health check."""
            click.echo("\n" + term.cyan("=== Health Check ==="))

            try:
                healthy = sensor.health_check()
                if healthy:
                    click.echo(
                        term.green(
                            "  ✓ Sensor is responding correctly"
                        )
                    )
                    dist = sensor.get_range()
                    click.echo(
                        term.green(f"  ✓ Test reading: {dist} mm")
                    )
                else:
                    click.echo(
                        term.red("  ✗ Sensor health check failed")
                    )
                    click.echo(
                        "    Try option 8 (Reinitialize) to recover."
                    )
            except Exception as e:
                click.echo(term.red(f"  ✗ Error: {e}"))

            input("\nPress Enter to continue...")

        def tui_status() -> None:
            """Show full sensor diagnostics."""
            click.echo("\n" + term.cyan("=== Sensor Status ==="))

            try:
                healthy = sensor.health_check()
                status_str = (
                    term.green("OK")
                    if healthy
                    else term.red("FAILED")
                )
            except Exception:
                status_str = term.red("ERROR")

            click.echo(f"  Health:     {status_str}")
            click.echo(f"  Offset:     {sensor.offset_mm} mm")
            click.echo(f"  Config:     {manager.path}")

            cfg = manager.config
            if cfg:
                click.echo("  Settings:")
                for key, value in cfg.items():
                    click.echo(f"    {key}: {value}")
            else:
                click.echo("  Settings:   (defaults)")

            try:
                dist = sensor.get_range()
                click.echo(
                    "  Reading:    " + term.green(f"{dist} mm")
                )
            except Exception as e:
                click.echo(
                    "  Reading:    " + term.red(f"Error: {e}")
                )

            input("\nPress Enter to continue...")

        def tui_config_menu() -> None:
            """Config management submenu."""
            click.echo(
                "\n" + term.cyan("=== Config Management ===")
            )
            click.echo(f"  File: {manager.path}\n")
            click.echo("  1. Show current config")
            click.echo("  2. Export to file")
            click.echo("  3. Import from file")
            click.echo("  b. Back")

            choice = input("\nChoice: ").strip().lower()

            if choice == "1":
                cfg = manager.config
                if cfg:
                    click.echo("\n" + json.dumps(cfg, indent=2))
                else:
                    click.echo("\n  (empty — using defaults)")

            elif choice == "2":
                click.echo(term.yellow("Enter export path:"))
                path = input("> ").strip()
                if path:
                    try:
                        manager.export_config(path)
                        click.echo(
                            term.green(f"  ✓ Exported to {path}")
                        )
                    except Exception as e:
                        click.echo(
                            term.red(f"  ✗ Export failed: {e}")
                        )

            elif choice == "3":
                click.echo(term.yellow("Enter import path:"))
                path = input("> ").strip()
                if path:
                    try:
                        manager.import_config(path)
                        manager.save()
                        imported_offset = manager.get(
                            "offset_mm", 0
                        )
                        sensor.set_offset(imported_offset)
                        click.echo(
                            term.green(
                                f"  ✓ Imported from {path}"
                            )
                        )
                        click.echo(
                            f"  Applied offset: "
                            f"{imported_offset} mm"
                        )
                    except Exception as e:
                        click.echo(
                            term.red(f"  ✗ Import failed: {e}")
                        )

            input("\nPress Enter to continue...")

        def tui_reinitialize() -> None:
            """Reinitialize sensor for recovery."""
            click.echo(
                "\n" + term.cyan("=== Reinitialize Sensor ===")
            )
            click.echo(
                "This performs a full sensor re-initialization.\n"
                "Use this to recover from a stuck or "
                "unresponsive state.\n"
            )

            click.echo(term.yellow("Proceed? (y/n):"))
            if input("> ").strip().lower() != "y":
                click.echo("  Cancelled.")
                input("\nPress Enter to continue...")
                return

            try:
                sensor.reinitialize()
                click.echo(
                    term.green("  ✓ Sensor reinitialized")
                )

                dist = sensor.get_range()
                click.echo(
                    term.green(f"  ✓ Test reading: {dist} mm")
                )
            except Exception as e:
                click.echo(
                    term.red(f"  ✗ Reinitialize failed: {e}")
                )

            input("\nPress Enter to continue...")

        # ==============================================================
        # Main loop
        # ==============================================================
        while running:
            show_menu()
            choice = input("Choice: ").strip().lower()

            if choice == "1":
                tui_single_read()
            elif choice == "2":
                tui_continuous_read()
            elif choice == "3":
                tui_performance()
            elif choice == "4":
                tui_calibrate()
            elif choice == "5":
                tui_health_check()
            elif choice == "6":
                tui_status()
            elif choice == "7":
                tui_config_menu()
            elif choice == "8":
                tui_reinitialize()
            elif choice == "q":
                running = False
            else:
                click.echo("Invalid choice")
                input("\nPress Enter to continue...")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        try:
            sensor.close()
        except Exception:
            pass
        pi.stop()  # type: ignore[attr-defined]
        click.echo("\nGoodbye!")


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    cli(obj={})  # pylint: disable=no-value-for-parameter
