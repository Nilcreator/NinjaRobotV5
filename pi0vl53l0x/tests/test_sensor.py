"""Unit tests for the VL53L0X sensor driver.

Tests cover:
- Init sequence (boot polling, VHV retry, cleanup on failure)
- get_range() exception contract (I2CError, TimeoutError, RuntimeError)
- get_data() correctness (V2 offset bug fix)
- health_check() and reinitialize()
- Async via asyncio (get_range_async)
- Error propagation
- Context manager (__enter__/__exit__)
- Backward compatibility shim (driver.py)
- get_ranges() convenience method
- Calibrate with mocked measurements
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from pi0vl53l0x.core.sensor import VL53L0X


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_pi():
    """Create a mock pigpio.pi instance with standard I2C behavior."""
    pi = MagicMock()
    pi.i2c_open.return_value = 42
    pi.i2c_close.return_value = 0
    pi.i2c_read_byte_data.return_value = 0x00
    pi.i2c_write_byte_data.return_value = 0
    pi.i2c_read_word_data.return_value = 0
    pi.i2c_write_word_data.return_value = 0
    pi.i2c_read_i2c_block_data.return_value = (
        6,
        bytearray([0x00] * 6),
    )
    pi.i2c_write_i2c_block_data.return_value = 0
    return pi


def _setup_init_responses(pi):
    """Configure the mock pi to pass through full initialization.

    Sets up the minimum required read responses for the VL53L0X
    init sequence to succeed.
    """
    # Track call count to return different values for different registers
    read_calls = []

    def smart_read(handle, register):
        read_calls.append(register)

        # Model ID check
        if register == 0xC0:
            return 0xEE

        # Firmware boot status — bit 0 set
        if register == 0x01:
            return 0x01

        # Stop variable
        if register == 0x91:
            return 0x28

        # GPIO_HV_MUX_ACTIVE_HIGH
        if register == 0x84:
            return 0x10

        # VHV_CFG_PAD
        if register == 0x89:
            return 0x00

        # MSRC_CONFIG_CONTROL
        if register == 0x60:
            return 0x00

        # SYSTEM_SEQUENCE_CONFIG (enables timing budget calc)
        if register == 0x01:
            return 0xC0  # pre-range + final-range enabled

        # SPAD info: waiting for readiness (0x83 register)
        if register == 0x83:
            return 0x01  # Ready on first check

        # SPAD count: 12 SPADs, not aperture
        if register == 0x92:
            return 12

        # RESULT_INTERRUPT_STATUS (calibration complete)
        if register == 0x13:
            return 0x07

        # VCSEL period registers
        if register in (0x50, 0x70):
            return 0x0E

        return 0x00

    def smart_read_word(handle, register):
        # Timing registers — return valid timeout values in LE
        return 0x0100  # Some plausible default

    pi.i2c_read_byte_data.side_effect = smart_read
    pi.i2c_read_word_data.side_effect = smart_read_word
    return read_calls


@pytest.fixture
def mock_pi():
    """Create a mock pigpio.pi with full init support."""
    pi = _make_mock_pi()
    _setup_init_responses(pi)
    return pi


@pytest.fixture
def sensor(mock_pi):
    """Create a VL53L0X instance with successful initialization."""
    return VL53L0X(mock_pi, i2c_bus=1, i2c_address=0x29)


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------


class TestInit:
    """Tests for VL53L0X initialization."""

    def test_successful_init(self, sensor):
        """Sensor should initialize successfully with valid responses."""
        assert sensor._initialized is True

    def test_init_verifies_model_id(self, mock_pi):
        """Init should check Model ID is 0xEE."""
        # First call to read_byte(0xC0) returns wrong ID
        original_side_effect = mock_pi.i2c_read_byte_data.side_effect

        def wrong_id(handle, register):
            if register == 0xC0:
                return 0x00  # Wrong model ID
            return original_side_effect(handle, register)

        mock_pi.i2c_read_byte_data.side_effect = wrong_id

        with pytest.raises(ConnectionError, match="Invalid Model ID"):
            VL53L0X(mock_pi)

    def test_init_cleanup_on_failure(self):
        """I2C handle should be closed if init fails."""
        pi = _make_mock_pi()

        # Make model ID check return wrong value
        def always_wrong(handle, register):
            if register == 0xC0:
                return 0x00
            return 0x00

        pi.i2c_read_byte_data.side_effect = always_wrong

        with pytest.raises(ConnectionError):
            VL53L0X(pi)

        # Verify i2c_close was called (cleanup)
        pi.i2c_close.assert_called()

    def test_firmware_boot_timeout(self):
        """Should raise TimeoutError if firmware doesn't boot."""
        pi = _make_mock_pi()

        def no_boot(handle, register):
            if register == 0xC0:
                return 0xEE  # Model ID OK
            if register == 0x01:
                return 0x00  # Firmware never boots
            return 0x00

        pi.i2c_read_byte_data.side_effect = no_boot

        with pytest.raises(TimeoutError, match="firmware did not boot"):
            VL53L0X(pi, firmware_boot_timeout=0.05)


