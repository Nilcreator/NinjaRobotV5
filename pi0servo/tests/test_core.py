"""Unit tests for core module."""

import threading
import time

import pytest

from pi0servo.core import (
    PULSE_CENTER,
    PULSE_MAX,
    PULSE_MIN,
    Servo,
    ServoCalibration,
    ServoGroup,
)


class TestServoCalibration:
    """Test ServoCalibration dataclass."""

    def test_defaults(self):
        """Default calibration values (safe - all center)."""
        cal = ServoCalibration()
        # Safe defaults: all pulses set to center to prevent unexpected movement
        assert cal.pulse_min == 1500
        assert cal.pulse_max == 1500
        assert cal.pulse_center == 1500
        assert cal.angle_min == -90.0
        assert cal.angle_max == 90.0
        assert cal.angle_center == 0.0
        assert cal.speed == 80

    def test_custom_values(self):
        """Custom calibration values."""
        cal = ServoCalibration(
            pulse_min=600,
            pulse_max=2400,
            pulse_center=1500,
            speed=100,
        )
        assert cal.pulse_min == 600
        assert cal.speed == 100


class TestServo:
    """Test Servo class."""

    def test_init_default_calibration(self, mock_pigpio):
        """Servo initializes with default calibration."""
        servo = Servo(mock_pigpio, pin=20)
        assert servo.pin == 20
        assert servo.calibration.pulse_min == PULSE_MIN
        assert servo.speed_limit == 80

    def test_init_custom_calibration(self, mock_pigpio):
        """Servo accepts custom calibration."""
        cal = ServoCalibration(speed=100)
        servo = Servo(mock_pigpio, pin=20, calibration=cal)
        assert servo.speed_limit == 100

    def test_speed_limit_clamped(self, mock_pigpio):
        """Speed limit is clamped to 0-100."""
        servo = Servo(mock_pigpio, pin=20)
        servo.speed_limit = 150
        assert servo.speed_limit == 100
        servo.speed_limit = -10
        assert servo.speed_limit == 0

    def test_angle_to_pulse_center(self, mock_pigpio):
        """0° maps to center pulse."""
        servo = Servo(mock_pigpio, pin=20)
        assert servo.angle_to_pulse(0.0) == PULSE_CENTER

    def test_angle_to_pulse_min(self, mock_pigpio):
        """-90° maps to min pulse with proper calibration."""
        cal = ServoCalibration(pulse_min=500, pulse_center=1500, pulse_max=2500)
        servo = Servo(mock_pigpio, pin=20, calibration=cal)
        assert servo.angle_to_pulse(-90.0) == 500

    def test_angle_to_pulse_max(self, mock_pigpio):
        """90° maps to max pulse with proper calibration."""
        cal = ServoCalibration(pulse_min=500, pulse_center=1500, pulse_max=2500)
        servo = Servo(mock_pigpio, pin=20, calibration=cal)
        assert servo.angle_to_pulse(90.0) == 2500

    def test_angle_to_pulse_interpolation(self, mock_pigpio):
        """Intermediate angles interpolate correctly with proper calibration."""
        # Use explicit calibration (not defaults, which are now all-center)
        cal = ServoCalibration(pulse_min=500, pulse_center=1500, pulse_max=2500)
        servo = Servo(mock_pigpio, pin=20, calibration=cal)
        # 45° is halfway between center (0) and max (90)
        pulse = servo.angle_to_pulse(45.0)
        expected = 1500 + (2500 - 1500) / 2  # 2000
        assert pulse == int(expected)

    def test_pulse_to_angle_roundtrip(self, mock_pigpio):
        """Angle -> pulse -> angle roundtrip is consistent with proper calibration."""
        cal = ServoCalibration(pulse_min=500, pulse_center=1500, pulse_max=2500)
        servo = Servo(mock_pigpio, pin=20, calibration=cal)
        for angle in [-90, -45, 0, 45, 90]:
            pulse = servo.angle_to_pulse(angle)
            recovered = servo.pulse_to_angle(pulse)
            assert abs(recovered - angle) < 0.1

    def test_set_angle_calls_pigpio(self, mock_pigpio):
        """set_angle calls pigpio with correct pulse."""
        servo = Servo(mock_pigpio, pin=20)
        servo.set_angle(45.0)
        mock_pigpio.set_servo_pulsewidth.assert_called_once()
        call_args = mock_pigpio.set_servo_pulsewidth.call_args
        assert call_args[0][0] == 20  # pin
        assert call_args[0][1] == servo.angle_to_pulse(45.0)  # pulse

    def test_off_sets_zero_pulse(self, mock_pigpio):
        """off() sets pulse width to 0."""
        servo = Servo(mock_pigpio, pin=20)
        servo.off()
        mock_pigpio.set_servo_pulsewidth.assert_called_with(20, 0)

    def test_get_pulse_returns_zero_on_pigpio_error(self, mock_pigpio):
        """get_pulse returns 0 when pigpio raises exception (e.g., after reboot)."""
        mock_pigpio.get_servo_pulsewidth.side_effect = Exception("GPIO is not in use for servo pulses")
        servo = Servo(mock_pigpio, pin=20)
        assert servo.get_pulse() == 0

    def test_get_angle_returns_none_on_uninitialized_gpio(self, mock_pigpio):
        """get_angle returns None when GPIO is not initialized."""
        mock_pigpio.get_servo_pulsewidth.side_effect = Exception("GPIO is not in use")
        servo = Servo(mock_pigpio, pin=20)
        assert servo.get_angle() is None


