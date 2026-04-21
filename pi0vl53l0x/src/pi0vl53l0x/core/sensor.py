"""VL53L0X Time-of-Flight distance sensor driver.

This module implements the full VL53L0X driver with:
- Hardened initialization with firmware boot polling (1.0s timeout)
- Cleanup on init failure (I2C handle released)
- Thread-safe I2C via I2CBus wrapper
- Single-shot ranging with quality validation
- Calibration support with offset management
- Health check and reinitialize for runtime recovery
- Async-ready get_range_async() for future asyncio integration
- Defined exception contract: I2CError, TimeoutError, RuntimeError

Implements the Sensor ABC from ninja_utils.interfaces.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import threading
import time
from typing import TYPE_CHECKING, Any

from pi0vl53l0x.core.i2c import I2CBus, I2CError
from pi0vl53l0x import registers as R

if TYPE_CHECKING:
    import pigpio

logger = logging.getLogger(__name__)


class VL53L0X:
    """VL53L0X distance sensor driver implementing the Sensor interface.

    This driver provides distance measurements using the VL53L0X
    Time-of-Flight laser ranging sensor via I2C communication.

    Thread Safety:
        Individual I2C operations are serialized by I2CBus. Whole ranging
        transactions are also serialized here so callers such as
        DistanceMonitor and Blockly user code cannot interleave the
        VL53L0X register sequence.

    Exception Contract:
        get_range() raises:
        - I2CError: I2C bus failure after retries
        - TimeoutError: Measurement did not complete within timeout
        - RuntimeError: Sensor not initialized

    Args:
        pi: A connected pigpio.pi instance.
        i2c_bus: I2C bus number (default: 1).
        i2c_address: 7-bit I2C address (default: 0x29).
        debug: Enable debug logging (default: False).
        config_file_path: Optional path to config file with offset_mm.
        firmware_boot_timeout: Timeout in seconds for firmware boot
            polling (default: 1.0s).
    """

    # Expected model ID for connection verification
    _MODEL_ID = 0xEE

    def __init__(
        self,
        pi: pigpio.pi,
        i2c_bus: int = 1,
        i2c_address: int = 0x29,
        debug: bool = False,
        config_file_path: Any = None,
        firmware_boot_timeout: float = 1.0,
    ) -> None:
        self._pi = pi
        self._i2c_bus_num = i2c_bus
        self._i2c_address = i2c_address
        self._firmware_boot_timeout = firmware_boot_timeout
        self._initialized = False
        self.offset_mm = 0
        self._stop_variable = 0
        self._measurement_timing_budget_us = 0
        self._measurement_lock = threading.RLock()

        logger.debug(
            "VL53L0X init: bus=%d, address=0x%02X",
            self._i2c_bus_num,
            self._i2c_address,
        )

        # Create the thread-safe I2C bus wrapper
        try:
            self.i2c = I2CBus(
                pi,
                bus=i2c_bus,
                address=i2c_address,
                max_retries=3,
            )
        except I2CError:
            logger.error("Failed to open I2C bus — sensor unavailable")
            raise

        # Load offset from config if provided
        if config_file_path:
            try:
                from pi0vl53l0x.config.config_manager import load_config

                config = load_config(config_file_path)
                if "offset_mm" in config:
                    self.set_offset(config["offset_mm"])
                    logger.debug(
                        "Loaded offset_mm=%d from %s",
                        self.offset_mm,
                        config_file_path,
                    )
            except Exception as exc:
                logger.warning("Could not load config: %s", exc)

        # Initialize the sensor — cleanup on failure
        try:
            self.initialize()
        except Exception:
            logger.error("Initialization failed — closing I2C handle")
            self.i2c.close()
            raise

    def __enter__(self) -> VL53L0X:
        """Context manager entry point."""
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit — closes I2C connection."""
        self.close()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Full sensor initialization sequence.

        Steps:
        1. Verify connection (Model ID = 0xEE)
        2. Software reset
        3. Wait for firmware boot (poll reg 0x01, up to 1.0s)
        4. Set initial register values and read stop_variable
        5. Configure signal rate limit
        6. Get SPAD info and configure SPAD map (with VHV retry)
        7. Configure interrupt GPIO
        8. Set timing budget and run calibrations

        Raises:
            ConnectionError: If sensor not detected or wrong model ID.
            TimeoutError: If firmware does not boot within timeout.
            I2CError: If I2C communication fails.
        """
        # Step 1: Verify connection
        self._check_connection()

        # Step 2: Software reset
        self._reset()

        # Step 3: Wait for firmware boot
        self._wait_for_firmware_boot(self._firmware_boot_timeout)

        # Step 4: Set initial register values
        self._set_i2c_registers_initial_values()

        # Step 5: Configure signal rate limit
        self._configure_signal_rate_limit()

        # Step 6: Setup SPAD configuration
        self._setup_spad_info()

        # Step 7: Configure interrupt GPIO
        self._configure_interrupt_gpio()

        # Step 8: Timing budget and calibrations
        self._set_timing_budget_and_calibrations()

        self._initialized = True
        logger.info("VL53L0X initialized successfully")

    def _check_connection(self) -> None:
        """Verify sensor is connected by reading Model ID.

        Raises:
            ConnectionError: If model ID is not 0xEE.
        """
        try:
            model_id = self.i2c.read_byte(R.IDENTIFICATION_MODEL_ID)
        except I2CError as exc:
            raise ConnectionError(
                f"Failed to connect to VL53L0X: {exc}"
            ) from exc

        if model_id != self._MODEL_ID:
            raise ConnectionError(
                f"Invalid Model ID: 0x{model_id:02X}. Expected 0xEE."
            )
        logger.debug("Model ID verified: 0xEE")

    def _reset(self) -> None:
        """Perform a software reset of the sensor."""
        logger.debug("Resetting VL53L0X...")
        self.i2c.write_byte(R.SOFT_RESET_GO2_SOFT_RESET_N, 0x00)
        time.sleep(0.01)
        self.i2c.write_byte(R.SOFT_RESET_GO2_SOFT_RESET_N, 0x01)
        time.sleep(0.01)
        logger.debug("VL53L0X reset complete")

    def _wait_for_firmware_boot(self, timeout_s: float = 1.0) -> None:
        """Poll register 0x01 until firmware boot is confirmed.

        Default timeout increased from 500ms to 1.0s to handle cold boot.

        Args:
            timeout_s: Maximum wait time in seconds.

        Raises:
            TimeoutError: If firmware does not boot within timeout.
        """
        start = time.time()
        while True:
            try:
                status = self.i2c.read_byte(R.FIRMWARE_BOOT_STATUS)
                if status & 0x01:
                    logger.debug("Firmware boot confirmed")
                    return
            except I2CError:
                pass  # May fail during boot — keep polling

            if time.time() - start > timeout_s:
                raise TimeoutError(
                    f"VL53L0X firmware did not boot within {timeout_s}s"
                )
            time.sleep(0.005)  # 5ms poll interval

    def _set_i2c_registers_initial_values(self) -> None:
        """Set initial I2C register values and read stop_variable.

        This sequence follows the ST reference driver's DataInit step.
        It sets the I2C standard mode, reads the stop variable,
        and configures the I/O 2.8V expander.
        """
        # Set I2C standard mode
        self.i2c.write_byte(R.I2C_STANDARD_MODE, 0x00)

        # Read stop variable from internal register
        self.i2c.write_byte(0x80, 0x01)
        self.i2c.write_byte(0xFF, 0x01)
        self.i2c.write_byte(0x00, 0x00)

        self._stop_variable = self.i2c.read_byte(0x91)

        self.i2c.write_byte(0x00, 0x01)
        self.i2c.write_byte(0xFF, 0x00)
        self.i2c.write_byte(0x80, 0x00)

        # Configure I/O 2.8V expander (recommended: once only)
        try:
            current = self.i2c.read_byte(R.VHV_CFG_PAD_SCL_SDA_EXTSUP_HV)
            self.i2c.write_byte(
                R.VHV_CFG_PAD_SCL_SDA_EXTSUP_HV, current | 0x01
            )
        except (I2CError, Exception):
            pass  # Non-critical — continue init

    def _configure_signal_rate_limit(self) -> None:
        """Configure signal rate limit for MSRC and final range.

        Disables SIGNAL_RATE_MSRC (bit 1) and SIGNAL_RATE_PRE_RANGE
        (bit 4) limit checks. Sets final range signal rate limit to
        0.25 MCPS (= 32 as fixed-point).
        """
        current = self.i2c.read_byte(R.MSRC_CONFIG_CONTROL)
        self.i2c.write_byte(R.MSRC_CONFIG_CONTROL, current | 0x12)

        # Set signal rate limit: 0.25 MCPS * 128 = 32
        self.i2c.write_word_big_endian(
            R.FINAL_RANGE_CFG_MIN_COUNT_RATE_RTN_LIMIT,
            R.SIGNAL_RATE_LIMIT_FIXED,
        )

        # Enable all sequence steps for configuration
        self.i2c.write_byte(R.SYSTEM_SEQUENCE_CONFIG, 0xFF)

    def _get_spad_info(self) -> tuple[int, bool]:
        """Get SPAD count and aperture information.

        Includes retry logic for VHV calibration stability.
        Up to 5 attempts if the SPAD calibration times out.

        Returns:
            Tuple of (spad_count, is_aperture).

        Raises:
            I2CError: If SPAD info cannot be retrieved after retries.
            TimeoutError: If SPAD calibration times out.
        """
        max_retries = 5

        for attempt in range(max_retries):
            try:
                # Set up for SPAD info read
                self.i2c.write_byte(0x80, 0x01)
                self.i2c.write_byte(0xFF, 0x01)
                self.i2c.write_byte(0x00, 0x00)

                self.i2c.write_byte(0xFF, 0x06)
                current_83 = self.i2c.read_byte(0x83)
                self.i2c.write_byte(0x83, current_83 | 0x04)
                self.i2c.write_byte(0xFF, 0x07)
                self.i2c.write_byte(0x81, 0x01)

                self.i2c.write_byte(0x80, 0x01)

                # Trigger SPAD calibration and wait for completion
                self.i2c.write_byte(0x94, 0x6B)
                self.i2c.write_byte(0x83, 0x00)

                start = time.time()
                while self.i2c.read_byte(0x83) == 0x00:
                    if time.time() - start > R.TIMEOUT_LIMIT:
                        raise TimeoutError("Timeout waiting for SPAD info")

                self.i2c.write_byte(0x83, 0x01)

                # Read SPAD count and aperture flag
                tmp = self.i2c.read_byte(0x92)
                count = tmp & R.SPAD_COUNT_MASK
                is_aperture = (tmp & R.SPAD_APERTURE_BIT) != 0

                # Restore registers to defaults
                self.i2c.write_byte(0x81, 0x00)
                self.i2c.write_byte(0xFF, 0x06)
                current_83 = self.i2c.read_byte(0x83)
                self.i2c.write_byte(0x83, current_83 & ~0x04)
                self.i2c.write_byte(0xFF, 0x01)
                self.i2c.write_byte(0x00, 0x01)

                self.i2c.write_byte(0xFF, 0x00)
                self.i2c.write_byte(0x80, 0x00)

                return count, is_aperture

            except Exception as exc:
                logger.warning(
                    "SPAD info retrieval failed (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries,
                    exc,
                )
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.1)  # Brief pause before retry

        # Should not reach here, but satisfy type checker
        raise RuntimeError("SPAD info retrieval failed")  # pragma: no cover

    def _setup_spad_info(self) -> None:
        """Configure SPAD map and default register tuning.

        Reads SPAD info, configures the SPAD enable map,
        then writes the full default register tuning sequence.
        """
        spad_count, spad_is_aperture = self._get_spad_info()

        # Read reference SPAD map (6 bytes)
        ref_spad_map = self.i2c.read_block(R.GLOBAL_CFG_SPAD_ENABLES_REF_0, 6)

        # Configure dynamic SPAD settings
        self.i2c.write_byte(0xFF, 0x01)
        self.i2c.write_byte(R.DYN_SPAD_REF_EN_START_OFFSET, 0x00)
        self.i2c.write_byte(
            R.DYN_SPAD_NUM_REQUESTED_REF_SPAD, R.SPAD_NUM_REQUESTED_REF
        )
        self.i2c.write_byte(0xFF, 0x00)
        self.i2c.write_byte(R.GLOBAL_CFG_REF_EN_START_SELECT, 0xB4)

        first_spad = R.SPAD_START_INDEX_APERTURE if spad_is_aperture else 0
        spads_enabled = 0

        # Enable SPADs based on count and aperture
        for i in range(R.SPAD_TOTAL_COUNT):
            byte_idx = i // R.SPAD_MAP_BITS_PER_BYTE
            bit_idx = i % R.SPAD_MAP_BITS_PER_BYTE
            if i < first_spad or spads_enabled == spad_count:
                ref_spad_map[byte_idx] &= ~(1 << bit_idx)
            elif (ref_spad_map[byte_idx] >> bit_idx) & 0x1:
                spads_enabled += 1

        self.i2c.write_block(R.GLOBAL_CFG_SPAD_ENABLES_REF_0, ref_spad_map)

        # Write default register tuning sequence
        # This long sequence is from the ST reference driver
        self._write_default_tuning()

    def _write_default_tuning(self) -> None:
        """Write the default register tuning sequence.

        This is the ~80 register write sequence from the ST VL53L0X
        reference driver. The registers are written as raw hex addresses
        because they are undocumented internal registers.
        """
        w = self.i2c.write_byte

        # Page 1 SPAD registers
        w(0xFF, 0x01)
        w(0x00, 0x00)
        w(0xFF, 0x00)
        w(0x09, 0x00)
        w(0x10, 0x00)
        w(0x11, 0x00)
        w(0x24, 0x01)
        w(0x25, 0xFF)
        w(0x75, 0x00)

        # Page 1 timing registers
        w(0xFF, 0x01)
        w(0x4E, R.SPAD_NUM_REQUESTED_REF)
        w(0x48, 0x00)
        w(0x30, 0x20)

        # Page 0 range config
        w(0xFF, 0x00)
        w(0x30, 0x09)
        w(0x54, 0x00)
        w(0x31, 0x04)
        w(0x32, 0x03)
        w(0x40, 0x83)
        w(0x46, 0x25)
        w(0x60, 0x00)
        w(0x27, 0x00)
        w(0x50, 0x06)
        w(0x51, 0x00)
        w(0x52, 0x96)
        w(0x56, 0x08)
        w(0x57, 0x30)
        w(0x61, 0x00)
        w(0x62, 0x00)
        w(0x64, 0x00)
        w(0x65, 0x00)
        w(0x66, 0xA0)

        # Page 1 range config
        w(0xFF, 0x01)
        w(0x22, 0x32)
        w(0x47, 0x14)
        w(0x49, 0xFF)
        w(0x4A, 0x00)

        w(0xFF, 0x00)
        w(0x7A, 0x0A)
        w(0x7B, 0x00)
        w(0x78, 0x21)

        # Page 1 internal calibration
        w(0xFF, 0x01)
        w(0x23, 0x34)
        w(0x42, 0x00)
        w(0x44, 0xFF)
        w(0x45, 0x26)
        w(0x46, 0x05)
        w(0x40, 0x40)
        w(0x0E, 0x06)
        w(0x20, 0x1A)
        w(0x43, 0x40)

        w(0xFF, 0x00)
        w(0x34, 0x03)
        w(0x35, 0x44)

        # Page 1 final calibration
        w(0xFF, 0x01)
        w(0x31, 0x04)
        w(0x4B, 0x09)
        w(0x4C, 0x05)
        w(0x4D, 0x04)

        # Page 0 final config
        w(0xFF, 0x00)
        w(0x44, 0x00)
        w(0x45, 0x20)
        w(0x47, 0x08)
        w(0x48, 0x28)
        w(0x67, 0x00)
        w(0x70, 0x04)
        w(0x71, 0x01)
        w(0x72, 0xFE)
        w(0x76, 0x00)
        w(0x77, 0x00)

        w(0xFF, 0x01)
        w(0x0D, 0x01)

        w(0xFF, 0x00)
        w(0x80, 0x01)
        w(0x01, 0xF8)

        w(0xFF, 0x01)
        w(0x8E, 0x01)
        w(0x00, 0x01)
        w(0xFF, 0x00)
        w(0x80, 0x00)

    def _configure_interrupt_gpio(self) -> None:
        """Configure GPIO for measurement-ready interrupts.

        Sets new-sample-ready interrupt mode and clears
        any pending interrupts.
        """
        self.i2c.write_byte(
            R.SYSTEM_INTERRUPT_CONFIG_GPIO, R.GPIO_INTERRUPT_CONFIG
        )

        # Set GPIO polarity to active-low
        current = self.i2c.read_byte(R.GPIO_HV_MUX_ACTIVE_HIGH)
        self.i2c.write_byte(R.GPIO_HV_MUX_ACTIVE_HIGH, current & ~0x10)

        # Clear any pending interrupts
        self.i2c.write_byte(R.SYSTEM_INTERRUPT_CLEAR, 0x01)

    def _set_timing_budget_and_calibrations(self) -> None:
        """Set measurement timing budget and run reference calibrations.

        Reads current timing budget, sets it, then runs VHV and
        phase calibration before restoring the sequence config.
        """
        self._measurement_timing_budget_us = (
            self._get_measurement_timing_budget()
        )
        logger.debug(
            "Timing budget: %d µs", self._measurement_timing_budget_us
        )
        self._set_measurement_timing_budget(
            self._measurement_timing_budget_us
        )

        # Restore sequence config and re-set timing budget
        self.i2c.write_byte(R.SYSTEM_SEQUENCE_CONFIG, 0xE8)
        self._set_measurement_timing_budget(
            self._measurement_timing_budget_us
        )

        # VHV calibration
        self.i2c.write_byte(R.SYSTEM_SEQUENCE_CONFIG, 0x01)
        self._perform_single_ref_calibration(R.CALIBRATION_VHV_INIT)

        # Phase calibration
        self.i2c.write_byte(R.SYSTEM_SEQUENCE_CONFIG, 0x02)
        self._perform_single_ref_calibration(0x00)

        # Restore final sequence config
        self.i2c.write_byte(R.SYSTEM_SEQUENCE_CONFIG, 0xE8)

    # ------------------------------------------------------------------
    # Timing Budget Helpers
    # ------------------------------------------------------------------

    def _calc_macro_period(self, vcsel_period_pclks: int) -> int:
        """Calculate macro period in nanoseconds.

        Port of C++ calcMacroPeriod from ST reference driver.
        """
        return ((2304 * vcsel_period_pclks * 1655) + 500) // 1000

    def _timeout_microseconds_to_mclks(
        self, timeout_us: int, vcsel_period_pclks: int
    ) -> int:
        """Convert timeout from microseconds to macro clocks."""
        macro_period_ns = self._calc_macro_period(vcsel_period_pclks)
        return (timeout_us * 1000 + (macro_period_ns // 2)) // macro_period_ns

    def _timeout_mclks_to_microseconds(
        self, timeout_mclks: int, vcsel_period_pclks: int
    ) -> int:
        """Convert timeout from macro clocks to microseconds."""
        macro_period_ns = self._calc_macro_period(vcsel_period_pclks)
        return ((timeout_mclks * macro_period_ns) + 500) // 1000

    def _decode_timeout(self, reg_val: int) -> int:
        """Decode timeout register value to macro clocks.

        Port of C++ VL53L0X_decode_timeout.
        """
        ls_byte = reg_val & 0xFF
        ms_byte = (reg_val >> 8) & 0xFF
        return (ls_byte << ms_byte) + 1

    def _encode_timeout(self, timeout_mclks: int) -> int:
        """Encode macro clocks to timeout register value.

        Port of C++ VL53L0X_encode_timeout.
        """
        if timeout_mclks <= 0:
            return 0

        ls_byte = 0
        ms_byte = 0
        timeout_mclks -= 1
        while (timeout_mclks & 0xFFFFFF00) > 0:
            timeout_mclks >>= 1
            ms_byte += 1
        ls_byte = timeout_mclks & 0xFF
        return (ms_byte << 8) | ls_byte

    def _get_measurement_timing_budget(self) -> int:
        """Get current measurement timing budget in microseconds."""
        budget_us = 1910  # Start overhead
        enables = self.i2c.read_byte(R.SYSTEM_SEQUENCE_CONFIG)

        pre_range_mclks: int | None = None

        # Pre-range step
        if (enables >> 6) & 0x01:
            pre_range_vcsel = self.i2c.read_byte(
                R.PRE_RANGE_CONFIG_VCSEL_PERIOD
            )
            pre_range_mclks = self._decode_timeout(
                self.i2c.read_word_big_endian(
                    R.PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI
                )
            )
            pre_range_us = self._timeout_mclks_to_microseconds(
                pre_range_mclks, pre_range_vcsel
            )
            budget_us += pre_range_us + 660  # overhead

        # Final-range step
        if (enables >> 7) & 0x01:
            final_range_vcsel = self.i2c.read_byte(
                R.FINAL_RANGE_CONFIG_VCSEL_PERIOD
            )
            final_range_mclks = self._decode_timeout(
                self.i2c.read_word_big_endian(
                    R.FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI
                )
            )
            if (enables >> 6) & 0x01 and pre_range_mclks is not None:
                final_range_mclks -= pre_range_mclks
            final_range_us = self._timeout_mclks_to_microseconds(
                final_range_mclks, final_range_vcsel
            )
            budget_us += final_range_us + 550  # overhead

        return budget_us

    def _set_measurement_timing_budget(self, budget_us: int) -> bool:
        """Set measurement timing budget in microseconds.

        Returns:
            True if budget was set successfully.
        """
        used_budget_us = 1320  # Start overhead
        enables = self.i2c.read_byte(R.SYSTEM_SEQUENCE_CONFIG)

        pre_range_mclks = 0

        # Pre-range step
        if (enables >> 6) & 0x01:
            pre_range_vcsel = self.i2c.read_byte(
                R.PRE_RANGE_CONFIG_VCSEL_PERIOD
            )
            pre_range_mclks = self._decode_timeout(
                self.i2c.read_word_big_endian(
                    R.PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI
                )
            )
            pre_range_us = self._timeout_mclks_to_microseconds(
                pre_range_mclks, pre_range_vcsel
            )
            used_budget_us += pre_range_us + 660

        # Final-range step
        if (enables >> 7) & 0x01:
            final_range_us = budget_us - used_budget_us - 550
            if final_range_us <= 0:
                raise ValueError("Requested timing budget too small")

            final_range_vcsel = self.i2c.read_byte(
                R.FINAL_RANGE_CONFIG_VCSEL_PERIOD
            )
            final_range_mclks = self._timeout_microseconds_to_mclks(
                final_range_us, final_range_vcsel
            )

            if (enables >> 6) & 0x01:
                final_range_mclks += pre_range_mclks

            self.i2c.write_word_big_endian(
                R.FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI,
                self._encode_timeout(final_range_mclks),
            )
            return True

        return False

    def _perform_single_ref_calibration(self, vhv_init_byte: int) -> None:
        """Perform a single reference calibration.

        Args:
            vhv_init_byte: Calibration init byte (0x40 for VHV, 0x00 for phase).

        Raises:
            TimeoutError: If calibration does not complete within 2s.
        """
        self.i2c.write_byte(R.SYSRANGE_START, 0x01 | vhv_init_byte)

        start = time.time()
        while True:
            status = self.i2c.read_byte(R.RESULT_INTERRUPT_STATUS)
            if (status & R.INTERRUPT_STATUS_MASK) != 0x00:
                break
            if time.time() - start > 2.0:
                raise TimeoutError("Timeout during reference calibration")

        self.i2c.write_byte(R.SYSTEM_INTERRUPT_CLEAR, 0x01)
        self.i2c.write_byte(R.SYSRANGE_START, 0x00)

    # ------------------------------------------------------------------
    # Public API — Measurement
    # ------------------------------------------------------------------

    def get_range(self) -> int:
        """Single-shot distance measurement (blocking).

        Returns:
            Distance in mm (with offset applied).

        Raises:
            I2CError: I2C bus failure after retries.
            TimeoutError: Measurement did not complete within timeout.
            RuntimeError: Sensor not initialized.

        Used by: ninja_core/perception.py DistanceMonitor._monitor_loop()
        Note: DistanceMonitor catches Exception broadly, so these are safe.
        """
        with self._measurement_lock:
            if not self._initialized:
                raise RuntimeError("Sensor not initialized — call initialize()")

            # Restore stop_variable sequence
            self.i2c.write_byte(0x80, 0x01)
            self.i2c.write_byte(0xFF, 0x01)
            self.i2c.write_byte(0x00, 0x00)
            self.i2c.write_byte(0x91, self._stop_variable)
            self.i2c.write_byte(0x00, 0x01)
            self.i2c.write_byte(0xFF, 0x00)
            self.i2c.write_byte(0x80, 0x00)

            # Start single-shot measurement
            self.i2c.write_byte(R.SYSRANGE_START, 0x01)

            # Calculate timeout based on timing budget
            budget_s = self._measurement_timing_budget_us / 1_000_000.0
            timeout_s = max(1.0, budget_s + 0.1)

            # Wait for measurement ready (interrupt status)
            start = time.time()
            while True:
                status = self.i2c.read_byte(R.RESULT_INTERRUPT_STATUS)
                if (status & R.INTERRUPT_STATUS_MASK) != 0x00:
                    break
                if time.time() - start > timeout_s:
                    raise TimeoutError(
                        f"Measurement did not complete within {timeout_s:.1f}s"
                    )

            # Read result: range status register + 0x0A offset
            raw_mm = self.i2c.read_word_big_endian(
                R.RESULT_RANGE_STATUS + 0x0A
            )

            # Clear interrupt
            self.i2c.write_byte(R.SYSTEM_INTERRUPT_CLEAR, 0x01)

            return raw_mm - self.offset_mm

    def get_data(self) -> dict[str, Any]:
        """Get sensor data in standardized format (Sensor interface).

        Returns a dictionary with:
        - distance_mm (int): Measured distance with offset applied.
        - is_valid (bool): Whether measurement is in valid range.
        - raw_value (int): Raw sensor value before offset correction.
        - timestamp (float): Measurement timestamp.

        Note: Fixed V2 offset bug — raw_value is now truly the raw
        value from the sensor, not the offset-corrected value.
        """
        try:
            raw_mm = self._get_raw_range()
            distance_mm = raw_mm - self.offset_mm
            return {
                "distance_mm": distance_mm,
                "is_valid": 0 < distance_mm < 8190,
                "raw_value": raw_mm,
                "timestamp": time.time(),
            }
        except Exception as exc:
            logger.error("Failed to get distance: %s", exc)
            return {
                "distance_mm": -1,
                "is_valid": False,
                "raw_value": None,
                "timestamp": time.time(),
            }

    def _get_raw_range(self) -> int:
        """Internal: perform measurement and return raw mm (no offset).

        This exists to fix the V2 offset bug — get_data() needs
        the true raw value before offset correction.

        Returns:
            Raw distance in mm from sensor (no offset applied).
        """
        with self._measurement_lock:
            if not self._initialized:
                raise RuntimeError("Sensor not initialized — call initialize()")

            # Restore stop_variable sequence
            self.i2c.write_byte(0x80, 0x01)
            self.i2c.write_byte(0xFF, 0x01)
            self.i2c.write_byte(0x00, 0x00)
            self.i2c.write_byte(0x91, self._stop_variable)
            self.i2c.write_byte(0x00, 0x01)
            self.i2c.write_byte(0xFF, 0x00)
            self.i2c.write_byte(0x80, 0x00)

            # Start single-shot measurement
            self.i2c.write_byte(R.SYSRANGE_START, 0x01)

            budget_s = self._measurement_timing_budget_us / 1_000_000.0
            timeout_s = max(1.0, budget_s + 0.1)

            start = time.time()
            while True:
                status = self.i2c.read_byte(R.RESULT_INTERRUPT_STATUS)
                if (status & R.INTERRUPT_STATUS_MASK) != 0x00:
                    break
                if time.time() - start > timeout_s:
                    raise TimeoutError(
                        f"Measurement did not complete within {timeout_s:.1f}s"
                    )

            raw_mm = self.i2c.read_word_big_endian(
                R.RESULT_RANGE_STATUS + 0x0A
            )

            self.i2c.write_byte(R.SYSTEM_INTERRUPT_CLEAR, 0x01)

            return raw_mm

    async def get_range_async(self) -> int:
        """Async version of get_range() for future asyncio integration.

        Runs the blocking get_range() in a thread pool executor
        to avoid blocking the event loop.

        Returns:
            Distance in mm (with offset applied).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_range)

    # ------------------------------------------------------------------
    # Public API — Calibration & Configuration
    # ------------------------------------------------------------------

    def set_offset(self, offset_mm: int) -> None:
        """Set measurement offset in mm.

        Args:
            offset_mm: Offset value to subtract from raw measurements.
        """
        self.offset_mm = offset_mm

    def get_ranges(self, num_samples: int) -> list[int]:
        """Take multiple measurements and return as a list.

        Args:
            num_samples: Number of measurements to take.

        Returns:
            List of distance values in mm.
        """
        return [self.get_range() for _ in range(num_samples)]

    def calibrate(self, target_distance_mm: int, num_samples: int) -> int:
        """Calibrate by measuring at a known distance.

        Temporarily sets offset to 0, takes measurements, and
        calculates the offset as (measured - target).

        Args:
            target_distance_mm: Actual distance to target in mm.
            num_samples: Number of measurements to average.

        Returns:
            Calculated offset in mm.
        """
        logger.debug(
            "Calibrating: target=%dmm, samples=%d",
            target_distance_mm,
            num_samples,
        )

        # Temporarily remove offset for calibration
        saved_offset = self.offset_mm
        self.set_offset(0)

        samples = self.get_ranges(num_samples)
        measured_distance = int(statistics.mean(samples))

        # Restore previous offset
        self.set_offset(saved_offset)

        offset = measured_distance - target_distance_mm
        logger.debug(
            "Calibration result: measured=%dmm, offset=%dmm",
            measured_distance,
            offset,
        )

        return offset

    # ------------------------------------------------------------------
    # Public API — Health & Recovery
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Quick health check — verify sensor responds.

        Returns:
            True if sensor is responding and model ID matches.
        """
        try:
            model_id = self.i2c.read_byte(R.IDENTIFICATION_MODEL_ID)
            return model_id == self._MODEL_ID
        except Exception:
            return False

    def reinitialize(self) -> None:
        """Full re-initialization for recovery from stuck state.

        Can be called at runtime without rebooting.

        Safe to call while other callers may read distance; it takes the
        same transaction lock used by get_range().
        """
        logger.info("Reinitializing VL53L0X...")
        with self._measurement_lock:
            self._initialized = False
            self.initialize()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the I2C connection.

        Safe to call multiple times.
        """
        with self._measurement_lock:
            self.i2c.close()

    # ------------------------------------------------------------------
    # Backward Compatibility — Direct I2C methods
    # These exist so old code using sensor.read_byte() still works.
    # New code should use self.i2c.read_byte() directly.
    # ------------------------------------------------------------------

    def read_byte(self, register: int) -> int:
        """Read a single byte (backward compatibility shim)."""
        return self.i2c.read_byte(register)

    def write_byte(self, register: int, value: int) -> None:
        """Write a single byte (backward compatibility shim)."""
        self.i2c.write_byte(register, value)

    def read_word(self, register: int) -> int:
        """Read a 16-bit word, big-endian (backward compatibility shim)."""
        return self.i2c.read_word_big_endian(register)

    def write_word(self, register: int, value: int) -> None:
        """Write a 16-bit word, big-endian (backward compatibility shim)."""
        self.i2c.write_word_big_endian(register, value)

    def read_block(self, register: int, count: int) -> list[int]:
        """Read a block of bytes (backward compatibility shim)."""
        return self.i2c.read_block(register, count)

    def write_block(self, register: int, data: list[int]) -> None:
        """Write a block of bytes (backward compatibility shim)."""
        self.i2c.write_block(register, data)