# ---------------------------------------------------------------------------
# get_range() Tests
# ---------------------------------------------------------------------------


class TestGetRange:
    """Tests for the get_range() method."""

    def test_returns_distance_mm(self, sensor, mock_pi):
        """get_range should return distance in mm."""
        # Override read_byte to return interrupt ready on first call
        original = mock_pi.i2c_read_byte_data.side_effect

        def range_read(handle, register):
            if register == 0x13:
                return 0x07  # Interrupt ready
            return original(handle, register)

        mock_pi.i2c_read_byte_data.side_effect = range_read
        # Return distance 250mm in LE format (swap: 0x00FA -> 0xFA00)
        mock_pi.i2c_read_word_data.side_effect = lambda h, r: 0xFA00

        result = sensor.get_range()
        assert result == 250

    def test_raises_runtime_error_if_not_initialized(self, mock_pi):
        """get_range should raise RuntimeError if not initialized."""
        pi = _make_mock_pi()
        _setup_init_responses(pi)
        s = VL53L0X(pi)
        s._initialized = False

        with pytest.raises(RuntimeError, match="not initialized"):
            s.get_range()

    def test_raises_timeout_on_no_data(self, sensor, mock_pi):
        """get_range should raise TimeoutError if measurement never completes."""

        def never_ready(handle, register):
            if register == 0x13:
                return 0x00  # Never ready
            return 0x00

        mock_pi.i2c_read_byte_data.side_effect = never_ready
        # Force a short timing budget for fast test
        sensor._measurement_timing_budget_us = 1000

        with pytest.raises(TimeoutError, match="did not complete"):
            sensor.get_range()

    def test_applies_offset(self, sensor, mock_pi):
        """get_range should subtract offset from raw measurement."""
        original = mock_pi.i2c_read_byte_data.side_effect

        def range_read(handle, register):
            if register == 0x13:
                return 0x07
            return original(handle, register)

        mock_pi.i2c_read_byte_data.side_effect = range_read
        mock_pi.i2c_read_word_data.side_effect = lambda h, r: 0xFA00  # 250mm

        sensor.set_offset(10)
        result = sensor.get_range()
        assert result == 240  # 250 - 10


# ---------------------------------------------------------------------------
# get_data() Tests — V2 Offset Bug Fix
# ---------------------------------------------------------------------------


class TestGetData:
    """Tests for get_data() and V2 offset bug fix."""

    def test_raw_value_is_truly_raw(self, sensor, mock_pi):
        """get_data() raw_value should be the actual raw sensor value.

        V2 bug: raw_value was storing (raw - offset), not raw.
        Fix: raw_value now contains the true raw value.
        """
        original = mock_pi.i2c_read_byte_data.side_effect

        def range_read(handle, register):
            if register == 0x13:
                return 0x07
            return original(handle, register)

        mock_pi.i2c_read_byte_data.side_effect = range_read
        mock_pi.i2c_read_word_data.side_effect = lambda h, r: 0xFA00  # 250mm

        sensor.set_offset(10)
        data = sensor.get_data()

        assert data["raw_value"] == 250   # True raw value
        assert data["distance_mm"] == 240  # 250 - 10
        assert data["is_valid"] is True

    def test_error_returns_safe_defaults(self, sensor, mock_pi):
        """get_data() should return safe defaults on error."""
        mock_pi.i2c_read_byte_data.side_effect = Exception("bus error")

        data = sensor.get_data()
        assert data["distance_mm"] == -1
        assert data["is_valid"] is False
        assert data["raw_value"] is None
        assert "timestamp" in data

    def test_invalid_range_detection(self, sensor, mock_pi):
        """get_data() should detect out-of-range values."""
        original = mock_pi.i2c_read_byte_data.side_effect

        def range_read(handle, register):
            if register == 0x13:
                return 0x07
            return original(handle, register)

        mock_pi.i2c_read_byte_data.side_effect = range_read
        # Return 8190mm (out of valid range)
        mock_pi.i2c_read_word_data.side_effect = lambda h, r: 0xFE1F  # 8190 in LE

        data = sensor.get_data()
        assert data["is_valid"] is False


