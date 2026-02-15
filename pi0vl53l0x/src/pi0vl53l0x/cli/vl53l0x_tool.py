"""Interactive VL53L0X sensor tool.

Provides a menu-driven interface for distance sensor testing,
calibration, and configuration — similar to pi0servo's servo-tool.

Usage:
    uv run pi0vl53l0x vl53l0x-tool
"""

from __future__ import annotations

import json
import statistics
import time

import click

# Optional blessed for TUI
try:
    from blessed import Terminal

    HAS_BLESSED = True
except ImportError:
    HAS_BLESSED = False


@click.command("vl53l0x-tool")
@click.option(
    "-c",
    "--config",
    "config_path",
    default=None,
    help="Path to sensor config file (default: vl53l0x.json).",
)
def vl53l0x_tool(config_path: str | None):
    """Interactive VL53L0X distance sensor tool."""
    if not HAS_BLESSED:
        click.echo("❌ 'blessed' library required for interactive mode.")
        click.echo("   Install with: pip install blessed")
        return

    # --- Connect to pigpio ---
    try:
        import pigpio  # type: ignore[import-untyped]

        pi = pigpio.pi()
        if not pi.connected:
            click.echo("❌ pigpio daemon not connected. Run: sudo pigpiod")
            return
    except ImportError:
        click.echo(
            "❌ pigpio is not installed. Install with:\n"
            "  Standalone: uv sync --extra pi\n"
            "  NinjaRobotV5: uv sync\n"
            "  Manual: pip install pigpio"
        )
        return
    except Exception as e:
        click.echo(f"❌ pigpio error: {e}")
        return

    # --- Initialize sensor & config ---
    try:
        from pi0vl53l0x.config.config_manager import ConfigManager
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

        def show_menu():
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

        def single_read():
            """Take single distance readings. Press Enter to repeat, 'q' to return."""
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

        def continuous_read():
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
            click.echo(f"\nStreaming every {interval_ms}ms. Press Ctrl+C to stop.\n")

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
                        click.echo(f"  [{readings:4d}] " + term.red(f"Error: {e}"))
                    time.sleep(interval_s)
            except KeyboardInterrupt:
                click.echo(term.yellow(f"\n  Stopped after {readings} readings."))

            input("\nPress Enter to continue...")

        def performance_test():
            """Measure readings per second."""
            click.echo("\n" + term.cyan("=== Performance Test ==="))

            click.echo(term.yellow("Number of samples (default 100):"))
            try:
                num = int(input("> ").strip() or "100")
            except ValueError:
                click.echo(term.red("Invalid number"))
                input("\nPress Enter to continue...")
                return

            click.echo(f"\nRunning {num} readings as fast as possible...\n")

            distances = []
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
                click.echo(f"  Mean:      {statistics.mean(distances):.0f} mm")
                click.echo(f"  Min:       {min(distances)} mm")
                click.echo(f"  Max:       {max(distances)} mm")
                if len(distances) >= 2:
                    click.echo(f"  Std Dev:   {statistics.stdev(distances):.1f} mm")

            input("\nPress Enter to continue...")

        def calibrate():
            """Guided offset calibration."""
            click.echo("\n" + term.cyan("=== Calibration ==="))
            click.echo(
                "Place a flat target at a known distance from the sensor.\n"
                "The sensor will take multiple readings and calculate the offset.\n"
            )

            click.echo(term.yellow("Target distance in mm (e.g. 200):"))
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

            click.echo(term.yellow("Number of samples (default 20):"))
            try:
                samples = int(input("> ").strip() or "20")
            except ValueError:
                click.echo(term.red("Invalid number"))
                input("\nPress Enter to continue...")
                return

            click.echo(f"\nMeasuring {samples} samples at {target}mm target...")

            try:
                new_offset = sensor.calibrate(target, samples)

                click.echo(term.green(f"\n  ✓ Calculated offset: {new_offset} mm"))
                click.echo(f"  (Current offset: {sensor.offset_mm} mm)")

                click.echo(term.yellow("\nApply this offset? (y/n):"))
                if input("> ").strip().lower() == "y":
                    sensor.set_offset(new_offset)
                    manager.set("offset_mm", new_offset)
                    manager.save()
                    click.echo(term.green("  ✓ Offset applied and saved"))
                else:
                    click.echo("  Offset not applied.")

            except Exception as e:
                click.echo(term.red(f"  ✗ Calibration failed: {e}"))

            input("\nPress Enter to continue...")

        def health_check():
            """Quick sensor health check."""
            click.echo("\n" + term.cyan("=== Health Check ==="))

            try:
                healthy = sensor.health_check()
                if healthy:
                    click.echo(term.green("  ✓ Sensor is responding correctly"))
                    # Also try a single reading
                    dist = sensor.get_range()
                    click.echo(term.green(f"  ✓ Test reading: {dist} mm"))
                else:
                    click.echo(term.red("  ✗ Sensor health check failed"))
                    click.echo("    Try option 8 (Reinitialize) to recover.")
            except Exception as e:
                click.echo(term.red(f"  ✗ Error: {e}"))

            input("\nPress Enter to continue...")

        def show_status():
            """Show full sensor diagnostics."""
            click.echo("\n" + term.cyan("=== Sensor Status ==="))

            # Health
            try:
                healthy = sensor.health_check()
                status_str = term.green("OK") if healthy else term.red("FAILED")
            except Exception:
                status_str = term.red("ERROR")

            click.echo(f"  Health:     {status_str}")
            click.echo(f"  Offset:     {sensor.offset_mm} mm")
            click.echo(f"  Config:     {manager.path}")

            # Config values
            cfg = manager.config
            if cfg:
                click.echo("  Settings:")
                for key, value in cfg.items():
                    click.echo(f"    {key}: {value}")
            else:
                click.echo("  Settings:   (defaults)")

            # Quick reading
            try:
                dist = sensor.get_range()
                click.echo("  Reading:    " + term.green(f"{dist} mm"))
            except Exception as e:
                click.echo("  Reading:    " + term.red(f"Error: {e}"))

            input("\nPress Enter to continue...")

        def config_menu():
            """Config management submenu."""
            click.echo("\n" + term.cyan("=== Config Management ==="))
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
                        click.echo(term.green(f"  ✓ Exported to {path}"))
                    except Exception as e:
                        click.echo(term.red(f"  ✗ Export failed: {e}"))

            elif choice == "3":
                click.echo(term.yellow("Enter import path:"))
                path = input("> ").strip()
                if path:
                    try:
                        manager.import_config(path)
                        manager.save()
                        # Apply offset from imported config
                        imported_offset = manager.get("offset_mm", 0)
                        sensor.set_offset(imported_offset)
                        click.echo(term.green(f"  ✓ Imported from {path}"))
                        click.echo(f"  Applied offset: {imported_offset} mm")
                    except Exception as e:
                        click.echo(term.red(f"  ✗ Import failed: {e}"))

            input("\nPress Enter to continue...")

        def reinitialize_sensor():
            """Reinitialize sensor for recovery."""
            click.echo("\n" + term.cyan("=== Reinitialize Sensor ==="))
            click.echo(
                "This performs a full sensor re-initialization.\n"
                "Use this to recover from a stuck or unresponsive state.\n"
            )

            click.echo(term.yellow("Proceed? (y/n):"))
            if input("> ").strip().lower() != "y":
                click.echo("  Cancelled.")
                input("\nPress Enter to continue...")
                return

            try:
                sensor.reinitialize()
                click.echo(term.green("  ✓ Sensor reinitialized"))

                # Verify with a test reading
                dist = sensor.get_range()
                click.echo(term.green(f"  ✓ Test reading: {dist} mm"))
            except Exception as e:
                click.echo(term.red(f"  ✗ Reinitialize failed: {e}"))

            input("\nPress Enter to continue...")

        # ==============================================================
        # Main loop
        # ==============================================================
        while running:
            show_menu()
            choice = input("Choice: ").strip().lower()

            if choice == "1":
                single_read()
            elif choice == "2":
                continuous_read()
            elif choice == "3":
                performance_test()
            elif choice == "4":
                calibrate()
            elif choice == "5":
                health_check()
            elif choice == "6":
                show_status()
            elif choice == "7":
                config_menu()
            elif choice == "8":
                reinitialize_sensor()
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
        pi.stop()
        click.echo("\nGoodbye!")
