"""Interactive servo control tool.

Provides a menu-driven interface for servo testing and configuration.

Usage:
    uv run pi0servo servo-tool
"""

import click

# Optional blessed for TUI
try:
    from blessed import Terminal

    HAS_BLESSED = True
except ImportError:
    HAS_BLESSED = False


@click.command("servo-tool")
@click.option(
    "-c",
    "--config",
    "config_path",
    default="servo.json",
    help="Path to calibration config file.",
)
def servo_tool(config_path: str):
    """Interactive servo control and configuration tool."""
    if not HAS_BLESSED:
        click.echo("❌ 'blessed' library required for interactive mode.")
        click.echo("   Install with: pip install blessed")
        return

    try:
        import pigpio

        pi = pigpio.pi()
        if not pi.connected:
            click.echo("❌ pigpio daemon not connected. Run: sudo pigpiod")
            return
    except Exception as e:
        click.echo(f"❌ pigpio error: {e}")
        return

    try:
        from ..config import ConfigManager
        from ..core import ServoGroup

        manager = ConfigManager(config_path)
        manager.load()

        term = Terminal()
        running = True

        def show_menu():
            """Display main menu."""
            click.echo(term.clear())
            click.echo(term.bold("╔" + "═" * 58 + "╗"))
            click.echo(term.bold("║") + term.cyan("           pi0servo Interactive Tool") + " " * 20 + term.bold("║"))
            click.echo(term.bold("╠" + "═" * 58 + "╣"))
            click.echo(term.bold("║") + "  1. Quick Move    - Enter commands like '17:30/27:M'    " + term.bold("║"))
            click.echo(term.bold("║") + "  2. Single Move   - Move one servo to angle             " + term.bold("║"))
            click.echo(term.bold("║") + "  3. Calibrate     - Launch calibration TUI              " + term.bold("║"))
            click.echo(term.bold("║") + "  4. Set Speed     - Adjust servo speed limit            " + term.bold("║"))
            click.echo(term.bold("║") + "  5. Status        - Show all servo configs              " + term.bold("║"))
            click.echo(term.bold("║") + "  6. Config        - Show/export/import config           " + term.bold("║"))
            click.echo(term.bold("║") + "  q. Exit                                                " + term.bold("║"))
            click.echo(term.bold("╚" + "═" * 58 + "╝"))
            click.echo()

        def quick_move():
            """Execute command strings continuously until 'q' to quit."""
            click.echo("\n" + term.cyan("=== Quick Move Mode ==="))
            click.echo("Enter commands like 'F_20:45/21:-30'. Type 'q' to return.\n")

            from ..parser import parse_command

            while True:
                cmd_str = input("> ").strip()
                if cmd_str.lower() in ("q", "b", "quit", "back"):
                    break
                if not cmd_str:
                    continue

                try:
                    parsed = parse_command(cmd_str)
                    pins = [t.pin for t in parsed.targets]

                    # Load calibrations fresh each time
                    calibrations = {pin: manager.get_calibration(pin) for pin in pins}

                    group = ServoGroup(pi, pins=pins, calibrations=calibrations)
                    success = group.execute_command(cmd_str)

                    if success:
                        click.echo(term.green("✓ Done"))
                    else:
                        click.echo(term.red("✗ Aborted"))

                except ValueError as e:
                    click.echo(term.red(f"✗ Error: {e}"))

        def single_move():
            """Move a single servo continuously until 'q' to quit."""
            click.echo("\n" + term.cyan("=== Single Move Mode ==="))
            click.echo("Enter GPIO pin:")
            try:
                pin = int(input("> ").strip())
            except ValueError:
                click.echo(term.red("Invalid pin"))
                input("\nPress Enter to continue...")
                return

            click.echo(f"Moving GPIO{pin}. Enter angle or 'min'/'center'/'max'. Type 'q' to return.\n")

            from ..core import Servo

            cal = manager.get_calibration(pin)
            servo = Servo(pi, pin, cal)

            while True:
                angle_str = input("> ").strip().lower()
                if angle_str in ("q", "b", "quit", "back"):
                    break
                if not angle_str:
                    continue

                # Resolve angle
                if angle_str == "min":
                    angle = cal.angle_min
                elif angle_str == "center":
                    angle = cal.angle_center
                elif angle_str == "max":
                    angle = cal.angle_max
                else:
                    try:
                        angle = float(angle_str)
                    except ValueError:
                        click.echo(term.red("Invalid angle"))
                        continue

                servo.set_angle(angle)
                click.echo(term.green(f"✓ GPIO{pin} → {angle}°"))

        def calibrate_servo():
            """Launch calibration TUI."""
            click.echo("\n" + term.yellow("Enter GPIO pin to calibrate:"))
            try:
                pin = int(input("> ").strip())
            except ValueError:
                click.echo(term.red("Invalid pin"))
                input("\nPress Enter to continue...")
                return

            # Import and run the calib TUI
            from .calib import CalibApp

            app = CalibApp(pi, pin, config_path)
            app.main()

            # Reload config to pick up changes from calibration
            manager.load()
            click.echo(term.green("✓ Config reloaded"))

        def set_speed():
            """Set speed limit for a servo."""
            click.echo("\n" + term.cyan("=== Set Servo Speed Limit ==="))

            # Show current configs
            configs = manager.get_all_calibrations()
            if configs:
                click.echo("\nCurrent speeds:")
                for pin_num, cal in configs.items():
                    click.echo(f"  GPIO{pin_num}: {cal.speed}%")

            click.echo("\n" + term.yellow("Enter GPIO pin:"))
            try:
                pin = int(input("> ").strip())
            except ValueError:
                click.echo(term.red("Invalid pin"))
                input("\nPress Enter to continue...")
                return

            # Get current calibration or create default
            cal = manager.get_calibration(pin)
            click.echo(f"Current speed for GPIO{pin}: {cal.speed}%")

            click.echo(term.yellow("Enter new speed (0-100):"))
            try:
                new_speed = int(input("> ").strip())
                if not 0 <= new_speed <= 100:
                    click.echo(term.red("Speed must be 0-100"))
                    input("\nPress Enter to continue...")
                    return
            except ValueError:
                click.echo(term.red("Invalid speed"))
                input("\nPress Enter to continue...")
                return

            # Update calibration with new speed
            from ..core import ServoCalibration

            new_cal = ServoCalibration(
                pulse_min=cal.pulse_min,
                pulse_max=cal.pulse_max,
                pulse_center=cal.pulse_center,
                angle_min=cal.angle_min,
                angle_max=cal.angle_max,
                angle_center=cal.angle_center,
                speed=new_speed,
            )
            manager.set_calibration(pin, new_cal)
            manager.save()

            click.echo(term.green(f"✓ Speed for GPIO{pin} set to {new_speed}%"))
            input("\nPress Enter to continue...")

        def show_status():
            """Show all servo configurations."""
            click.echo("\n" + term.cyan("=== Servo Configurations ==="))
            configs = manager.get_all_calibrations()

            if not configs:
                click.echo("No servos configured. Run calibration first.")
            else:
                for pin_num, cal in configs.items():
                    click.echo(
                        f"  GPIO{pin_num}: "
                        f"pulse=[{cal.pulse_min}, {cal.pulse_center}, {cal.pulse_max}] "
                        f"speed={cal.speed}%"
                    )

            input("\nPress Enter to continue...")

        def config_menu():
            """Config management submenu."""
            click.echo("\n" + term.cyan("=== Config Management ==="))
            click.echo("  1. Show current config")
            click.echo("  2. Export to file")
            click.echo("  3. Import from file")
            click.echo("  b. Back")

            choice = input("\nChoice: ").strip().lower()

            if choice == "1":
                import json

                click.echo("\n" + json.dumps(manager._to_dict(), indent=2))
            elif choice == "2":
                click.echo(term.yellow("Enter export path:"))
                path = input("> ").strip()
                if path:
                    manager.save_to(path)
                    click.echo(term.green(f"✓ Exported to {path}"))
            elif choice == "3":
                click.echo(term.yellow("Enter import path:"))
                path = input("> ").strip()
                if path:
                    manager.load_from(path)
                    click.echo(term.green(f"✓ Imported from {path}"))

            input("\nPress Enter to continue...")

        # Main loop
        while running:
            show_menu()
            choice = input("Choice: ").strip().lower()

            if choice == "1":
                quick_move()
            elif choice == "2":
                single_move()
            elif choice == "3":
                calibrate_servo()
            elif choice == "4":
                set_speed()
            elif choice == "5":
                show_status()
            elif choice == "6":
                config_menu()
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
        pi.stop()
        click.echo("\nGoodbye!")
