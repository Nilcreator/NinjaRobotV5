#
# (c) 2025 Yoichi Tanibayashi
#
import json
import queue
import threading
import time

from ..core.multi_servo import MultiServo
from ninja_utils.my_logger import get_logger


class ThreadWorker(threading.Thread):
    """Thred worker.

    すべてのコマンドは、JSON形式で、キューを介して受け渡される。

    利用者は、コマンドを`send()`したら、ブロックせずに、
    非同期に他の処理を行える。

    `Worker`は、コマンドキューから一つずつコマンドを取り出し、
    順に実行する。

    コマンドをキャンセルしたい場合は、`clear_cmdq()`で、
    キューに溜まっているコマンドをすべてキャンセルできる。

    **コマンド一覧(例)**
    
    {"cmd": "move_all_angles_sync",
     "angles": [30, None, "center"],   # mandatory
     "move_sec": 0.2, "step_n": 40}    # optional

    {"cmd": "move",                    # "move_all_angles_sync"の省略形
     "angles": [30, None, "center"],   # mandatory
     "move_sec": 0.2, "step_n": 40}    # optional

    {"cmd": "move_all_angles", "angles": [30, None, "center"]}
    {"cmd": "move_all_pulses", "pulses": [1000, 2000, None, 0]}

    {"cmd": "move_sec", "sec": 1.5}
    {"cmd": "step_n", "n": 40}
    {"cmd": "interval", "sec": 0.5}
    {"cmd": "sleep", "sec": 1.0}

    # for calibration
    {"cmd": "move_pulse_relative", "servo": 2, "pulse_diff": -20}
    {"cmd": "set", "servo": 1, "target": "center"}
    """

    DEF_RECV_TIMEOUT = 0.2  # sec
    DEF_INTERVAL_SEC = 0.0  # sec

    CMD_CANCEL = "cancel"

    def __init__(
        self,
        mservo: MultiServo,
        move_sec: float | None = None,
        step_n: int | None = None,
        interval_sec: float = DEF_INTERVAL_SEC,
        debug=False,
    ):
        """Constructor."""
        super().__init__(daemon=True)

        self._debug = debug
        self.__log = get_logger(self.__class__.__name__, self._debug)

        self.mservo = mservo

        if move_sec is None:
            self.move_sec = mservo.DEF_MOVE_SEC
        else:
            self.move_sec = move_sec

        if step_n is None:
            self.step_n = mservo.DEF_STEP_N
        else:
            self.step_n = step_n

        self.interval_sec = interval_sec

        self.__log.debug(
            "move_sec=%s, step_n=%s, interval_sec=%s",
            move_sec, step_n, interval_sec
        )

        self._cmdq: queue.Queue = queue.Queue()
        self._active = False

        self._command_handlers = {
            "move":
            self._handle_move_all_angles_sync,

            "move_all_angles_sync":
            self._handle_move_all_angles_sync,

            "move_all_angles_sync_relative":
            self._handle_move_all_angles_sync_relative,

            "move_all_angles":
            self._handle_move_all_angles,

            "move_all_pulses_relative":
            self._handle_move_all_pulses_relative,

            "move_sec": self._handle_move_sec,
            "step_n": self._handle_step_n,
            "interval": self._handle_interval,
            "sleep": self._handle_sleep,
            "set": self._handle_set,
        }

    def __del__(self):
        """del"""
        self._active = False
        self.__log.debug("")

    def end(self):
        """end worker"""
        self.__log.debug("")
        self._active = False
        self.clear_cmdq()
        self.join()
        self.__log.debug("done")

    def clear_cmdq(self):
        """clear command queue"""
        _count = 0
        while not self._cmdq.empty():
            _count += 1
            _cmd = self._cmdq.get()
            self.__log.debug("%2d:%s", _count, _cmd)

        self.__log.debug("count=%s", _count)
        return _count

    def cancel_cmds(self):
        """Alias of clear_cmdq()."""
        self.__log.debug("")
        return self.clear_cmdq()

    def send(self, cmd_data):
        """send"""
        try:
            if isinstance(cmd_data, str):
                cmd_data = json.loads(cmd_data)

            if cmd_data.get("cmd") == self.CMD_CANCEL:
                cmd_data["count"] = self.clear_cmdq()
            else:
                self._cmdq.put(cmd_data)

            self.__log.debug(
                "cmd_data=%s, qsize=%s", cmd_data, self._cmdq.qsize()
            )

        except Exception as _e:
            self.__log.error("%s: %s", type(_e).__name__, _e)

        return cmd_data

    def recv(self, timeout=DEF_RECV_TIMEOUT):
        """recv"""
        try:
            _cmd_data = self._cmdq.get(timeout=timeout)
        except queue.Empty:
            _cmd_data = ""

        return _cmd_data

    def _handle_move_all_angles_sync(self, cmd: dict):
        """Handle move_all_angles_sync().

        e.g. {"cmd": "move_all_angles_sync", "angles": [30, None, -30, 0],
          "move_sec": 0.2,  # optional
          "step_n": 40  # optional
        }
        """
        _angles = cmd["angles"]

        _move_sec = cmd.get("move_sec")
        if _move_sec is None:
            _move_sec = self.move_sec

        _step_n = cmd.get("step_n")
        if _step_n is None:
            _step_n = self.step_n

        self.mservo.move_all_angles_sync(_angles, _move_sec, _step_n)
        self._sleep_interval()

    def _handle_move_all_angles_sync_relative(self, cmd: dict):
        """Handle move_all_angles_sync_relative().

        e.g. {
          "cmd": "move_all_angles_sync_relative",
          "angle_diffs": [10, -10, 0, 0],
          "move_sec": 0.2,  # optional
          "step_n": 40  # optional
        }
        """
        _angle_diffs = cmd["angle_diffs"]

        _move_sec = cmd.get("move_sec")
        if _move_sec is None:
            _move_sec = self.move_sec

        _step_n = cmd.get("step_n")
        if _step_n is None:
            _step_n = self.step_n

        self.mservo.move_all_angles_sync_relative(
            _angle_diffs, _move_sec, _step_n
        )
        self._sleep_interval()

    def _handle_move_all_angles(self, cmd: dict):
        """Handle move_all_angles().

        e.g. {"cmd": "move_all_angles", "angles": [30, None, -30, 0]}
        """
        _angles = cmd["angles"]
        self.mservo.move_all_angles(_angles)
        self._sleep_interval()

    def _handle_move_all_pulses_relative(self, cmd: dict):
        """Handle move_all_angles().

        e.g. {
               "cmd": "move_all_pulses_relative",
               "pulse_diffs": [2000, 1000, None, 0]
             }
        """
        _pulse_diffs = cmd["pulse_diffs"]
        self.mservo.move_all_pulses_relative(_pulse_diffs, forced=True)
        self._sleep_interval()

    def _handle_move_sec(self, cmd: dict):
        """Handle move_sec.

        e.g. {"cmd": "move_sec", "sec": 1.5}
        """
        self.move_sec = float(cmd["sec"])
        self.__log.debug("move_sec=%s", self.move_sec)

    def _handle_step_n(self, cmd: dict):
        """Handle step_n.

        e.g. {"cmd": "step_n", "n": 40}
        """
        self.step_n = int(cmd["n"])
        self.__log.debug("step_n=%s", self.step_n)

    def _handle_interval(self, cmd: dict):
        """Handle interval.

        e.g. {"cmd": "interval", "sec": 0.5}
        """
        self.interval_sec = float(cmd["sec"])
        self.__log.debug("set interval_sec=%s", self.interval_sec)

    def _handle_sleep(self, cmd: dict):
        """Handle sleep.

        e.g. {"cmd": "sleep", "sec": 1.0}
        """
        _sec = float(cmd["sec"])
        self.__log.debug("sleep: %s sec", _sec)
        if _sec > 0.0:
            time.sleep(_sec)

    def _sleep_interval(self):
        """sleep interval"""
        if self.interval_sec > 0:
            self.__log.debug("sleep interval_sec: %s sec", self.interval_sec)
            time.sleep(self.interval_sec)

    def _handle_move_pulse_relative(self, cmd: dict):
        """Handle move pulse relative.

        e.g. {"cmd": "move_pulse_relative", "servo": 2, "pulse_diff": -20}
        """
        servo = int(cmd["servo"])
        pulse_diff = int(cmd["pulse_diff"])
        self.__log.debug("servo=%s, pulse_diff=%s", servo, pulse_diff)

        self.mservo.move_pulse_relative(servo, pulse_diff, forced=True)

    def _handle_set(self, cmd: dict):
        """Handle set cmd. (save calibration)

        e.g. {"cmd": "set", "servo": 1, "target": "max"}

        * pulse is current value.
        """
        _servo = int(cmd["servo"])
        _target = cmd["target"]
        
        self.__log.debug("set: servo:%s", _servo)
 
        if _target == "center":
            self.mservo.set_pulse_center(_servo)
        elif _target == "min":
            self.mservo.set_pulse_min(_servo)
        elif _target == "max":
            self.mservo.set_pulse_max(_servo)
        else:
            self.__log.warning("Invalid target: %s", _target)

    def _dispatch_cmd(self, cmd_data: dict):
        """Dispatch command."""
        self.__log.debug("cmd_data=%a", cmd_data)

        _cmd_str = cmd_data.get("cmd")
        if not _cmd_str:
            self.__log.error("invalid command (no 'cmd' key): %s", cmd_data)
            return

        handler = self._command_handlers.get(_cmd_str)
        if handler:
            handler(cmd_data)
        else:
            self.__log.error("unknown command: %s", cmd_data)

    def run(self):
        """run"""
        self.__log.debug("start")

        self._active = True

        while self._active:
            _cmd_data = self.recv()
            if not _cmd_data:
                continue

            self.__log.debug("qsize=%s", self._cmdq.qsize())
            try:
                self._dispatch_cmd(_cmd_data)

            except Exception as _e:
                self.__log.error("%s: %s", type(_e).__name__, _e)

        self.__log.debug("done")
