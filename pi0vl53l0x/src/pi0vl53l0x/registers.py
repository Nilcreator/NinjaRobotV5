"""VL53L0X register constants with semantic names.

Replaces the previous ~330 obfuscated VALUE_XX/REG_XX constants with
~60 meaningful names. Register addresses and constant values are taken
from the ST VL53L0X API and validated against the working v1 driver.

All addresses are in hexadecimal. Groups are organized by function.
"""

# ---------------------------------------------------------------------------
# Identification
# ---------------------------------------------------------------------------
IDENTIFICATION_MODEL_ID = 0xC0          # Expected value: 0xEE
IDENTIFICATION_REVISION_ID = 0xC2

# ---------------------------------------------------------------------------
# System Control
# ---------------------------------------------------------------------------
SYSRANGE_START = 0x00                   # Write 0x01 to start single-shot
SYSTEM_SEQUENCE_CONFIG = 0x01           # Enable/disable sequence steps
SYSTEM_RANGE_CONFIG = 0x09
SYSTEM_INTERMEASUREMENT_PERIOD = 0x04
SYSTEM_INTERRUPT_CONFIG_GPIO = 0x0A     # GPIO interrupt configuration
SYSTEM_INTERRUPT_CLEAR = 0x0B           # Write 0x01 to clear interrupts
SYSTEM_THRESH_HIGH = 0x0C
SYSTEM_THRESH_LOW = 0x0E

# ---------------------------------------------------------------------------
# Result Registers
# ---------------------------------------------------------------------------
RESULT_INTERRUPT_STATUS = 0x13          # Bit 0-2: interrupt status
RESULT_RANGE_STATUS = 0x14              # Range result base register

# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------
SOFT_RESET_GO2_SOFT_RESET_N = 0xBF      # Write 0x00 then 0x01 for reset
FIRMWARE_BOOT_STATUS = 0x01             # Bit 0 = firmware booted (polled)

# ---------------------------------------------------------------------------
# GPIO
# ---------------------------------------------------------------------------
GPIO_HV_MUX_ACTIVE_HIGH = 0x84          # GPIO polarity control

# ---------------------------------------------------------------------------
# Signal Rate
# ---------------------------------------------------------------------------
MSRC_CONFIG_CONTROL = 0x60
FINAL_RANGE_CFG_MIN_COUNT_RATE_RTN_LIMIT = 0x44

# ---------------------------------------------------------------------------
# SPAD (Single Photon Avalanche Diode)
# ---------------------------------------------------------------------------
GLOBAL_CFG_SPAD_ENABLES_REF_0 = 0xB0   # Base of 6-byte SPAD enable map
GLOBAL_CFG_REF_EN_START_SELECT = 0xB6
DYN_SPAD_REF_EN_START_OFFSET = 0x4F
DYN_SPAD_NUM_REQUESTED_REF_SPAD = 0x4E

# ---------------------------------------------------------------------------
# Timing Configuration
# ---------------------------------------------------------------------------
PRE_RANGE_CONFIG_VCSEL_PERIOD = 0x50
PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x51
FINAL_RANGE_CONFIG_VCSEL_PERIOD = 0x70
FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x71

# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------
VHV_CFG_PAD_SCL_SDA_EXTSUP_HV = 0x89   # Voltage reference pad config
ALGO_PART_TO_PART_RANGE_OFFSET = 0x28
OSC_CALIBRATE_VAL = 0xF8

# ---------------------------------------------------------------------------
# Communication / Power
# ---------------------------------------------------------------------------
I2C_STANDARD_MODE = 0x88                # I2C mode register
I2C_SLAVE_DEVICE_ADDRESS = 0x8A
POWER_MGMT_GO1_POWER_FORCE = 0x80

# ---------------------------------------------------------------------------
# Numeric Constants
# ---------------------------------------------------------------------------
INTERRUPT_STATUS_MASK = 0x07            # Bits 0-2 of interrupt register
GPIO_INTERRUPT_CONFIG = 0x04            # New-sample-ready interrupt mode
SPAD_COUNT_MASK = 0x7F                  # Mask for SPAD count bits
SPAD_APERTURE_BIT = 0x80                # Bit 7 = aperture flag
SPAD_START_INDEX_APERTURE = 12          # First aperture SPAD index
SPAD_MAP_BITS_PER_BYTE = 8
SPAD_TOTAL_COUNT = 48
SPAD_NUM_REQUESTED_REF = 0x2C          # Default requested reference SPADs
CALIBRATION_VHV_INIT = 0x40             # VHV calibration init byte
TIMEOUT_LIMIT = 2.0                     # Maximum wait time in seconds
SIGNAL_RATE_LIMIT_FIXED = 32            # 0.25 MCPS * 128 = 32

# ---------------------------------------------------------------------------
# Magic Registers (unnamed in ST datasheet, used during init sequence)
# These are written as raw hex addresses per the ST reference driver.
# They MUST remain as hex values for the init sequence to work correctly.
# ---------------------------------------------------------------------------
# Page-select and internal-state registers used in _set_registers()
# and _get_spad_info() sequences. See core/sensor.py for usage.
