#
# (c) 2025 Yoichi Tanibayashi
#
"""piservo.py"""
import pigpio

from ninja_utils.my_logger import get_logger


class PiServo:
    """The most basic class for controlling servo motors.

    pigpioライブラリを利用して、より手軽にサーボモーターを制御する。
    """

    OFF = 0
    MIN = 500
    MAX = 2500
    CENTER = 1500

    def __init__(self, pi, pin, debug=False):
        """PiServoクラスのコンストラクタ。

        Args:
            pi (pigpio.pi):
                pigpio.piのインスタンス。サーボモーターを制御するために必要。
            pin (int, optional):
                サーボモーターが接続されているGPIOピン番号。
            debug (bool, optional):
                デバッグログを有効にするかどうかのフラグ。
                Trueの場合、詳細なログが出力される。デフォルトはFalse。
        """
        self._debug = debug
        self.__log = get_logger(self.__class__.__name__, self._debug)
        self.__log.debug("pin=%s", pin)

        self._pi = pi
        self._pin = pin

    @property
    def pi(self):
        return self._pi

    @property
    def pin(self):
        return self._pin
    
    def get_pulse(self):
        """Get pulse.

        Returns the center pulse value if the servo is not currently active
        to prevent errors on first read.

        Returns:
            int: pulse width (micro sec)
        """
        try:
            pulse = self.pi.get_servo_pulsewidth(self.pin)
            if pulse == 0:
                self.__log.warning("pin %s: pulse=0, using center", self.pin)
                return self.CENTER
            self.__log.debug("pulse=%s", pulse)
            return pulse
        except pigpio.error:
            self.__log.warning("pin %s: pigpio err, using center", self.pin)
            return self.CENTER

    def move_pulse(self, pulse):
        """サーボモーターを指定されたパルス幅に移動させる。

        パルス幅はMINからMAXの範囲に制限される。
        指定されたパルス幅が範囲外の場合、自動的に最小値または最大値に調整される。

        Args:
            pulse (int):
                サーボモーターに設定するパルス幅（マイクロ秒）。
                この値に基づいてサーボの位置が決定される。
        """
        self.__log.debug("pin=%s, pulse=%s", self.pin, pulse)

        if pulse < self.MIN or pulse > self.MAX:
            pulse = max(min(pulse, self.MAX), self.MIN)
            self.__log.debug("pulse=%s", pulse)

        self.pi.set_servo_pulsewidth(self.pin, pulse)

    def move_pulse_relative(self, pulse_diff):
        """Move relative.

        もし、現在のパルスが、0(off)の場合は、動かさない。

        Args:
            pulse_diff (int): Differential Pulse
        """
        self.__log.debug("pin=%s, pulse_diff=%s", self.pin, pulse_diff)

        _cur_pulse = self.get_pulse()
        self.__log.debug("cur_pulse=%s", _cur_pulse)
        
        if _cur_pulse == 0:
            return

        self.move_pulse(_cur_pulse + pulse_diff)

    def move_min(self):
        """サーボモーターを最小位置に移動させる。

        パルス幅をMINに設定する。
        """
        self.__log.debug("pin=%s", self.pin)
        self.move_pulse(self.MIN)

    def move_max(self):
        """サーボモーターを最大位置に移動させる。

        パルス幅をMAXに設定する。
        """
        self.__log.debug("pin=%s", self.pin)
        self.move_pulse(self.MAX)

    def move_center(self):
        """サーボモーターを中央位置に移動させる。

        パルス幅をCENTERに設定する。
        """
        self.__log.debug("pin=%s", self.pin)
        self.move_pulse(self.CENTER)

    def off(self):
        """サーボモーターの電源をオフにする。

        サーボモーターのパルス幅をOFF (0) に設定し、動作を停止させる。
        """
        self.__log.debug("pin=%s", self.pin)
        self.pi.set_servo_pulsewidth(self.pin, self.OFF)
