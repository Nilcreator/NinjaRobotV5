"""Unit tests for the I2CBus thread-safe wrapper.

Tests cover:
- Basic read/write operations (byte, word, block)
- Big-endian word byte-swap correctness
- Retry on transient failure with exponential backoff
- Bus recovery after persistent failure
- Close guard (safe to call multiple times)
- Thread safety (concurrent reads from multiple threads)
- I2CError raised on unrecoverable failure
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

# Import I2CBus and I2CError from the package
from pi0vl53l0x.core.i2c import I2CBus, I2CError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_pi():
    """Create a mock pigpio.pi instance with standard I2C methods."""
    pi = MagicMock()
    pi.i2c_open.return_value = 42  # Fake handle
    pi.i2c_close.return_value = 0
    pi.i2c_read_byte_data.return_value = 0xAB
    pi.i2c_write_byte_data.return_value = 0
    pi.i2c_read_word_data.return_value = 0x1234  # LE: 0x34 0x12
    pi.i2c_write_word_data.return_value = 0
    pi.i2c_read_i2c_block_data.return_value = (6, bytearray([1, 2, 3, 4, 5, 6]))
    pi.i2c_write_i2c_block_data.return_value = 0
    return pi


@pytest.fixture
def bus(mock_pi):
    """Create an I2CBus instance with the mocked pigpio."""
    return I2CBus(mock_pi, bus=1, address=0x29, max_retries=3)


# ---------------------------------------------------------------------------
# Construction & Handle
# ---------------------------------------------------------------------------


class TestI2CBusInit:
    """Tests for I2CBus initialization."""

    def test_opens_handle_on_init(self, mock_pi, bus):
        """I2C handle should be opened during construction."""
        mock_pi.i2c_open.assert_called_once_with(1, 0x29)

    def test_raises_on_failed_open(self, mock_pi):
        """Should raise I2CError if i2c_open fails."""
        mock_pi.i2c_open.side_effect = Exception("daemon not running")
        with pytest.raises(I2CError, match="Failed to open I2C"):
            I2CBus(mock_pi)

    def test_raises_on_negative_handle(self, mock_pi):
        """Should raise I2CError if pigpio returns a negative handle."""
        mock_pi.i2c_open.return_value = -1
        with pytest.raises(I2CError, match="pigpio returned error"):
            I2CBus(mock_pi)


# ---------------------------------------------------------------------------
# Basic Read/Write Operations
# ---------------------------------------------------------------------------


class TestReadWrite:
    """Tests for basic I2C read and write operations."""

    def test_read_byte(self, bus, mock_pi):
        """read_byte should return the value from pigpio."""
        result = bus.read_byte(0xC0)
        assert result == 0xAB
        mock_pi.i2c_read_byte_data.assert_called_once_with(42, 0xC0)

    def test_write_byte(self, bus, mock_pi):
        """write_byte should pass register and value to pigpio."""
        bus.write_byte(0x00, 0x01)
        mock_pi.i2c_write_byte_data.assert_called_once_with(42, 0x00, 0x01)

    def test_read_block(self, bus, mock_pi):
        """read_block should return a list of byte values."""
        result = bus.read_block(0xB0, 6)
        assert result == [1, 2, 3, 4, 5, 6]
        mock_pi.i2c_read_i2c_block_data.assert_called_once_with(42, 0xB0, 6)

    def test_write_block(self, bus, mock_pi):
        """write_block should pass data list to pigpio."""
        data = [0x01, 0x02, 0x03]
        bus.write_block(0xB0, data)
        mock_pi.i2c_write_i2c_block_data.assert_called_once_with(
            42, 0xB0, [0x01, 0x02, 0x03]
        )


# ---------------------------------------------------------------------------
# Big-Endian Word Byte-Swap
# ---------------------------------------------------------------------------


class TestBigEndianSwap:
    """Tests for big-endian word read/write with byte swap."""

    def test_read_word_swaps_bytes(self, bus, mock_pi):
        """read_word_big_endian should swap bytes from LE to BE.

        pigpio returns 0x1234 (LE: low=0x34, high=0x12).
        After swap: (0x34 << 8) | 0x12 = 0x3412.
        """
        mock_pi.i2c_read_word_data.return_value = 0x1234
        result = bus.read_word_big_endian(0x14)
        assert result == 0x3412

    def test_read_word_identity_on_symmetric(self, bus, mock_pi):
        """Symmetric values (e.g., 0xAAAA) should be unchanged."""
        mock_pi.i2c_read_word_data.return_value = 0xAAAA
        result = bus.read_word_big_endian(0x14)
        assert result == 0xAAAA

    def test_write_word_swaps_bytes(self, bus, mock_pi):
        """write_word_big_endian should swap BE value to LE for pigpio.

        Writing 0xABCD: pigpio receives (0xCD << 8) | 0xAB = 0xCDAB.
        """
        bus.write_word_big_endian(0x44, 0xABCD)
        mock_pi.i2c_write_word_data.assert_called_once_with(42, 0x44, 0xCDAB)

    def test_roundtrip_word(self, bus, mock_pi):
        """Writing then reading the same value should produce identity."""
        # Write 0x1234 (BE) → pigpio gets 0x3412 (LE)
        bus.write_word_big_endian(0x50, 0x1234)
        written_le = mock_pi.i2c_write_word_data.call_args[0][2]
        # Simulate reading back the same LE value
        mock_pi.i2c_read_word_data.return_value = written_le
        result = bus.read_word_big_endian(0x50)
        assert result == 0x1234


# ---------------------------------------------------------------------------
# Retry Logic
# ---------------------------------------------------------------------------


class TestRetry:
    """Tests for retry with exponential backoff."""

    def test_retries_on_transient_failure(self, bus, mock_pi):
        """Should retry and succeed if a later attempt works."""
        mock_pi.i2c_read_byte_data.side_effect = [
            Exception("glitch"),
            Exception("glitch"),
            0x42,  # Third attempt succeeds
        ]
        result = bus.read_byte(0xC0)
        assert result == 0x42
        assert mock_pi.i2c_read_byte_data.call_count == 3

    def test_backoff_timing(self, bus, mock_pi):
        """Verify that retry delays follow the backoff schedule."""
        mock_pi.i2c_read_byte_data.side_effect = [
            Exception("fail1"),
            Exception("fail2"),
            0xFF,
        ]
        with patch("pi0vl53l0x.core.i2c.time.sleep") as mock_sleep:
            bus.read_byte(0xC0)
            # First retry: 10ms, second retry: 20ms
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(0.010)
            mock_sleep.assert_any_call(0.020)


# ---------------------------------------------------------------------------
# Bus Recovery
# ---------------------------------------------------------------------------


class TestBusRecovery:
    """Tests for bus recovery after persistent failure."""

    def test_recovery_on_all_retries_exhausted(self, bus, mock_pi):
        """Should attempt bus recovery after all retries fail."""
        # All 3 retries fail, then recovery attempt succeeds
        mock_pi.i2c_read_byte_data.side_effect = [
            Exception("fail"),
            Exception("fail"),
            Exception("fail"),
            0x77,  # Post-recovery attempt
        ]
        mock_pi.i2c_open.return_value = 99  # New handle from recovery

        result = bus.read_byte(0xC0)
        assert result == 0x77
        # Should have closed the old handle and opened a new one
        assert mock_pi.i2c_close.called
        assert mock_pi.i2c_open.call_count == 2  # Initial + recovery

    def test_raises_if_recovery_also_fails(self, bus, mock_pi):
        """Should raise I2CError if both retries and recovery fail."""
        mock_pi.i2c_read_byte_data.side_effect = Exception("permanent failure")
        mock_pi.i2c_open.side_effect = [42, Exception("daemon dead")]

        with pytest.raises(I2CError, match="failed after 3 retries"):
            bus.read_byte(0xC0)


# ---------------------------------------------------------------------------
# Close Guard
# ---------------------------------------------------------------------------


class TestClose:
    """Tests for close behavior."""

    def test_close_releases_handle(self, bus, mock_pi):
        """close() should call pigpio i2c_close."""
        bus.close()
        mock_pi.i2c_close.assert_called_once_with(42)
        assert bus.is_closed is True

    def test_double_close_is_safe(self, bus, mock_pi):
        """Calling close() twice should not raise."""
        bus.close()
        bus.close()
        # i2c_close should only be called once
        mock_pi.i2c_close.assert_called_once()

    def test_is_closed_property(self, bus):
        """is_closed should reflect the close state."""
        assert bus.is_closed is False
        bus.close()
        assert bus.is_closed is True


# ---------------------------------------------------------------------------
# Thread Safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    """Tests for concurrent thread safety."""

    def test_concurrent_reads_are_serialized(self, bus, mock_pi):
        """Multiple threads reading simultaneously should not corrupt data.

        We verify this by making read_byte_data take some time and
        checking that all results are correct (no interleaving).
        """
        call_count = 0
        lock = threading.Lock()

        def slow_read(handle, register):
            nonlocal call_count
            with lock:
                call_count += 1
            time.sleep(0.001)  # Simulate I2C bus time
            return register  # Return register as value for verification

        mock_pi.i2c_read_byte_data.side_effect = slow_read

        results = {}
        errors = []

        def reader(thread_id, reg):
            try:
                val = bus.read_byte(reg)
                results[thread_id] = val
            except Exception as exc:
                errors.append(exc)

        threads = []
        for i in range(10):
            t = threading.Thread(target=reader, args=(i, i + 0x10))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 10
        # Each thread should get its own register value back
        for thread_id, value in results.items():
            assert value == thread_id + 0x10

    def test_concurrent_read_write_no_crash(self, bus, mock_pi):
        """Mix of reads and writes from multiple threads should not crash."""
        errors = []

        def writer(n):
            try:
                for _ in range(20):
                    bus.write_byte(0x00, n)
            except Exception as exc:
                errors.append(exc)

        def reader():
            try:
                for _ in range(20):
                    bus.read_byte(0xC0)
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=writer, args=(1,)),
            threading.Thread(target=writer, args=(2,)),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0, f"Thread errors: {errors}"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for unusual inputs and edge conditions."""

    def test_read_block_empty_bytearray(self, bus, mock_pi):
        """Should return empty list if pigpio returns non-bytearray."""
        mock_pi.i2c_read_i2c_block_data.return_value = (0, b"")
        result = bus.read_block(0xB0, 0)
        assert result == []

    def test_custom_max_retries(self, mock_pi):
        """Should respect custom max_retries value."""
        b = I2CBus(mock_pi, max_retries=5)
        mock_pi.i2c_read_byte_data.side_effect = [
            Exception("e1"),
            Exception("e2"),
            Exception("e3"),
            Exception("e4"),
            0xDD,  # Fifth attempt succeeds
        ]
        result = b.read_byte(0xC0)
        assert result == 0xDD
        assert mock_pi.i2c_read_byte_data.call_count == 5
