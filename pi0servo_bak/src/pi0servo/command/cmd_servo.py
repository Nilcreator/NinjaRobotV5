#
# (c) 2025 Yoichi Tanibayashi
#
import time

import click
import pigpio

from ..core.calibrable_servo import CalibrableServo
from ninja_utils.my_logger import get_logger


class CmdServo:
    """servo command"""

    def __init__(self, pi, pin, angle, sec=1.0, debug=False):
        self._debug = debug
        self.__log = get_logger(__class__.__name__, self._debug)
        self.__log.debug('pin=%s, angle="%s", sec=%s', pin, angle, sec)

        self.pin = pin
        self.angle_str = angle
        self.sec = sec

        self.pi = pi
        if not self.pi.connected:
            self.__log.error("pigpio daemon not connected.")
            raise ConnectionError("pigpio daemon not connected.")

        self.servo = CalibrableServo(self.pi, self.pin, debug=self._debug)

    def main(self):
        """main"""
        try:
            # Try to convert to float first
            angle_float = float(self.angle_str)
            self.servo.move_angle(angle_float)
            print(f"pin={self.pin}, angle={angle_float} deg")

        except ValueError:
            # If it fails, treat as a string keyword
            if self.angle_str in [self.servo.POS_MIN, self.servo.POS_CENTER, self.servo.POS_MAX]:
                self.servo.move_angle(self.angle_str)
                print(f"pin={self.pin}, position='{self.angle_str}'")
            else:
                self.__log.error(
                    '"%s": invalid angle or keyword', self.angle_str
                )
                return

        time.sleep(self.sec)

    def end(self):
        """end"""
        self.__log.debug("")
        self.servo.off()
        print("done")


@click.command()
@click.argument("pin", type=int)
@click.argument("angle", type=str)
@click.option("--sec", "-s", "sec", type=float, default=1.0, help="sleep time")
@click.option("--debug", "-d", "debug", is_flag=True, help="debug flag")
def main(pin, angle, sec, debug):
    """
    Move servo to a specified ANGLE or position.

    ANGLE: min | center | max | <angle_in_degrees>
    """
    log = get_logger(__name__, debug)

    pi = pigpio.pi()

    app = None
    try:
        app = CmdServo(pi, pin, angle, sec, debug=debug)
        app.main()
    except Exception as e:
        log.error(e)
    finally:
        if app:
            app.end()
        log.debug("finally")


if __name__ == "__main__":
    main()