class TestServoGroup:
    """Test ServoGroup class."""

    @pytest.fixture
    def mock_pi(self, mock_pigpio):
        """Return the mock pigpio instance."""
        return mock_pigpio

    @pytest.fixture
    def group(self, mock_pi):
        """Create a ServoGroup with 4 servos."""
        return ServoGroup(mock_pi, pins=[20, 21, 22, 23])

    def test_init_creates_servos(self, group):
        """ServoGroup creates Servo instances for each pin."""
        assert len(group.servos) == 4
        assert 20 in group.servos
        assert 21 in group.servos

    def test_get_servo(self, group):
        """get_servo returns correct Servo."""
        servo = group.get_servo(20)
        assert servo is not None
        assert servo.pin == 20

    def test_get_servo_invalid_pin(self, group):
        """get_servo returns None for unknown pin."""
        assert group.get_servo(99) is None

    def test_abort_sets_event(self, group):
        """abort() sets the abort event."""
        group.abort()
        assert group._abort_event.is_set()

    def test_abortable_sleep_interrupted(self, group):
        """Abortable sleep can be interrupted."""
        def abort_after_delay():
            time.sleep(0.01)
            group.abort()

        thread = threading.Thread(target=abort_after_delay)
        thread.start()

        start = time.time()
        result = group._abortable_sleep(1.0)  # 1 second sleep
        elapsed = time.time() - start

        thread.join()
        assert result is False  # Was aborted
        assert elapsed < 0.5  # Didn't wait full second

    def test_off_turns_off_all_servos(self, group, mock_pi):
        """off() turns off all servos."""
        group.off()
        # Should have been called for each servo
        assert mock_pi.set_servo_pulsewidth.call_count >= 4

    def test_center_all(self, group, mock_pi):
        """center_all() moves all servos to center."""
        group.center_all()
        assert mock_pi.set_servo_pulsewidth.call_count >= 4


class TestServoGroupMovement:
    """Test ServoGroup movement functions."""

    @pytest.fixture
    def mock_pi(self, mock_pigpio):
        return mock_pigpio

    @pytest.fixture
    def group(self, mock_pi):
        g = ServoGroup(mock_pi, pins=[20, 21])
        # Set initial positions
        for servo in g.servos.values():
            servo._last_angle = 0.0
        return g

    def test_move_all_sync_completes(self, group):
        """move_all_sync returns True when completed."""
        result = group.move_all_sync([45.0, -30.0], speed_mode="F")
        assert result is True

    def test_move_all_sync_skip_none(self, group):
        """None targets are skipped."""
        result = group.move_all_sync([45.0, None], speed_mode="F")
        assert result is True

    def test_execute_command(self, group):
        """execute_command parses and executes."""
        result = group.execute_command("F_20:45/21:-30")
        assert result is True

    def test_actuator_interface_execute(self, group):
        """Actuator interface execute() returns dict."""
        result = group.execute("F_20:45")
        assert "success" in result
        assert "message" in result
        assert result["success"] is True
