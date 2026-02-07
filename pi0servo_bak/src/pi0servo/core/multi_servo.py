#
# (c) 2025 Yoichi Tanibayashi
#
"""multi_servo.py

V5 Changes:
- Implements Actuator ABC from ninja_utils.interfaces
- Added initialize() and execute() methods for standardized interface
"""
import time
from typing import Any

from ninja_utils import Actuator, get_logger
from .calibrable_servo import CalibrableServo


class MultiServo(Actuator):
    """
    Multi-servo controller implementing the Actuator interface.
    
    Controls multiple servo motors simultaneously with support for
    synchronized movements and calibration.
    """

    DEF_MOVE_SEC = 0.2  # sec
    DEF_STEP_N = 40

    def initialize(self) -> None:
        """Initialize the servos (Actuator interface).
        
        Note: Servos are already initialized in __init__, so this method
        centers all servos as a safe default state.
        """
        self.move_all_angles([0] * self.servo_n)

    def execute(self, command: dict[str, Any]) -> None:
        """Execute a servo command (Actuator interface).
        
        Args:
            command: A dictionary containing one of:
                - "angles" (list[float]): Target angles for all servos.
                - "pin" (int) + "angle" (float): Move a single servo.
                - "sync" (bool): If True, use synchronized smooth movement.
        
        Example:
            servo.execute({"angles": [0, 45, -30, 0, 0, 0, 0, 0]})
            servo.execute({"pin": 20, "angle": 45})
            servo.execute({"angles": [0, 0, 0, 0, 0, 0, 0, 0], "sync": True})
        """
        if "angles" in command:
            angles = command["angles"]
            if command.get("sync", False):
                self.move_all_angles_sync(angles)
            else:
                self.move_all_angles(angles)
        elif "pin" in command and "angle" in command:
            pin = command["pin"]
            angle = command["angle"]
            # Find the servo index for the given pin
            if pin in self.pins:
                idx = self.pins.index(pin)
                self.servo[idx].move_angle(angle)


    def __init__(
        self,
        pi,
        pins: list[int],
        first_move=True,
        conf_file=CalibrableServo.DEF_CONF_FILE,
        debug=False,
    ):
        """
        MultiServoのインスタンスを初期化する。

        Parameters
        ----------
        pi: pigpio.pi
            pigpio.piのインスタンス。
        pins: list[int]
            サーボモーターを接続したGPIOピンのリスト。
        first_move: bool
            Trueの場合、初期化時にサーボを0度の位置に移動させる。
        conf_file: str
            キャリブレーション設定ファイルのパス。
        debug: bool
            デバッグモードを有効にするかどうかのフラグ。
        """
        self._debug = debug
        self.__log = get_logger(self.__class__.__name__)
        self.__log.debug(
            "pins=%s, first_move=%s, conf_file=%s",
            pins, first_move, conf_file
        )

        self._pi = pi
        self.pins = pins
        self.first_move = first_move

        self.servo_n = len(pins)

        self.servo = [
            CalibrableServo(self._pi, _pin, conf_file=conf_file, debug=False)
            for _pin in self.pins
        ]

        self.conf_file = self.servo[0].conf_file
        self.__log.debug("conf_file=%s", self.conf_file)

        if self.first_move:
            self.move_all_angles([0] * self.servo_n)

    def __getattr__(self, name):
        """
        存在しない属性が呼び出された場合に、
        各サーボの同名メソッドを呼び出す。
        """
        self.__log.debug("name=%s", name)

        # 各サーボインスタンスに同じ名前のメソッドが存在するか確認
        if not all(
                hasattr(s, name) and callable(getattr(s, name))
                for s in self.servo
        ):
            msg = (
                f"'{self.__class__.__name__}' object and its servos "
                f"have no attribute '{name}'"
            )
            raise AttributeError(msg)

        def method(*args, **kwargs):
            results = []
            for s in self.servo:
                # 各サーボのメソッドを呼び出す
                result = getattr(s, name)(*args, **kwargs)
                results.append(result)

            # 結果がすべてNoneならNoneを、そうでなければ結果のリストを返す
            if all(r is None for r in results):
                return None
            return results

        return method

    def get_pulse_center(self, index: int):
        """Get center(0 deg) pulse.

        Returns
        -------
        pulse: int
        """
        return self.servo[index].pulse_center

    def set_pulse_center(self, index: int, pulse: int | None = None):
        """Set center(0 deg) pulse.
        設定した値は、`conf_file`に保存される。

        Parameters
        ----------
        index: int
            index of servo
        pulse: int | None
            None: current pulse
        """
        if pulse is None:
            pulse = self.servo[index].get_pulse()

        self.__log.debug("index=%s, pulse=%s", index, pulse)

        self.servo[index].pulse_center = pulse
        return pulse

    def get_pulse_min(self, index: int):
        """Get min(-90 deg) pulse.

        Returns
        -------
        pulse: int
        """
        return self.servo[index].pulse_min

    def set_pulse_min(self, index: int, pulse: int | None = None):
        """Set min(-90) pulse.
        設定した値は、`conf_file`に保存される。

        Parameters
        ----------
        index: int
            index of servo
        pulse: int | None
            None: current pulse
        """
        if pulse is None:
            pulse = self.servo[index].get_pulse()

        self.__log.debug("index=%s, pulse=%s", index, pulse)

        self.servo[index].pulse_min = pulse
        return pulse

    def get_pulse_max(self, index: int):
        """Get max(90 deg) pulse.

        Returns
        -------
        pulse: int
        """
        return self.servo[index].pulse_max

    def set_pulse_max(self, index: int, pulse: int | None = None):
        """Set max(90 deg) pulse.
        設定した値は、`conf_file`に保存される。

        Parameters
        ----------
        index: int
            index of servo
        pulse: int
            None: current pulse
        """
        if pulse is None:
            pulse = self.servo[index].get_pulse()

        self.__log.debug("index=%s, pulse=%s", index, pulse)

        self.servo[index].pulse_max = pulse
        return pulse

    def _validate_pulse_list(self, pulses):
        """
        パルス幅のリストを検証する。
        有効な場合はTrue、そうでない場合はFalseを返す。

        Parameters
        ----------
        pulses: list[int] or tuple[int]
            検証するパルス幅のリストまたはタプル。

        Returns
        -------
        bool
            検証結果。
        """
        if not isinstance(pulses, (list, tuple)):
            self.__log.error(
                "pulses:%s must be list or tupple:%s", pulses, type(pulses)
            )
            return False

        if len(pulses) != self.servo_n:
            self.__log.error(
                "len(%s)=%s != servo_n=%s", pulses, len(pulses), self.servo_n
            )
            return False

        return True

    def _validate_angle_list(self, angles):
        """
        角度のリストを検証する。
        有効な場合はTrue、そうでない場合はFalseを返す。

        Parameters
        ----------
        angles: list[float] or tuple[float]
            検証する角度のリストまたはタプル。

        Returns
        -------
        bool
            検証結果。
        """
        if not isinstance(angles, (list, tuple)):
            self.__log.error(
                "angles:%s must be list or tupple:%s", angles, type(angles)
            )
            return False

        if len(angles) != self.servo_n:
            self.__log.error(
                "len(%s)=%s != servo_n=%s", angles, len(angles), self.servo_n
            )
            return False

        return True

    def off(self):
        """
        すべてのサーボをオフにする。
        """
        self.__log.debug("")
        for s in self.servo:
            s.off()

    def get_pulse(self, idx: int) -> int:
        """Get pulse of servo[idx].
        """
        _pulse = self.servo[idx].get_pulse()
        self.__log.debug("idx=%s, pulse=%s", idx, _pulse)
        return _pulse

    def get_all_pulses(self):
        """Get pulses of all servos.

        Returns
        -------
        list[int]
            各サーボのパルス幅のリスト。
        """
        pulses = [s.get_pulse() for s in self.servo]
        self.__log.debug("pulses=%s", pulses)
        return pulses

    def move_pulse(self, idx, pulse, forced=False):
        """Move one servo[idx].
        """
        self.servo[idx].move_pulse(pulse, forced)

    def move_all_pulses(self, pulses, forced=False):
        """Move all servos to `pulse`.

        Parameters
        ----------
        pulses: list[int]
            各サーボに設定するパルス幅のリスト。
            `None`の場合は、動かさない
        forced: bool
            `True`の場合、可動範囲外のパルス幅も強制的に設定する。
        """
        for i in range(len(self.servo)):
            self.move_pulse(i, pulses[i], forced)

    def move_pulse_relative(self, idx: int, pulse_diff: int, forced=False):
        """Relative move one servo[idx].
        """
        self.__log.debug(
            "idx=%s, pulse_diff=%s, forced=%s", idx, pulse_diff, forced
        )
        _new_pulse = self.get_pulse(idx) + pulse_diff
        self.__log.debug("new_pulse=%s", _new_pulse)

        self.move_pulse(idx, _new_pulse, forced)

    def move_all_pulses_relative(self, pulse_diffs, forced=False):
        """Relative move all servos.

        Args:
            pulse_diffs (List[int]):
        """
        self.__log.debug("pulse_diffs=%s, force=%s", pulse_diffs, forced)

        _cur_pulses = self.get_all_pulses()
        self.__log.debug("cur_pulses=%s", _cur_pulses)

        _new_pulses = [
            _cur_pulses[i] + pulse_diffs[i] for i in range(len(self.servo))
        ]
        self.__log.debug("new_pulses=%s", _new_pulses)

        self.move_all_pulses(_new_pulses, forced=forced)

    def get_all_angles(self) -> list[float]:
        """
        すべてのサーボの現在の角度を取得する。

        Returns
        -------
        list[float]
            各サーボの角度のリスト。
        """
        angles = [s.get_angle() for s in self.servo]
        self.__log.debug("angles=%s", angles)
        return angles

    def move_all_angles(self, target_angles):
        """
        各サーボを指定された角度に動かす。

        Parameters
        ----------
        target_angles: list[float]
            各サーボに設定する角度のリスト。
        """
        self.__log.debug("target_angles=%s", target_angles)

        if not self._validate_angle_list(target_angles):
            return

        for _i, _s in enumerate(self.servo):
            # self.__log.debug("pin=%s, angle=%s", _s.pin, target_angles[_i])
            _s.move_angle(target_angles[_i])

    def move_all_angles_relative(self, angle_diffs):
        """Relative Move.

        Args:
            angle_diffs (List[float]):
        """
        self.__log.debug("angle_diffs=%s", angle_diffs)

        _cur_angles = self.get_all_angles()
        self.__log.debug("cur_angles=%s", _cur_angles)

        _new_angles = [
            _cur_angles[i] + angle_diffs[i] for i in range(len(self.servo))
        ]
        self.__log.debug("new_angles=%s", _new_angles)

        self.move_angle(_new_angles)

    def move_all_angles_sync(
        self,
        target_angles,
        move_sec: float = DEF_MOVE_SEC,
        step_n: int = DEF_STEP_N
    ):
        """
        すべてのサーボを目標角度まで同期的かつ滑らかに動かす。
        角度は、数値だけでなく、文字列、Noneでも指定できる。

        Parameters
        ----------
        target_angles: list[float]
            各サーボの目標角度のリスト。
            None: 現在の角度(つまり、動かさない)
            文字列: "center", "min", "max"
        move_sec: float
            動作にかかるおおよその時間（秒）。
        step_n: int
            動作を分割するステップ数。
            1以下の場合は、move_angle() を呼び出して、ダイレクトに動かす
        """
        self.__log.debug(
            "target_angles=%s, move_sec=%s, step_n=%s",
            target_angles, move_sec, step_n
        )

        if not self._validate_angle_list(target_angles):
            return

        # step_n が１以下の場合は、ダイレクトに動かす
        if step_n <= 1:
            self.move_all_angles(target_angles)
            return

        _step_sec = move_sec / step_n
        self.__log.debug("_step_sec=%.3f", _step_sec)

        _start_angles = self.get_all_angles()
        self.__log.debug("_start_angles=%s", _start_angles)

        # target_anglesを数値(角度)に変換
        _num_target_angles = []
        for i, _angle in enumerate(target_angles):
            _servo = self.servo[i]

            if isinstance(_angle, str):
                if _angle == _servo.POS_CENTER:
                    _num_target_angles.append(_servo.ANGLE_CENTER)
                elif _angle == _servo.POS_MIN:
                    _num_target_angles.append(_servo.ANGLE_MIN)
                elif _angle == _servo.POS_MAX:
                    _num_target_angles.append(_servo.ANGLE_MAX)
                else:  # 不明な文字: 動かさない
                    self.__log.warning("invalid word %a: ignored", _angle)
                    _num_target_angles.append(_start_angles[i])

            elif _angle is None:  # None は、「動かさない」の意味
                _num_target_angles.append(_start_angles[i])

            else:  # num
                # clip: ANGLE_MIN <= _angle <= ANGLE_MAX
                _angle = max(min(_angle, _servo.ANGLE_MAX), _servo.ANGLE_MIN)
                _num_target_angles.append(_angle)

        self.__log.debug("_num_target_angles=%s", _num_target_angles)

        _angle_diffs = [
            _num_target_angles[i] - _start_angles[i]
            for i in range(self.servo_n)
        ]
        self.__log.debug("_angle_diffs=%s", _angle_diffs)

        for _step_i in range(1, step_n + 1):
            next_angles = [
                _start_angles[i] + _angle_diffs[i] * _step_i / step_n
                for i in range(self.servo_n)
            ]

            self.move_all_angles(next_angles)
            # self.__log.debug(
            #     "step %s/%s: next_angles=%s, _step_sec=%s",
            #     _step_i, step_n, next_angles, _step_sec
            # )
            time.sleep(_step_sec)

    def move_angle_sync_relative(
        self,
        angle_diffs: list[float],
        move_sec: float = DEF_MOVE_SEC,
        step_n: int = DEF_STEP_N
    ):
        """Relative Move.
        """
        self.__log.debug(
            "angle_diffs=%s, move_sec=%s, step_n=%s",
            angle_diffs, move_sec, step_n
        )

        _cur_angles = self.get_all_angles()
        self.__log.debug("cur_angles=%s", _cur_angles)

        _new_angles = [
            _cur_angles[i] + angle_diffs[i] for i in range(len(self.servo))
        ]
        self.__log.debug("new_angles=%s", _cur_angles)

        self.move_angle_sync(_new_angles, move_sec, step_n)
