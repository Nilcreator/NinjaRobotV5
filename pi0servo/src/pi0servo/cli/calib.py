"""CLI calibration command - interactive servo calibration tool.

This implements an interactive TUI for servo calibration, matching the
original CalibApp from pi0servo_bak. Users can adjust servo pulse widths
for min/center/max positions using keyboard navigation.
"""

import sys

import click

from ..config import ConfigManager
from ..core import PULSE_MAX, PULSE_MIN, Servo, ServoCalibration


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


class CalibApp:
    """Interactive servo calibration TUI application.

    Allows interactive adjustment of min/center/max pulse widths
    using keyboard navigation.
    """

    TARGET_CENTER = 0
    TARGET_MIN = -90
    TARGET_MAX = 90
    TARGETS = [TARGET_MIN, TARGET_CENTER, TARGET_MAX]
    TARGET_NAMES = {TARGET_MIN: "Min", TARGET_CENTER: "Center", TARGET_MAX: "Max"}

    STEP_LARGE = 20
    STEP_FINE = 1

    def __init__(self, pi, pin: int, config_path: str, debug: bool = False):
        """Initialize calibration app.

        Args:
            pi: pigpio instance
            pin: GPIO pin number
            config_path: Path to servo.json config file
            debug: Enable debug output
        """
        self.pi = pi
        self.pin = pin
        self.config_path = config_path
        self.debug = debug

        # Load or create calibration
        self.manager = ConfigManager(config_path)
        self.manager.load()
        self.calibration = self.manager.get_calibration(pin)

        # Create servo with calibration
        self.servo = Servo(pi, pin, self.calibration)

        # Current calibration values (mutable during session)
        self.pulse_min = self.calibration.pulse_min
        self.pulse_center = self.calibration.pulse_center
        self.pulse_max = self.calibration.pulse_max
        self.speed = self.calibration.speed

        # Current target position
        self.cur_target = self.TARGET_CENTER
        self.running = True

        # Current pulse position (for adjustment)
        self.cur_pulse = self.pulse_center

        # Try to import blessed for TUI
        try:
            import blessed
            self.term = blessed.Terminal()
            self.has_blessed = True
        except ImportError:
            self.has_blessed = False
            click.echo("Warning: 'blessed' not installed. Using simple mode.", err=True)

    def _setup_key_bindings(self):
        """Set up keyboard action mappings."""
        return {
            # Cycle through targets
            "KEY_TAB": self.inc_target,
            "KEY_BTAB": self.dec_target,
            # Direct target selection
            "v": lambda: self.set_target(self.TARGET_MIN),
            "c": lambda: self.set_target(self.TARGET_CENTER),
            "x": lambda: self.set_target(self.TARGET_MAX),
            # Fine-tune adjustment
            "w": lambda: self.move_diff(self.STEP_FINE),
            "s": lambda: self.move_diff(-self.STEP_FINE),
            # Large step adjustment
            "KEY_UP": lambda: self.move_diff(self.STEP_LARGE),
            "KEY_DOWN": lambda: self.move_diff(-self.STEP_LARGE),
            # Calibration save
            "KEY_ENTER": self.set_calibration,
            " ": self.set_calibration,
            # Misc
            "h": self.display_help,
            "H": self.display_help,
            "?": self.display_help,
            "q": self.quit,
            "Q": self.quit,
        }

    def main(self):
        """Main interactive loop."""
        if not self.has_blessed:
            # Fallback to simple mode
            self._simple_mode()
            return

        click.echo("\nServo Calibration Tool: 'h' for help, 'q' to quit")
        self.show()

        # Move to center position
        self.servo.set_pulse(self.pulse_center)
        self.cur_pulse = self.pulse_center

        key_bindings = self._setup_key_bindings()

        with self.term.cbreak(), self.term.hidden_cursor():
            while self.running:
                self.print_prompt()
                inkey = self.term.inkey()
                if not inkey:
                    continue

                key_name = inkey.name if inkey.is_sequence else str(inkey)

                if key_name:
                    action = key_bindings.get(key_name)
                    if action:
                        action()
                        continue

                # Unknown key - ignore silently

    def _simple_mode(self):
        """Simple non-interactive mode when blessed is not available."""
        click.echo("\n=== Simple Calibration Mode ===")
        click.echo(f"Config: {self.config_path}")
        click.echo(f"GPIO Pin: {self.pin}")
        click.echo("Current calibration:")
        click.echo(f"  Min: {self.pulse_min}, Center: {self.pulse_center}, Max: {self.pulse_max}")
        click.echo("\nInstall 'blessed' for interactive mode: pip install blessed")

    def show(self):
        """Show current calibration status."""
        click.echo()
        click.echo(f"* Config: {self.config_path}")
        click.echo()
        click.echo(f"* GPIO{self.pin}")
        click.echo(f"   Min ({self.TARGET_MIN}°): pulse = {self.pulse_min}")
        click.echo(f"   Center ({self.TARGET_CENTER}°): pulse = {self.pulse_center}")
        click.echo(f"   Max ({self.TARGET_MAX}°): pulse = {self.pulse_max}")
        click.echo(f"   Speed: {self.speed}%")
        click.echo()

    def print_prompt(self):
        """Print interactive prompt."""
        target_str = self.TARGET_NAMES.get(self.cur_target, "Unknown")
        prompt = (
            f"GPIO{self.pin}"
            f" | Target: {target_str}"
            f" | pulse={self.cur_pulse}"
        )
        print(f"\r{self.term.clear_eol()}{prompt}> ", end="", flush=True)

    def inc_target(self):
        """Cycle to next target."""
        idx = self.TARGETS.index(self.cur_target)
        idx = (idx + 1) % len(self.TARGETS)
        self.set_target(self.TARGETS[idx])

    def dec_target(self):
        """Cycle to previous target."""
        idx = self.TARGETS.index(self.cur_target)
        idx = (idx - 1 + len(self.TARGETS)) % len(self.TARGETS)
        self.set_target(self.TARGETS[idx])

    def set_target(self, target: int):
        """Set current target and move servo to saved position."""
        if target in self.TARGETS:
            self.cur_target = target

            # Move to saved pulse for this target
            if target == self.TARGET_MIN:
                self.cur_pulse = self.pulse_min
            elif target == self.TARGET_CENTER:
                self.cur_pulse = self.pulse_center
            elif target == self.TARGET_MAX:
                self.cur_pulse = self.pulse_max

            self.servo.set_pulse(self.cur_pulse)

    def move_diff(self, diff_pulse: int):
        """Adjust pulse by relative amount."""
        dst_pulse = self.cur_pulse + diff_pulse
        # Clamp to valid range
        dst_pulse = max(min(dst_pulse, PULSE_MAX), PULSE_MIN)
        self.cur_pulse = dst_pulse
        self.servo.set_pulse(dst_pulse)

    def set_calibration(self):
        """Save current pulse as calibration for current target."""
        print(f"\r{self.term.clear_eol()}", end="")

        target_str = self.TARGET_NAMES.get(self.cur_target, "Unknown")

        # Validate and save
        if self.cur_target == self.TARGET_CENTER:
            if self.pulse_min < self.cur_pulse < self.pulse_max:
                self.pulse_center = self.cur_pulse
            else:
                click.echo(f"Error: Center ({self.cur_pulse}) must be between Min ({self.pulse_min}) and Max ({self.pulse_max}).")
                return
        elif self.cur_target == self.TARGET_MIN:
            if PULSE_MIN <= self.cur_pulse < self.pulse_center:
                self.pulse_min = self.cur_pulse
            else:
                click.echo(f"Error: Min ({self.cur_pulse}) must be less than Center ({self.pulse_center}).")
                return
        elif self.cur_target == self.TARGET_MAX:
            if self.pulse_center < self.cur_pulse <= PULSE_MAX:
                self.pulse_max = self.cur_pulse
            else:
                click.echo(f"Error: Max ({self.cur_pulse}) must be greater than Center ({self.pulse_center}).")
                return

        # Update config manager
        new_cal = ServoCalibration(
            pulse_min=self.pulse_min,
            pulse_max=self.pulse_max,
            pulse_center=self.pulse_center,
            speed=self.speed,
        )
        self.manager.set_calibration(self.pin, new_cal)
        self.manager.save()

        click.echo(f"✓ Saved! {target_str} for GPIO{self.pin} = pulse {self.cur_pulse}")

    def display_help(self):
        """Display help message."""
        click.echo("""

=== Servo Calibration Help ===

Select Target:
  [Tab] / [Shift+Tab] : Cycle through Min, Center, Max
  [v] : Select Min (-90°)
  [c] : Select Center (0°)
  [x] : Select Max (90°)

Adjust Pulse:
  [Up] / [Down] : Large step adjustment (±20)
  [w] / [s]     : Fine-tune adjustment (±1)

Save:
  [Enter] / [Space] : Save current pulse for selected target

Misc:
  [q] : Quit
  [h] : Show this help
""")
        self.show()

    def quit(self):
        """Quit the application."""
        click.echo("\n=== Quit ===")
        self.running = False

    def end(self):
        """Cleanup on exit."""
        self.servo.off()
        self.show()


