#
# (c) 2025 Yoichi Tanibayashi
#
import pprint

import blessed
import click
import pigpio

from ..core.calibrable_servo import CalibrableServo
from ninja_utils.my_logger import get_logger


class CalibApp:
    """CalibApp:サーボキャリブレーション用CUIアプリケーション."""

    TARGET_CENTER = 0
    TARGET_MIN = -90
    TARGET_MAX = 90
    TARGETS = [TARGET_MIN, TARGET_CENTER, TARGET_MAX]
    
    STEP_LARGE = 20
    STEP_FINE = 1

    def __init__(self, pi, pin, conf_file, debug=False):
        self._debug = debug
        self.__log = get_logger(self.__class__.__name__, self._debug)
        self.__log.debug("pin=%s, conf_file=%s", pin, conf_file)

        self.pi = pi
        self.pin = pin
        self.conf_file = conf_file
        
        if not self.pi.connected:
            raise ConnectionError("pigpio daemon not connected.")

        self.cur_target = self.TARGET_CENTER
        self.__log.debug("cur_target=%s", self.cur_target)

        self.term = blessed.Terminal()
        self.servo = CalibrableServo(
            self.pi, self.pin, conf_file=self.conf_file, debug=self._debug
        )
        self.conf_file = self.servo.conf_file
        self.__log.debug("conf_file=%s", self.conf_file)

        self.servo.move_center()

        self.running = True

        self.key_bindings = self._setup_key_bindings()
        self.__log.debug(
            "key_bindings=%s",
            pprint.pformat(self.key_bindings, indent=2)
            .replace("{ ", "{\n ")
            .replace(" }", "\n}"),
        )

    def _setup_key_bindings(self):
        """キーバインドを設定する"""
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
            # Calibration
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
        """メインループ"""
        print("\nCalibration Tool: 'h' for help, 'q' for quit")
        self.show()

        self.__log.debug("starting main loop")
        with self.term.cbreak(), self.term.hidden_cursor():
            while self.running:
                self.print_prompt()
                inkey = self.term.inkey()
                if not inkey:
                    continue

                key_name = inkey.name if inkey.is_sequence else str(inkey)
                self.__log.debug("key_name=%s", key_name)

                if key_name:
                    action = self.key_bindings.get(key_name)
                    if action:
                        action()
                        continue

                print(f"'{key_name}': unknown key")

    def show(self):
        """Show current setup."""
        print()
        print(f"* conf_file: {self.conf_file}")
        print()
        print(f"* GPIO{self.pin}")
        print(f"   Min ({self.TARGET_MIN} deg): pulse = {self.servo.pulse_min:-4d}")
        print(f"   Center ({self.TARGET_CENTER} deg): pulse = {self.servo.pulse_center:-4d}")
        print(f"   Max ({self.TARGET_MAX} deg): pulse = {self.servo.pulse_max:-4d}")
        print()

    def print_prompt(self):
        """Print Prompt string."""
        _cur_pulse = self.servo.get_pulse()
        
        target_map = {
            self.TARGET_MIN: "Min",
            self.TARGET_CENTER: "Center",
            self.TARGET_MAX: "Max"
        }
        target_str = target_map.get(self.cur_target, "Unknown")

        prompt_str = (
            f"GPIO{self.pin}"
            f" | Target: {target_str}"
            f" | pulse={_cur_pulse}"
        )

        print(f"\r{self.term.clear_eol()}{prompt_str}> ", end="", flush=True)

    def inc_target(self):
        """Change target cyclically."""
        _idx = self.TARGETS.index(self.cur_target)
        _idx = (_idx + 1) % len(self.TARGETS)
        self.set_target(self.TARGETS[_idx])

    def dec_target(self):
        """Change target cyclically."""
        _idx = self.TARGETS.index(self.cur_target)
        _idx = (_idx - 1 + len(self.TARGETS)) % len(self.TARGETS)
        self.set_target(self.TARGETS[_idx])

    def set_target(self, target: int):
        """Set target."""
        if target in self.TARGETS:
            self.cur_target = target
            self.__log.debug("cur_target=%s", self.cur_target)
            self.servo.move_angle(self.cur_target)
        
    def move_diff(self, diff_pulse):
        """パルス幅を相対的に変更する"""
        cur_pulse = self.servo.get_pulse()
        dst_pulse = cur_pulse + diff_pulse
        dst_pulse = max(min(dst_pulse, self.servo.MAX), self.servo.MIN)
        self.__log.debug("dst_pulse=%s", dst_pulse)
        self.servo.move_pulse(dst_pulse, forced=True)

    def set_calibration(self):
        """キャリブレーション値を設定・保存する"""
        cur_pulse = self.servo.get_pulse()
        print(f"\r{self.term.clear_eol()}", end="")

        if self.cur_target == self.TARGET_CENTER:
            if self.servo.pulse_min < cur_pulse < self.servo.pulse_max:
                self.servo.pulse_center = cur_pulse
            else:
                print(f"Error: Center pulse {cur_pulse} must be between Min ({self.servo.pulse_min}) and Max ({self.servo.pulse_max}).")
                return
        elif self.cur_target == self.TARGET_MIN:
            if self.servo.MIN <= cur_pulse < self.servo.pulse_center:
                self.servo.pulse_min = cur_pulse
            else:
                print(f"Error: Min pulse {cur_pulse} must be less than Center ({self.servo.pulse_center}).")
                return
        elif self.cur_target == self.TARGET_MAX:
            if self.servo.pulse_center < cur_pulse <= self.servo.MAX:
                self.servo.pulse_max = cur_pulse
            else:
                print(f"Error: Max pulse {cur_pulse} must be greater than Center ({self.servo.pulse_center}).")
                return
        else:
            self.__log.warning("cur_target=%s??", self.cur_target)
            return

        target_map = {self.TARGET_MIN: "Min", self.TARGET_CENTER: "Center", self.TARGET_MAX: "Max"}
        target_str = target_map.get(self.cur_target, "Unknown")
        print(f"Saved! {target_str} for GPIO{self.pin} is now pulse={cur_pulse}")

    def display_help(self):
        """ヘルプメッセージを表示する"""
        print(
            """

=== Usage ===
* Select Target:
  [Tab] / [Shift+Tab] : Cycle through Min, Center, Max
  [v] : Select Min (-90 deg)
  [c] : Select Center (0 deg)
  [x] : Select Max (90 deg)

* Adjust Position:
  [Up]/[Down] : Large step adjustment
  [w] / [s]   : Fine-tune adjustment

* Save:
  [Enter] / [Space] : Save current pulse for the selected target

* Misc:
  [q] : Quit
  [h] : Show this help
"""
        )
        self.show()

    def quit(self):
        """アプリケーションを終了する"""
        print("\n=== Quit ===")
        self.running = False

    def end(self):
        """終了処理"""
        self.servo.off()
        self.show()


@click.command()
@click.argument("pin", type=int)
@click.option(
    "--conf-file",
    "-f",
    "conf_file",
    type=str,
    default=CalibrableServo.DEF_CONF_FILE,
    help="config file name",
)
@click.option("--debug", "-d", "debug", is_flag=True, help="debug flag")
def main(pin, conf_file, debug):
    """Servo Motor Calibration Tool"""
    log = get_logger(__name__, debug)
    pi = pigpio.pi()
    app = None

    try:
        app = CalibApp(pi, pin, conf_file, debug=debug)
        app.main()
    except Exception as e:
        log.error(e)
    finally:
        if app:
            app.end()
        log.debug("finally")


if __name__ == "__main__":
    main()