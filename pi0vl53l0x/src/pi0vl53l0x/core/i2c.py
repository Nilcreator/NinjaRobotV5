"""Thread-safe I2C bus wrapper with automatic retry and bus recovery.

This module wraps pigpio I2C operations with:
- Thread safety via threading.Lock (required because DistanceMonitor
  and main thread may access I2C concurrently)
- Automatic retry with exponential backoff (10ms → 20ms → 50ms)
- Bus recovery on persistent failure (close + reopen handle)
- Big-endian word handling (VL53L0X uses big-endian, pigpio uses little)
- Clear diagnostic error messages via I2CError

All I2C operations in the pi0vl53l0x library go through this class.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pigpio

logger = logging.getLogger(__name__)


class I2CError(Exception):
    """Raised when I2C communication fails after all retries."""

    pass


class I2CBus:
    """Resilient, thread-safe I2C bus wrapper with automatic retry.

    All read/write operations are serialized via a threading.Lock to
    prevent state corruption when accessed from multiple threads.

    On failure, operations:
    1. Retry up to max_retries times with exponential backoff
    2. On persistent failure, attempt bus recovery (close + reopen)
    3. Raise I2CError with a clear diagnostic message

    Args:
        pi: A connected pigpio.pi instance.
        bus: I2C bus number (default: 1 for Raspberry Pi).
        address: 7-bit I2C device address (default: 0x29 for VL53L0X).
        max_retries: Maximum number of retry attempts per operation.
    """

    # Backoff delays in seconds for each retry attempt
    _BACKOFF_DELAYS = (0.010, 0.020, 0.050, 0.100, 0.200)

    def __init__(
        self,
        pi: "pigpio.pi",
        bus: int = 1,
        address: int = 0x29,
        max_retries: int = 3,
    ) -> None:
        self._pi = pi
        self._bus = bus
        self._address = address
        self._max_retries = max_retries
        self._lock = threading.Lock()
        self._handle: int | None = None
        self._closed = False

        # Open the I2C handle immediately
        self._handle = self._open_handle()
        logger.debug(
            "I2CBus opened: bus=%d, address=0x%02X, handle=%d",
            self._bus,
            self._address,
            self._handle,
        )

    def _open_handle(self) -> int:
        """Open a new I2C handle via pigpio.

        Returns:
            The integer handle for subsequent I2C operations.

        Raises:
            I2CError: If the handle cannot be opened.
        """
        try:
            handle = self._pi.i2c_open(self._bus, self._address)
        except Exception as exc:
            raise I2CError(
                f"Failed to open I2C bus={self._bus}, "
                f"address=0x{self._address:02X}: {exc}"
            ) from exc

        if handle < 0:
            raise I2CError(
                f"pigpio returned error {handle} opening I2C "
                f"bus={self._bus}, address=0x{self._address:02X}"
            )
        return handle

    def _recover_bus(self) -> None:
        """Attempt bus recovery by closing and reopening the I2C handle.

        Called automatically after all retries are exhausted.
        """
        logger.warning("Attempting I2C bus recovery (close + reopen)...")
        try:
            if self._handle is not None:
                self._pi.i2c_close(self._handle)
        except Exception:
            pass  # Best-effort close

        try:
            self._handle = self._open_handle()
            logger.info("I2C bus recovery successful, new handle=%d", self._handle)
        except I2CError:
            logger.error("I2C bus recovery FAILED")
            raise

    def _retry_operation(self, operation_name: str, func: "callable") -> Any:
        """Execute an I2C operation with retry and exponential backoff.

        The lock MUST be held by the caller before calling this method.

        Args:
            operation_name: Human-readable name for error messages.
            func: Callable that performs the pigpio I2C operation.

        Returns:
            The return value of func() on success.

        Raises:
            I2CError: If all retries are exhausted and bus recovery fails.
        """
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                result = func()
                # pigpio returns negative values on error
                if isinstance(result, int) and result < 0:
                    raise I2CError(
                        f"{operation_name}: pigpio error code {result}"
                    )
                return result
            except I2CError:
                raise  # Don't retry on our own errors with negative codes
            except Exception as exc:
                last_error = exc
                delay = self._BACKOFF_DELAYS[
                    min(attempt, len(self._BACKOFF_DELAYS) - 1)
                ]
                logger.debug(
                    "%s failed (attempt %d/%d): %s — retrying in %.0fms",
                    operation_name,
                    attempt + 1,
                    self._max_retries,
                    exc,
                    delay * 1000,
                )
                time.sleep(delay)

        # All retries exhausted — try bus recovery
        logger.error(
            "%s failed after %d retries, attempting bus recovery",
            operation_name,
            self._max_retries,
        )
        try:
            self._recover_bus()
            # One final attempt after recovery
            return func()
        except Exception as exc:
            raise I2CError(
                f"{operation_name} failed after {self._max_retries} retries "
                f"and bus recovery: {last_error}"
            ) from exc

    # ------------------------------------------------------------------
    # Public I2C Operations (all acquire _lock)
    # ------------------------------------------------------------------

    def read_byte(self, register: int) -> int:
        """Read a single byte from a register.

        Args:
            register: The register address to read from.

        Returns:
            The byte value (0-255).

        Raises:
            I2CError: If the read fails after retries.
        """
        with self._lock:
            result = self._retry_operation(
                f"read_byte(0x{register:02X})",
                lambda: self._pi.i2c_read_byte_data(self._handle, register),
            )
            return int(result)

    def write_byte(self, register: int, value: int) -> None:
        """Write a single byte to a register.

        Args:
            register: The register address to write to.
            value: The byte value to write (0-255).

        Raises:
            I2CError: If the write fails after retries.
        """
        with self._lock:
            self._retry_operation(
                f"write_byte(0x{register:02X}, 0x{value:02X})",
                lambda: self._pi.i2c_write_byte_data(
                    self._handle, register, value
                ),
            )

    def read_word_big_endian(self, register: int) -> int:
        """Read a 16-bit word from a register in big-endian format.

        pigpio reads in little-endian, but VL53L0X uses big-endian.
        This method handles the byte-swap automatically.

        Args:
            register: The register address to read from.

        Returns:
            The 16-bit value in correct (big-endian) byte order.

        Raises:
            I2CError: If the read fails after retries.
        """
        with self._lock:
            raw = self._retry_operation(
                f"read_word(0x{register:02X})",
                lambda: self._pi.i2c_read_word_data(self._handle, register),
            )
            # Swap bytes: pigpio returns LE, sensor expects BE
            return ((raw & 0xFF) << 8) | (raw >> 8)

    def write_word_big_endian(self, register: int, value: int) -> None:
        """Write a 16-bit word to a register in big-endian format.

        Handles the byte-swap from big-endian (sensor) to
        little-endian (pigpio) automatically.

        Args:
            register: The register address to write to.
            value: The 16-bit value in big-endian byte order.

        Raises:
            I2CError: If the write fails after retries.
        """
        # Swap bytes: sensor is BE, pigpio expects LE
        swapped = ((value & 0xFF) << 8) | (value >> 8)
        with self._lock:
            self._retry_operation(
                f"write_word(0x{register:02X}, 0x{value:04X})",
                lambda: self._pi.i2c_write_word_data(
                    self._handle, register, swapped
                ),
            )

    def read_block(self, register: int, count: int) -> list[int]:
        """Read a block of bytes from a register.

        Args:
            register: The starting register address.
            count: Number of bytes to read.

        Returns:
            List of byte values.

        Raises:
            I2CError: If the read fails after retries.
        """
        with self._lock:
            result = self._retry_operation(
                f"read_block(0x{register:02X}, {count})",
                lambda: self._pi.i2c_read_i2c_block_data(
                    self._handle, register, count
                ),
            )
            # pigpio returns (count, bytearray)
            _, data = result
            if isinstance(data, bytearray):
                return list(data)
            return []

    def write_block(self, register: int, data: list[int]) -> None:
        """Write a block of bytes to a register.

        Args:
            register: The starting register address.
            data: List of byte values to write.

        Raises:
            I2CError: If the write fails after retries.
        """
        with self._lock:
            self._retry_operation(
                f"write_block(0x{register:02X}, {len(data)} bytes)",
                lambda: self._pi.i2c_write_i2c_block_data(
                    self._handle, register, data
                ),
            )

    def close(self) -> None:
        """Close the I2C handle.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._handle is not None:
                try:
                    self._pi.i2c_close(self._handle)
                    logger.debug("I2C handle %d closed", self._handle)
                except Exception as exc:
                    logger.warning("Error closing I2C handle: %s", exc)
                finally:
                    self._handle = None

    @property
    def is_closed(self) -> bool:
        """Whether the I2C handle has been closed."""
        return self._closed
