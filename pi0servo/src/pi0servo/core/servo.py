"""Single servo control with calibration support.

This module provides the Servo class which handles:
- PWM control via pigpio
- Angle to pulse conversion with calibration
- Per-servo speed limit (0-100)
"""

from dataclasses import dataclass

# Default pulse width constants (microseconds)
PULSE_MIN = 500
PULSE_MAX = 2500
PULSE_CENTER = 1500

# Default angle range
ANGLE_MIN = -90.0
ANGLE_MAX = 90.0
ANGLE_CENTER = 0.0

# Default speed limit (0-100%)
DEFAULT_SPEED_LIMIT = 80


@dataclass
class ServoCalibration:
    """Calibration data for a single servo.

    Attributes:
        pulse_min: Minimum pulse width (μs) corresponding to angle_min
        pulse_max: Maximum pulse width (μs) corresponding to angle_max
        pulse_center: Center pulse width (μs) corresponding to angle_center
        angle_min: Minimum angle in degrees (default -90)
        angle_max: Maximum angle in degrees (default 90)
        angle_center: Center angle in degrees (default 0)
        speed: Speed limit 0-100 (default 80)
    """

    pulse_min: int = PULSE_MIN
    pulse_max: int = PULSE_MAX
    pulse_center: int = PULSE_CENTER
    angle_min: float = ANGLE_MIN
    angle_max: float = ANGLE_MAX
    angle_center: float = ANGLE_CENTER
    speed: int = DEFAULT_SPEED_LIMIT


class Servo:
    """Single servo controller with calibration.

    Provides angle-based control with configurable pulse width calibration.
    Supports per-servo speed limits for velocity-based motion control.
    """

    def __init__(
        self,
        pi,
        pin: int,
        calibration: ServoCalibration | None = None,
    ):
        """Initialize a Servo.

        Args:
            pi: pigpio.pi() instance
            pin: GPIO pin number (0-27)
            calibration: Optional ServoCalibration, uses defaults if None
        """
        self._pi = pi
        self._pin = pin
        self._calibration = calibration or ServoCalibration()

        # Track last known angle (None if unknown)
        self._last_angle: float | None = None

    @property
    def pin(self) -> int:
        """GPIO pin number."""
        return self._pin

    @property
    def calibration(self) -> ServoCalibration:
        """Current calibration data."""
        return self._calibration

    @calibration.setter
    def calibration(self, value: ServoCalibration):
        """Update calibration."""
        self._calibration = value

    @property
    def speed_limit(self) -> int:
        """Per-servo speed limit (0-100)."""
        return self._calibration.speed

    @speed_limit.setter
    def speed_limit(self, value: int):
        """Set per-servo speed limit (clamped to 0-100)."""
        self._calibration.speed = max(0, min(100, value))

    @property
    def last_angle(self) -> float | None:
        """Last known angle, or None if not set."""
        return self._last_angle

    def angle_to_pulse(self, angle: float) -> int:
        """Convert angle in degrees to pulse width in microseconds.

        Uses linear interpolation based on calibration.

        Args:
            angle: Angle in degrees (clamped to min/max)

        Returns:
            Pulse width in microseconds
        """
        cal = self._calibration

        # Clamp angle to valid range
        angle = max(cal.angle_min, min(cal.angle_max, angle))

        # Linear interpolation with division-by-zero guards
        if angle >= cal.angle_center:
            # Upper half: center to max
            divisor = cal.angle_max - cal.angle_center
            if divisor == 0:
                # Degenerate case: center equals max
                pulse = cal.pulse_center
            else:
                t = (angle - cal.angle_center) / divisor
                pulse = cal.pulse_center + t * (cal.pulse_max - cal.pulse_center)
        else:
            # Lower half: min to center
            divisor = cal.angle_center - cal.angle_min
            if divisor == 0:
                # Degenerate case: center equals min
                pulse = cal.pulse_center
            else:
                t = (angle - cal.angle_min) / divisor
                pulse = cal.pulse_min + t * (cal.pulse_center - cal.pulse_min)

        return int(pulse)

    def pulse_to_angle(self, pulse: int) -> float:
        """Convert pulse width in microseconds to angle in degrees.

        Args:
            pulse: Pulse width in microseconds

        Returns:
            Angle in degrees
        """
        cal = self._calibration

        # Clamp pulse to valid range
        pulse = max(cal.pulse_min, min(cal.pulse_max, pulse))

        if pulse >= cal.pulse_center:
            # Upper half
            divisor = cal.pulse_max - cal.pulse_center
            if divisor == 0:
                angle = cal.angle_center
            else:
                t = (pulse - cal.pulse_center) / divisor
                angle = cal.angle_center + t * (cal.angle_max - cal.angle_center)
        else:
            # Lower half
            divisor = cal.pulse_center - cal.pulse_min
            if divisor == 0:
                angle = cal.angle_center
            else:
                t = (pulse - cal.pulse_min) / divisor
                angle = cal.angle_min + t * (cal.angle_center - cal.angle_min)

        return angle

    def get_pulse(self) -> int:
        """Get current pulse width from hardware.

        Returns:
            Current pulse width in microseconds, or 0 if off
        """
        return self._pi.get_servo_pulsewidth(self._pin)

    def get_angle(self) -> float | None:
        """Get current angle if servo is active.

        Returns:
            Current angle in degrees, or None if servo is off
        """
        pulse = self.get_pulse()
        if pulse == 0:
            return None
        return self.pulse_to_angle(pulse)

    def set_pulse(self, pulse: int):
        """Set servo to specific pulse width.

        Args:
            pulse: Pulse width in microseconds (0 to turn off, 500-2500 typical)
        """
        self._pi.set_servo_pulsewidth(self._pin, pulse)
        if pulse > 0:
            self._last_angle = self.pulse_to_angle(pulse)

    def set_angle(self, angle: float):
        """Set servo to specific angle.

        Args:
            angle: Angle in degrees (will be calibrated to pulse)
        """
        pulse = self.angle_to_pulse(angle)
        self.set_pulse(pulse)
        self._last_angle = angle

    def move_to_center(self):
        """Move servo to calibrated center position."""
        self.set_angle(self._calibration.angle_center)

    def move_to_min(self):
        """Move servo to calibrated minimum position."""
        self.set_angle(self._calibration.angle_min)

    def move_to_max(self):
        """Move servo to calibrated maximum position."""
        self.set_angle(self._calibration.angle_max)

    def off(self):
        """Turn off servo PWM signal."""
        self._pi.set_servo_pulsewidth(self._pin, 0)