@click.command("calib")
@click.argument("pin", type=int, required=False)
@click.option(
    "-c", "--config",
    type=click.Path(),
    default="servo.json",
    help="Path to configuration file.",
)
@click.option(
    "-d", "--debug",
    is_flag=True,
    help="Enable debug output.",
)
@click.option(
    "--show", is_flag=True,
    help="Show calibration without interactive mode.",
)
def calib(pin: int | None, config: str, debug: bool, show: bool):
    """Interactive servo calibration tool.

    PIN: GPIO pin number to calibrate

    When run without --show, enters interactive calibration mode:
    - Use Tab to cycle through Min/Center/Max targets
    - Use Up/Down or w/s to adjust pulse width
    - Press Enter to save the current value

    Examples:\n
        pi0servo calib 20          # Calibrate GPIO pin 20\n
        pi0servo calib 20 --show   # Just show current calibration\n
        pi0servo calib --show      # Show all calibrations\n
    """
    manager = ConfigManager(config)
    manager.load()

    # Show-only mode
    if show or pin is None:
        if pin is not None:
            cal = manager.get_calibration(pin)
            _print_calibration(pin, cal)
        else:
            all_cals = manager.get_all_calibrations()
            if not all_cals:
                click.echo("No calibrations stored.")
                click.echo(f"Config file: {config}")
            else:
                click.echo(f"Config: {config}")
                for p, cal in sorted(all_cals.items()):
                    _print_calibration(p, cal)
        return

    # Interactive mode requires pin
    pi = create_pi()
    app = None

    try:
        app = CalibApp(pi, pin, config, debug=debug)
        app.main()
    except KeyboardInterrupt:
        click.echo("\nInterrupted.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        if app:
            app.end()
        pi.stop()


def _print_calibration(pin: int, cal: ServoCalibration):
    """Print calibration info for a pin."""
    click.echo(f"Pin {pin}:")
    click.echo(f"  Pulse: {cal.pulse_min} / {cal.pulse_center} / {cal.pulse_max}")
    click.echo(f"  Angle: {cal.angle_min}° / {cal.angle_center}° / {cal.angle_max}°")
    click.echo(f"  Speed: {cal.speed}%")