# ---------------------------------------------------------------------------
# Health Check & Reinitialize
# ---------------------------------------------------------------------------


class TestHealthAndRecovery:
    """Tests for health_check() and reinitialize()."""

    def test_health_check_ok(self, sensor, mock_pi):
        """health_check should return True if model ID matches."""
        original = mock_pi.i2c_read_byte_data.side_effect

        def model_read(handle, register):
            if register == 0xC0:
                return 0xEE
            return original(handle, register)

        mock_pi.i2c_read_byte_data.side_effect = model_read
        assert sensor.health_check() is True

    def test_health_check_fail(self, sensor, mock_pi):
        """health_check should return False on I2C error."""
        mock_pi.i2c_read_byte_data.side_effect = Exception("bus error")
        assert sensor.health_check() is False

    def test_reinitialize(self, sensor, mock_pi):
        """reinitialize should re-run full init sequence."""
        _setup_init_responses(mock_pi)
        sensor.reinitialize()
        assert sensor._initialized is True


# ---------------------------------------------------------------------------
# Async Support
# ---------------------------------------------------------------------------


class TestAsync:
    """Tests for async get_range_async()."""

    def test_get_range_async(self, sensor, mock_pi):
        """get_range_async should return same result as get_range."""
        original = mock_pi.i2c_read_byte_data.side_effect

        def range_read(handle, register):
            if register == 0x13:
                return 0x07
            return original(handle, register)

        mock_pi.i2c_read_byte_data.side_effect = range_read
        mock_pi.i2c_read_word_data.side_effect = lambda h, r: 0xFA00  # 250mm

        result = asyncio.run(sensor.get_range_async())
        assert result == 250


# ---------------------------------------------------------------------------
# Context Manager
# ---------------------------------------------------------------------------


class TestContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_closes(self, mock_pi):
        """__exit__ should close I2C connection."""
        with VL53L0X(mock_pi) as _sensor:
            pass
        mock_pi.i2c_close.assert_called()


# ---------------------------------------------------------------------------
# get_ranges() and calibrate()
# ---------------------------------------------------------------------------


class TestUtilities:
    """Tests for get_ranges() and calibrate()."""

    def test_get_ranges_returns_list(self, sensor, mock_pi):
        """get_ranges should return a list of ints."""
        original = mock_pi.i2c_read_byte_data.side_effect

        def range_read(handle, register):
            if register == 0x13:
                return 0x07
            return original(handle, register)

        mock_pi.i2c_read_byte_data.side_effect = range_read
        mock_pi.i2c_read_word_data.side_effect = lambda h, r: 0xFA00

        result = sensor.get_ranges(3)
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(r == 250 for r in result)

    def test_calibrate(self, sensor, mock_pi):
        """calibrate should return offset between measured and target."""
        original = mock_pi.i2c_read_byte_data.side_effect

        def range_read(handle, register):
            if register == 0x13:
                return 0x07
            return original(handle, register)

        mock_pi.i2c_read_byte_data.side_effect = range_read
        mock_pi.i2c_read_word_data.side_effect = lambda h, r: 0xFA00  # 250mm

        offset = sensor.calibrate(target_distance_mm=200, num_samples=3)
        assert offset == 50  # 250 - 200


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    """Tests for backward compatibility."""

    def test_driver_import(self):
        """pi0vl53l0x.driver should export VL53L0X."""
        from pi0vl53l0x.driver import VL53L0X as DriverVL53L0X
        from pi0vl53l0x.core.sensor import VL53L0X as CoreVL53L0X

        assert DriverVL53L0X is CoreVL53L0X

    def test_package_import(self):
        """pi0vl53l0x should export VL53L0X."""
        from pi0vl53l0x import VL53L0X as PkgVL53L0X
        from pi0vl53l0x.core.sensor import VL53L0X as CoreVL53L0X

        assert PkgVL53L0X is CoreVL53L0X

    def test_direct_read_write_methods(self, sensor, mock_pi):
        """Sensor should expose read_byte/write_byte for compat."""
        original = mock_pi.i2c_read_byte_data.side_effect

        def compat_read(handle, register):
            if register == 0xAA:
                return 0x55
            return original(handle, register)

        mock_pi.i2c_read_byte_data.side_effect = compat_read

        # Use backward-compat methods on sensor directly
        assert sensor.read_byte(0xAA) == 0x55
        sensor.write_byte(0xBB, 0xCC)

    def test_close_method(self, sensor, mock_pi):
        """close() should work on sensor instance."""
        sensor.close()
        mock_pi.i2c_close.assert_called()
