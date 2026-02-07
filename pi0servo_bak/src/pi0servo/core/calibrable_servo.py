#
# (c) 2025 Yoichi Tanibayashi
#
from .piservo import PiServo
from ..utils.servo_config_manager import ServoConfigManager
from ninja_utils.my_logger import get_logger


class CalibrableServo(PiServo):
    """PiServoを拡張し、キャリブレーション機能を追加したクラス。

    サーボモーターの制御に特化し、設定の永続化はServoConfigManagerに委任する。

    Attributes:
        conf_file (str): 使用する設定ファイルへのパス。
        pulse_center (int): キャリブレーション後の中央位置のパルス幅。
        pulse_min (int): キャリブレーション後の最小位置のパルス幅。
        pulse_max (int): キャリブレーション後の最大位置のパルス幅。
    """

    DEF_CONF_FILE = "servo.json"  # デフォルトの設定ファイル名

    ANGLE_MIN = -90.0
    ANGLE_MAX = 90.0
    ANGLE_CENTER = 0.0

    POS_CENTER = "center"
    POS_MIN = "min"
    POS_MAX = "max"

    def __init__(self, pi, pin, conf_file=DEF_CONF_FILE, debug=False):
        """CalibrableServoオブジェクトを初期化する。

        親クラスを初期化した後、ServoConfigManagerを使って設定を読み込む。
        設定が存在しない場合は、安全なデフォルト値で作成する。
        """
        super().__init__(pi, pin, debug)

        self._debug = debug
        self.__log = get_logger(self.__class__.__name__, self._debug)
        self.__log.debug("pin=%s, conf_file=%s", pin, conf_file)

        self._config_manager = ServoConfigManager(conf_file, self._debug)
        self.conf_file = self._config_manager.conf_file
        self.__log.debug("self.conf_file=%s", self.conf_file)

        # 設定を読み込んで適用
        self.load_conf()

    def _normalize_pulse(self, pulse):
        """パルス幅を正規化する。(プライベートメソッド)"""
        if pulse is None:
            pulse = self.get_pulse()
        return max(min(pulse, self.MAX), self.MIN)

    @property
    def pulse_center(self):
        """中央位置のパルス幅を取得する。"""
        return self._pulse_center

    @pulse_center.setter
    def pulse_center(self, pulse=None):
        """中央位置のパルス幅を設定し、設定ファイルに保存する。"""
        pulse = self._normalize_pulse(pulse)
        pulse = max(min(pulse, self.pulse_max), self.pulse_min)
        self._pulse_center = pulse
        self.save_conf()

    @property
    def pulse_min(self):
        """最小位置のパルス幅を取得する。"""
        return self._pulse_min

    @pulse_min.setter
    def pulse_min(self, pulse=None):
        """最小位置のパルス幅を設定し、設定ファイルに保存する。"""
        pulse = self._normalize_pulse(pulse)
        pulse = min(pulse, self.pulse_center)
        self._pulse_min = pulse
        self.save_conf()

    @property
    def pulse_max(self):
        """最大位置のパルス幅を取得する。"""
        return self._pulse_max

    @pulse_max.setter
    def pulse_max(self, pulse=None):
        """最大位置のパルス幅を設定し、設定ファイルに保存する。"""
        pulse = self._normalize_pulse(pulse)
        pulse = max(pulse, self.pulse_center)
        self._pulse_max = pulse
        self.save_conf()

    def move_pulse(self, pulse, forced=False):
        """サーボモーターを、キャリブレーション値を考慮して移動させる。"""
        if pulse is None:
            return
        if not forced:
            pulse = max(min(pulse, self.pulse_max), self.pulse_min)
        super().move_pulse(pulse)

    def move_center(self):
        """Move center angle (0 deg)."""
        self.__log.debug("")
        self.move_pulse(self.pulse_center)

    def move_min(self):
        """Move min angle (-90 deg)."""
        self.__log.debug("")
        self.move_pulse(self.pulse_min)

    def move_max(self):
        """Move max angle (90 deg)."""
        self.__log.debug("")
        self.move_pulse(self.pulse_max)

    def deg2pulse(self, deg: float) -> int:
        """Degree to Pulse."""
        if self.pulse_max == self.pulse_center and deg > 0:
            return self.pulse_center
        if self.pulse_min == self.pulse_center and deg < 0:
            return self.pulse_center

        if deg >= self.ANGLE_CENTER:
            d = self.pulse_max - self.pulse_center
            pulse_float = d / self.ANGLE_MAX * deg + self.pulse_center
        else:
            d = self.pulse_center - self.pulse_min
            pulse_float = d / self.ANGLE_MAX * deg + self.pulse_center
            
        pulse_int = int(round(pulse_float))
        self.__log.debug("deg=%s, pulse_float=%s, pulse_int=%s", deg, pulse_float, pulse_int)
        return pulse_int

    def pulse2deg(self, pulse: int) -> float:
        """Pulse to degree."""
        if pulse >= self.pulse_center:
            if self.pulse_max == self.pulse_center:
                return self.ANGLE_CENTER
            d = self.pulse_max - self.pulse_center
        else:
            if self.pulse_min == self.pulse_center:
                return self.ANGLE_CENTER
            d = self.pulse_center - self.pulse_min
        
        if d == 0:
            return self.ANGLE_CENTER

        deg = (pulse - self.pulse_center) / d * self.ANGLE_MAX
        self.__log.debug("pulse=%s, deg=%s", pulse, deg)
        return deg

    def get_angle(self):
        """Get current angle (deg)."""
        pulse = self.get_pulse()
        angle = self.pulse2deg(pulse)
        self.__log.debug("pulse=%s, angle=%s", pulse, angle)
        return angle

    def move_angle(self, deg: float | str | None = None):
        """Move angle."""
        self.__log.debug("pin=%s, deg=%s", self.pin, deg)

        if deg is None:
            deg = self.get_angle()
        elif isinstance(deg, str):
            if deg == self.POS_CENTER:
                deg = self.ANGLE_CENTER
            elif deg == self.POS_MIN:
                deg = self.ANGLE_MIN
            elif deg == self.POS_MAX:
                deg = self.ANGLE_MAX
            elif deg == "":
                deg = self.get_angle()
            else:
                self.__log.error('deg="%s": invalid string. do nothing', deg)
                return

        deg = max(min(deg, self.ANGLE_MAX), self.ANGLE_MIN)
        self.__log.debug("deg=%s", deg)
        pulse = self.deg2pulse(float(deg))
        self.move_pulse(pulse)

    def move_angle_relative(self, deg_diff: float):
        """Move relative."""
        self.__log.debug("pin=%s, deg_diff=%s", self.pin, deg_diff)
        _cur_angle = self.get_angle()
        self.__log.debug("cur_angle=%s", _cur_angle)
        self.move_angle(_cur_angle + deg_diff)

    def load_conf(self):
        """設定ファイルからこのサーボのキャリブレーション値を読み込む。"""
        config = self._config_manager.get_config(self.pin)
        if config:
            self._pulse_min = config.get("min", super().MIN)
            self._pulse_center = config.get("center", super().CENTER)
            self._pulse_max = config.get("max", super().MAX)
            self.__log.debug("Loaded config for pin %s", self.pin)
        else:
            # Safe defaults for a new servo
            self.__log.warning("No config for pin %s. Using safe defaults.", self.pin)
            self._pulse_min = super().CENTER
            self._pulse_center = super().CENTER
            self._pulse_max = super().CENTER
            self.save_conf()

    def save_conf(self):
        """現在のキャリブレーション値を設定ファイルに保存する。"""
        new_config = {
            "pin": self.pin,
            "min": self.pulse_min,
            "center": self.pulse_center,
            "max": self.pulse_max,
        }
        self._config_manager.save_config(new_config)
        self.__log.debug("Saved: %s", new_config)