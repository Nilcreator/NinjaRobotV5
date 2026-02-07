"""Multi-servo group controller with abort support.

This module provides the ServoGroup class which handles:
- Coordinated multi-servo movement
- Abort mechanism via threading.Event
- Velocity-based duration calculation
- Easing curves for smooth motion
"""

import asyncio
import logging
import threading
from typing import Callable

# Optional ninja_utils integration (fallback to standard logging)
try:
    from ninja_utils import get_module_logger
    logger = get_module_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

from ..motion import (
    EASING_FUNCTIONS,
    calculate_duration,
    calculate_step_count,
    ease_out,
)
from ..parser import ParsedCommand, ServoTarget, parse_command, resolve_special_angle
from .servo import Servo, ServoCalibration

# Default step interval for motion interpolation (20ms = 50Hz)
STEP_INTERVAL = 0.02


class ServoGroup:
    """Multi-servo controller with synchronized movement and abort support.

    Implements the Actuator interface from ninja_utils.

    Key features:
    - Coordinated movement of multiple servos with easing
    - Abortable motion via threading.Event (sync) or asyncio.Event (async)
    - Velocity-based duration calculation (respects per-servo speed limits)
    - Command string parsing (movement-tool format)
    """

    def __init__(
        self,
        pi,
        pins: list[int],
        calibrations: dict[int, ServoCalibration] | None = None,
    ):
        """Initialize a ServoGroup.

        Args:
            pi: pigpio.pi() instance
            pins: List of GPIO pin numbers
            calibrations: Optional dict mapping pin to ServoCalibration
        """
        self._pi = pi
        self._pins = list(pins)
        self._servos: dict[int, Servo] = {}
        self._abort_event = threading.Event()
        self._async_abort_event = asyncio.Event()

        # Create Servo instances
        calibrations = calibrations or {}
        for pin in self._pins:
            cal = calibrations.get(pin)
            self._servos[pin] = Servo(pi, pin, cal)

    @property
    def pins(self) -> list[int]:
        """List of GPIO pins."""
        return list(self._pins)

    @property
    def servos(self) -> dict[int, Servo]:
        """Dictionary of pin -> Servo."""
        return self._servos

    def get_servo(self, pin: int) -> Servo | None:
        """Get a Servo by pin number.

        Args:
            pin: GPIO pin number

        Returns:
            Servo instance or None if not found
        """
        return self._servos.get(pin)

    def update_calibration(self, pin: int, calibration: ServoCalibration):
        """Update calibration for a specific servo.

        Args:
            pin: GPIO pin number
            calibration: New calibration data
        """
        if pin in self._servos:
            self._servos[pin].calibration = calibration

    def abort(self):
        """Signal abort for any running movement.

        Thread-safe. Can be called from any thread.
        """
        logger.info("Abort signal received")
        self._abort_event.set()
        self._async_abort_event.set()

    def _reset_abort(self):
        """Reset abort events for new movement."""
        self._abort_event.clear()
        self._async_abort_event.clear()

    def _is_aborted(self) -> bool:
        """Check if abort was signaled."""
        return self._abort_event.is_set()

    def _abortable_sleep(self, duration: float) -> bool:
        """Sleep that can be interrupted by abort.

        Args:
            duration: Sleep duration in seconds

        Returns:
            True if slept fully, False if aborted
        """
        if self._abort_event.wait(timeout=duration):
            logger.info("Sleep aborted after partial wait")
            return False
        return True

    async def _abortable_sleep_async(self, duration: float) -> bool:
        """Async sleep that can be interrupted by abort.

        Args:
            duration: Sleep duration in seconds

        Returns:
            True if slept fully, False if aborted
        """
        try:
            await asyncio.wait_for(
                self._async_abort_event.wait(),
                timeout=duration,
            )
            # If we get here, abort was signaled
            logger.info("Async sleep aborted")
            return False
        except asyncio.TimeoutError:
            # Normal case - sleep completed without abort
            return True

    def move_all_sync(
        self,
        targets: list[float | None],
        speed_mode: str = "M",
        easing: str | Callable[[float], float] = "ease_out",
    ) -> bool:
        """Move all servos to target angles with synchronized motion.

        Uses velocity-based duration calculation (slowest servo determines time).
        Motion is abortable via the abort() method.

        Args:
            targets: List of target angles (same order as pins). None = skip.
            speed_mode: "F" (Fast), "M" (Medium), "S" (Slow)
            easing: Easing function name or callable

        Returns:
            True if completed successfully, False if aborted
        """
        self._reset_abort()

        # Resolve easing function
        if isinstance(easing, str):
            easing_fn = EASING_FUNCTIONS.get(easing, ease_out)
        else:
            easing_fn = easing

        # Build movement plan
        movements: list[tuple[Servo, float, float]] = []  # (servo, start, end)
        max_duration = 0.0

        for i, pin in enumerate(self._pins):
            if i >= len(targets) or targets[i] is None:
                continue

            servo = self._servos[pin]
            target = targets[i]

            # Get current angle (default to center if unknown)
            current = servo.last_angle
            if current is None:
                current = servo.get_angle()
            if current is None:
                current = servo.calibration.angle_center

            distance = abs(target - current)
            if distance < 0.1:  # Skip negligible movement
                continue

            duration = calculate_duration(distance, servo.speed_limit, speed_mode)
            max_duration = max(max_duration, duration)
            movements.append((servo, current, target))

        if not movements:
            logger.debug("No movement required")
            return True

        step_count = calculate_step_count(max_duration, STEP_INTERVAL)
        logger.info(
            f"Moving {len(movements)} servos, duration={max_duration:.2f}s, steps={step_count}"
        )

        # Execute interpolated movement
        for step in range(1, step_count + 1):
            if self._is_aborted():
                logger.info(f"Movement aborted at step {step}/{step_count}")
                return False

            t = step / step_count
            eased_t = easing_fn(t)

            for servo, start, end in movements:
                angle = start + (end - start) * eased_t
                servo.set_angle(angle)

            if not self._abortable_sleep(STEP_INTERVAL):
                return False

        logger.debug("Movement completed successfully")
        return True

    async def move_all_async(
        self,
        targets: list[float | None],
        speed_mode: str = "M",
        easing: str | Callable[[float], float] = "ease_out",
    ) -> bool:
        """Async version of move_all_sync.

        Non-blocking movement using asyncio.sleep instead of time.sleep.

        Args:
            targets: List of target angles (same order as pins). None = skip.
            speed_mode: "F" (Fast), "M" (Medium), "S" (Slow)
            easing: Easing function name or callable

        Returns:
            True if completed successfully, False if aborted
        """
        self._reset_abort()

        # Resolve easing function
        if isinstance(easing, str):
            easing_fn = EASING_FUNCTIONS.get(easing, ease_out)
        else:
            easing_fn = easing

        # Build movement plan (same as sync)
        movements: list[tuple[Servo, float, float]] = []
        max_duration = 0.0

        for i, pin in enumerate(self._pins):
            if i >= len(targets) or targets[i] is None:
                continue

            servo = self._servos[pin]
            target = targets[i]

            current = servo.last_angle
            if current is None:
                current = servo.get_angle()
            if current is None:
                current = servo.calibration.angle_center

            distance = abs(target - current)
            if distance < 0.1:
                continue

            duration = calculate_duration(distance, servo.speed_limit, speed_mode)
            max_duration = max(max_duration, duration)
            movements.append((servo, current, target))

        if not movements:
            return True

        step_count = calculate_step_count(max_duration, STEP_INTERVAL)

        for step in range(1, step_count + 1):
            if self._async_abort_event.is_set():
                return False

            t = step / step_count
            eased_t = easing_fn(t)

            for servo, start, end in movements:
                angle = start + (end - start) * eased_t
                servo.set_angle(angle)

            if not await self._abortable_sleep_async(STEP_INTERVAL):
                return False

        return True

    def execute_command(
        self,
        command: str,
        easing: str | Callable[[float], float] = "ease_out",
    ) -> bool:
        """Execute a movement-tool format command string.

        Format: [SPEED_]PIN:ANGLE[/PIN:ANGLE...]

        Args:
            command: Command string (e.g., "F_20:45/21:-30")
            easing: Easing function name or callable

        Returns:
            True if completed successfully, False if aborted
        """
        parsed = parse_command(command)
        return self._execute_parsed(parsed, easing)

    async def execute_command_async(
        self,
        command: str,
        easing: str | Callable[[float], float] = "ease_out",
    ) -> bool:
        """Async version of execute_command.

        Args:
            command: Command string
            easing: Easing function name or callable

        Returns:
            True if completed successfully, False if aborted
        """
        parsed = parse_command(command)
        return await self._execute_parsed_async(parsed, easing)

    def _execute_parsed(
        self,
        parsed: ParsedCommand,
        easing: str | Callable[[float], float],
    ) -> bool:
        """Execute a parsed command."""
        targets = self._resolve_targets(parsed.targets)
        return self.move_all_sync(targets, parsed.speed_mode, easing)

    async def _execute_parsed_async(
        self,
        parsed: ParsedCommand,
        easing: str | Callable[[float], float],
    ) -> bool:
        """Async execution of parsed command."""
        targets = self._resolve_targets(parsed.targets)
        return await self.move_all_async(targets, parsed.speed_mode, easing)

    def _resolve_targets(self, targets: list[ServoTarget]) -> list[float | None]:
        """Convert ServoTargets to angle list indexed by pin order."""
        result: list[float | None] = [None] * len(self._pins)

        for target in targets:
            if target.pin not in self._servos:
                logger.warning(f"Unknown pin in command: {target.pin}")
                continue

            pin_index = self._pins.index(target.pin)
            servo = self._servos[target.pin]

            if target.angle is not None:
                result[pin_index] = target.angle
            elif target.special:
                # Resolve special position using servo calibration
                cal_dict = {
                    "angle_center": servo.calibration.angle_center,
                    "angle_min": servo.calibration.angle_min,
                    "angle_max": servo.calibration.angle_max,
                }
                result[pin_index] = resolve_special_angle(target.special, cal_dict)

        return result

    # --- Actuator Interface (ninja_utils) ---

    def initialize(self):
        """Initialize all servos (Actuator interface)."""
        logger.info(f"ServoGroup initialized with pins: {self._pins}")

    def execute(self, command: str) -> dict:
        """Execute a command (Actuator interface).

        Args:
            command: Movement-tool format string

        Returns:
            Dict with 'success' bool and 'message' string
        """
        try:
            success = self.execute_command(command)
            return {
                "success": success,
                "message": "Completed" if success else "Aborted",
            }
        except ValueError as e:
            return {"success": False, "message": str(e)}

    def off(self):
        """Turn off all servos (Actuator interface)."""
        for servo in self._servos.values():
            servo.off()
        logger.info("All servos turned off")

    def center_all(self):
        """Move all servos to their calibrated center position."""
        for servo in self._servos.values():
            servo.move_to_center()
