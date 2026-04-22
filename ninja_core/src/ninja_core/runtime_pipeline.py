from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .facial_expressions import AnimatedFaces
    from .hal import HardwareAbstractionLayer
    from .robot_sound import RobotSoundPlayer

log = logging.getLogger(__name__)


class RuntimePipeline:
    """Coordinate native robot behavior with uploaded Blockly execution."""

    def __init__(
        self,
        hal: HardwareAbstractionLayer | None = None,
        faces: AnimatedFaces | None = None,
        sound: RobotSoundPlayer | None = None,
    ):
        self.hal = hal
        self.faces = faces
        self.sound = sound
        self._lock = threading.RLock()
        self._mode = "native"
        self._display_hold = False

    @property
    def mode(self) -> str:
        with self._lock:
            return self._mode

    def attach_hal(self, hal: HardwareAbstractionLayer):
        with self._lock:
            self.hal = hal

    def attach_faces(self, faces: AnimatedFaces):
        with self._lock:
            self.faces = faces

    def attach_sound(self, sound: RobotSoundPlayer):
        with self._lock:
            self.sound = sound

    def begin_blockly(self):
        """Give uploaded code exclusive control over transient robot output."""
        with self._lock:
            self._mode = "blockly"
            self._display_hold = False
            self._stop_native_locked()

    def mark_display_hold(self):
        """Keep the display blank after a Blockly clear command completes."""
        with self._lock:
            if self._mode == "blockly":
                self._display_hold = True

    def complete_blockly(self, status: str | None = None):
        """Return to native behavior after uploaded code finishes."""
        with self._lock:
            if self._mode not in {"blockly", "blockly_hold"}:
                return
            if status == "success" and self._display_hold:
                self._mode = "blockly_hold"
                return
            self._resume_native_locked()

    def abort_blockly(self):
        """Cancel Blockly ownership and immediately restore native idle."""
        with self._lock:
            self._display_hold = False
            self._resume_native_locked()

    def reclaim_native(self):
        """Let direct web/native interactions reclaim the robot."""
        with self._lock:
            if self._mode == "native":
                return
            self._display_hold = False
            self._resume_native_locked()

    def _stop_native_locked(self):
        if self.faces:
            try:
                self.faces.stop()
            except Exception as exc:
                log.warning("Failed to stop native face animation: %s", exc)

        if self.sound and hasattr(self.sound, "stop"):
            try:
                self.sound.stop(restart_buzzer=True)
            except Exception as exc:
                log.warning("Failed to stop native sound: %s", exc)

        servos = getattr(self.hal, "servos", None) if self.hal else None
        if servos and hasattr(servos, "abort"):
            try:
                servos.abort()
            except Exception as exc:
                log.warning("Failed to abort native servo motion: %s", exc)

    def _resume_native_locked(self):
        self._mode = "native"
        self._display_hold = False
        if self.faces:
            try:
                self.faces.play("idle", duration_s=float("inf"))
            except Exception as exc:
                log.warning("Failed to resume native idle face: %s", exc)
