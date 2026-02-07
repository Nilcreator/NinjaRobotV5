"""Unit tests for parser module."""

import pytest

from pi0servo.parser import (
    ParsedCommand,
    ServoTarget,
    parse_command,
    resolve_special_angle,
)


class TestParseCommand:
    """Test command string parsing."""

    def test_simple_target(self):
        """Parse a simple single target."""
        result = parse_command("20:45")
        assert result.speed_mode == "M"  # Default Medium
        assert len(result.targets) == 1
        assert result.targets[0].pin == 20
        assert result.targets[0].angle == 45.0

    def test_fast_speed_prefix(self):
        """Parse command with Fast speed prefix."""
        result = parse_command("F_20:45")
        assert result.speed_mode == "F"
        assert result.targets[0].angle == 45.0

    def test_slow_speed_prefix(self):
        """Parse command with Slow speed prefix."""
        result = parse_command("S_20:45")
        assert result.speed_mode == "S"

    def test_multiple_targets(self):
        """Parse multiple targets separated by /."""
        result = parse_command("F_20:45/21:-30/22:0")
        assert result.speed_mode == "F"
        assert len(result.targets) == 3
        assert result.targets[0].pin == 20
        assert result.targets[0].angle == 45.0
        assert result.targets[1].pin == 21
        assert result.targets[1].angle == -30.0
        assert result.targets[2].pin == 22
        assert result.targets[2].angle == 0.0

    def test_center_special(self):
        """Parse C (center) special position."""
        result = parse_command("20:C")
        assert result.targets[0].pin == 20
        assert result.targets[0].special == "C"
        assert result.targets[0].angle is None

    def test_min_special(self):
        """Parse M (min) special position."""
        result = parse_command("20:M")
        assert result.targets[0].special == "M"

    def test_max_special(self):
        """Parse X (max) special position."""
        result = parse_command("20:X")
        assert result.targets[0].special == "X"

    def test_negative_angle(self):
        """Parse negative angle values."""
        result = parse_command("20:-45")
        assert result.targets[0].angle == -45.0

    def test_float_angle(self):
        """Parse floating-point angle values."""
        result = parse_command("20:45.5")
        assert result.targets[0].angle == 45.5

    def test_empty_command_raises(self):
        """Empty command should raise ValueError."""
        with pytest.raises(ValueError, match="Empty"):
            parse_command("")

    def test_invalid_format_raises(self):
        """Invalid format should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid target"):
            parse_command("invalid")

    def test_angle_out_of_range_raises(self):
        """Angle outside -90 to 90 should raise ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            parse_command("20:100")

    def test_whitespace_handling(self):
        """Whitespace should be trimmed."""
        result = parse_command("  F_20:45  ")
        assert result.speed_mode == "F"
        assert result.targets[0].angle == 45.0

    def test_per_target_speed(self):
        """Test per-target speed suffixes."""
        cmd = "20:45F/21:30S/22:0M"
        result = parse_command(cmd)
        
        assert len(result.targets) == 3
        assert result.targets[0].pin == 20
        assert result.targets[0].speed == "F"
        assert result.targets[1].pin == 21
        assert result.targets[1].speed == "S"
        assert result.targets[2].pin == 22
        assert result.targets[2].speed == "M"

    def test_mixed_global_and_local_speed(self):
        """Test mixing global speed prefix with local suffixes."""
        cmd = "S_20:45/21:30F"
        result = parse_command(cmd)
        
        assert result.speed_mode == "S"
        assert result.targets[0].pin == 20
        assert result.targets[0].speed is None  # Inherits global
        assert result.targets[1].pin == 21
        assert result.targets[1].speed == "F"  # Overrides

    def test_special_with_speed(self):
        """Test special positions with speed suffix."""
        cmd = "20:CS/21:MF"
        result = parse_command(cmd)
        
        assert result.targets[0].special == "C"
        assert result.targets[0].speed == "S"
        assert result.targets[1].special == "M"
        assert result.targets[1].speed == "F"

    def test_invalid_speed_char_raises(self):
        """Test that invalid speed characters are rejected."""
        # This is actually handled by regex not matching, leading to invalid format error
        with pytest.raises(ValueError):
            parse_command("20:45X")  # X is not a speed


class TestServoTarget:
    """Test ServoTarget dataclass."""

    def test_with_angle(self):
        """Create target with angle."""
        target = ServoTarget(pin=20, angle=45.0)
        assert target.pin == 20
        assert target.angle == 45.0
        assert target.special is None

    def test_with_special(self):
        """Create target with special position."""
        target = ServoTarget(pin=20, special="C")
        assert target.special == "C"

    def test_with_speed(self):
        """Test initialization with speed."""
        t = ServoTarget(20, angle=45.0, speed="F")
        assert t.speed == "F"
    
    def test_invalid_speed_raises(self):
        """Test that invalid speed raises ValueError."""
        with pytest.raises(ValueError):
            ServoTarget(20, angle=45.0, speed="X")

    def test_invalid_no_value_raises(self):
        """Target without angle or special should raise ValueError."""
        with pytest.raises(ValueError, match="Either angle or special"):
            ServoTarget(pin=20)

    def test_invalid_special_raises(self):
        """Invalid special code should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid special"):
            ServoTarget(pin=20, special="Z")


class TestResolveSpecialAngle:
    """Test special position resolution."""

    def test_center_default(self):
        """C should default to 0°."""
        assert resolve_special_angle("C") == 0.0

    def test_min_default(self):
        """M should default to -90°."""
        assert resolve_special_angle("M") == -90.0

    def test_max_default(self):
        """X should default to 90°."""
        assert resolve_special_angle("X") == 90.0

    def test_with_calibration(self):
        """Use calibration values when provided."""
        calib = {"angle_center": 5.0, "angle_min": -85.0, "angle_max": 85.0}
        assert resolve_special_angle("C", calib) == 5.0
        assert resolve_special_angle("M", calib) == -85.0
        assert resolve_special_angle("X", calib) == 85.0
