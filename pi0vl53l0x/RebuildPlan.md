# pi0vl53l0x Library Rebuild Plan

> **Status:** Refined Plan Approved → Implementation In Progress  
> **Created:** 2026-02-13  
> **Last Updated:** 2026-02-15 (audit refinement — thread safety, exception contracts, ContinuousReader deferred)  
> **Reference:** Previous version backed up to `pi0vl53l0x_bak/`

---

## 1. Overview

### 1.1 Objective

Full rewrite from scratch of the pi0vl53l0x library — creating a robust, modular VL53L0X Time-of-Flight distance sensor driver. The new library must:

1. **100% backward compatible** — zero changes to ninja_core (HAL, perception, api_wrappers)
2. **Fix the "returns 0 after reboot" bug** — hardened initialization with firmware boot polling
3. **Resilient I2C** — automatic retry with exponential backoff + **thread-safe** (`threading.Lock`)
4. **Standalone capable** — usable independently OR integrated into NinjaRobotV5
5. **Async ready** — `get_range_async()` for future asyncio integration
6. **Fully tested** — unit tests with mocked pigpio for PC/Mac development
7. **Defined exception contract** — `I2CError`, `TimeoutError`, `RuntimeError` on failure

### 1.2 Previous Library Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| V1 | 🔴 Critical | No I2C retry — single bus glitch crashes driver. Also no thread safety — concurrent access from `DistanceMonitor` thread and main thread corrupts state | `driver.py` all I2C calls |
| V2 | 🔴 Critical | `get_data()` offset bug — `get_range()` returns `raw - offset`, but `get_data()` stores that offset-corrected value as `raw_value`. The "raw" value is not actually raw | `driver.py` L556-557 |
| V3 | 🔴 Critical | No firmware boot polling after soft reset — **root cause of "returns 0 after reboot"** | `driver.py` L304-307 |
| V4 | 🔴 Critical | VHV config error silently swallowed | `driver.py` L97-99 |
| V5 | 🟡 Medium | No measurement quality validation (signal rate, sigma) | `driver.py` L560-571 |
| V6 | 🟡 Medium | Resource leak on init failure — I2C handle not closed | `driver.py` L43 |
| V7 | 🟡 Medium | `close()` doesn't stop sensor ranging — leaves stale state | `driver.py` L622 |
| V8 | 🟡 Medium | Race condition with pigpiod on boot | `hal.py` L253 |
| V9 | 🟢 Low | ~160 magic VALUE_XX/REG_XX constants with no semantic meaning | `constants.py` |
| V10 | 🟢 Low | Unnecessary numpy dependency (~30MB on RPi Zero) | `driver.py` L13 |
| V11 | 🟢 Low | Config in home dir `~/vl53l0x.json` instead of project-relative | `config_manager.py` |
| V12 | 🟢 Low | Zero test files | — |

### 1.3 Root Cause Analysis: "Returns 0 After Reboot"

Six contributing factors were identified:

**RC#1 — No Firmware Boot-Ready Polling (Primary Cause)**
After soft reset, the driver waits only 10ms before writing registers. The VL53L0X firmware boot time is variable. The ST official API polls register `0x01` bit 0 until firmware boot is confirmed. Our current driver never does this. If register writes happen before boot finishes, the NVM loading process overwrites them — leaving the sensor in a corrupted state returning all zeros.

**RC#2 — VHV Config Error Silently Ignored**
The VHV voltage reference configuration write (`VHV_CFG_PAD_SCL_SDA_EXTSUP_HV`) is wrapped in a bare `try/except: pass`. If this fails, I2C pad voltage levels are wrong and all subsequent reads return 0x00.

**RC#3 — Race with pigpiod Startup**
If ninja_core starts before pigpiod is fully ready, `i2c_open()` may succeed but operations behave erratically. HAL gives up entirely on failure (sets `distance_sensor = None`) with no retry.

**RC#4 — Stale SYSRANGE_START State**
After power-off, the sensor may retain a pending ranging command. `get_range()` never checks if a previous measurement was active before starting a new one.

**RC#5 — First Measurement Returns Stale Data**
Interrupt status register may have a stale value from the previous session. If `_configure_interrupt_gpio()` clear was corrupted by timing issues, the first measurement can return 0.

**RC#6 — Improper Shutdown**
`close()` only calls `i2c_close()` — never stops the sensor's ranging operation. On power loss or SIGKILL, the sensor is left in active ranging mode.

---

## 2. Architecture

### 2.1 File Structure

```
pi0vl53l0x/
├── src/pi0vl53l0x/
│   ├── __init__.py              # Exports: VL53L0X
│   ├── driver.py                # Backward-compat shim → core.sensor
│   ├── core/
│   │   ├── __init__.py
│   │   ├── sensor.py            # VL53L0X class (Sensor ABC implementation)
│   │   └── i2c.py               # I2C helper with retry, recovery & Lock
│   ├── registers.py             # Clean register constants (semantic names)
│   ├── config/
│   │   ├── __init__.py
│   │   └── config_manager.py    # Project-relative config (pi0servo pattern)
│   └── cli/
│       ├── __init__.py
│       └── sensor_tool.py       # Interactive CLI tool
├── tests/
│   ├── __init__.py
│   ├── test_i2c.py              # I2C retry + thread safety tests (mocked pigpio)
│   ├── test_sensor.py           # VL53L0X driver tests (mocked pigpio)
│   └── test_config.py           # Config manager tests
├── pyproject.toml               # pigpio as optional dep (RPi-only)
├── RebuildPlan.md               # This file
├── README.md
└── LICENSE
```

> **Note:** `ContinuousReader` (`core/continuous.py`, `test_continuous.py`) is **deferred** to a future Phase 6. The core driver and ninja_core integration are the priority.

### 2.2 Module Responsibilities

| Module | Purpose |
|--------|---------|
| `core/i2c.py` | Resilient I2C bus wrapper — `threading.Lock()` for thread safety, automatic retry (3 attempts, exponential backoff 10→20→50ms), bus recovery on persistent failure, endian handling (`read_word_big_endian`) |
| `core/sensor.py` | VL53L0X class implementing `Sensor` ABC — hardened init **with cleanup on failure**, single-shot ranging, quality validation, calibration, async support, health check, reinitialize |
| ~~`core/continuous.py`~~ | **DEFERRED to Phase 6** — `ContinuousReader` for background polling. `perception.py.DistanceMonitor` already provides this for NinjaRobotV5 |
| `registers.py` | Clean VL53L0X register map with semantic names (~60 constants vs. previous ~330) |
| `config/config_manager.py` | Project-relative JSON config following pi0servo pattern |
| `cli/sensor_tool.py` | Interactive CLI: get, performance, calibrate, test, status, config |
| `driver.py` | **Thin shim**: `from .core.sensor import VL53L0X` — preserves `pi0vl53l0x.driver.VL53L0X` import path for DRIVER_REGISTRY |

### 2.3 Continuous Monitoring Design

**Current state:** The driver only provides single-shot `get_range()`. Continuous monitoring, velocity tracking, and emergency stop all live in `ninja_core/perception.py`.

**Decision: ContinuousReader is DEFERRED to Phase 6.** The `perception.py.DistanceMonitor` already provides background polling with velocity tracking and emergency stop — features that are robot-specific and don't belong in the driver library.

| Feature | Driver (Phases 1-5) | ContinuousReader (Phase 6, future) | perception.py DistanceMonitor |
|---------|---------------------|-----------------------------------|---------------------------------|
| Single-shot measurement | ✅ `get_range()` | — | ✅ via driver |
| Continuous background polling | ❌ | ✅ simple thread | ✅ with velocity |
| Async measurement | ✅ `get_range_async()` | — | ✅ future asyncio |
| Velocity tracking | ❌ | ❌ | ✅ Robot-specific |
| Emergency stop | ❌ | ❌ | ✅ Robot-specific |
| Health check & recovery | ✅ `health_check()` + `reinitialize()` | — | ✅ can call driver |

### 2.4 Async `get_range_async()`

Wraps the blocking I2C measurement using `asyncio.to_thread()` so the asyncio event loop stays responsive during the ~30ms I2C wait:

```python
async def get_range_async(self) -> int:
    """Non-blocking distance measurement for asyncio applications."""
    return await asyncio.to_thread(self.get_range)
```

**Why `asyncio.to_thread()`?** I2C on Raspberry Pi uses kernel-level system calls via pigpio — they can't be made truly async at the hardware level. This is the standard Python pattern (same approach as FastAPI, aiohttp) for wrapping blocking I/O.

**Enables:** Web server, BLE, display, and AI agent can run concurrently during measurements. Future: perception.py can be refactored from manual threading to clean asyncio coroutines.

---

## 3. Public API

### 3.1 VL53L0X Class (Sensor ABC)

```python
class VL53L0X(Sensor):
    """VL53L0X ToF distance sensor driver.
    
    Implements the Sensor ABC from ninja_utils.interfaces.
    """
    
    def __init__(
        self, 
        pi: pigpio.pi,
        i2c_bus: int = 1, 
        i2c_address: int = 0x29,
        debug: bool = False, 
        config_file_path: Path | None = None
    ) -> None:
        """Initialize VL53L0X sensor.
        
        Constructor signature is IDENTICAL to the previous version
        for backward compatibility with ninja_core HAL.
        """
        ...

    # --- Sensor ABC Methods ---

    def initialize(self) -> None:
        """Hardened initialization sequence.
        
        The new sequence includes:
        1. Check pi.connected
        2. i2c_open()
        3. check_connection() — verify Model ID = 0xEE
        4. reset() — soft reset
        5. _wait_for_firmware_boot() — poll reg 0x01 ⭐ NEW
        6. Clear SYSRANGE_START + interrupts ⭐ NEW
        7. Register initialization (with VHV retry) ⭐ FIXED
        8. SPAD configuration
        9. Timing budget + calibration
        10. _flush_stale_state() — dummy measurement ⭐ NEW
        """
        ...

    def get_data(self) -> dict[str, Any]:
        """Get standardized sensor data.
        
        Returns:
            {
                "distance_mm": int,     # Corrected distance
                "is_valid": bool,       # Based on range status + quality metrics
                "raw_value": int,       # True raw sensor value (BEFORE offset)
                "range_status": int,    # Hardware range status code
                "timestamp": float      # time.time()
            }
        
        Note: The offset bug from the previous version is FIXED.
        """
        ...

    def close(self) -> None:
        """Properly shut down the sensor.
        
        Stops any active ranging, clears interrupts, then closes I2C.
        Guards against double-close.
        """
        ...

    # --- Measurement Methods ---

    def get_range(self) -> int:
        """Single-shot distance measurement (blocking).
        
        Returns:
            Distance in mm (with offset applied).
        
        Raises:
            I2CError: I2C bus failure after retries.
            TimeoutError: Measurement did not complete within 2s.
            RuntimeError: Sensor not initialized.
        
        Used by: ninja_core/perception.py DistanceMonitor._monitor_loop()
        Note: DistanceMonitor catches Exception broadly, so these are safe.
        """
        ...

    async def get_range_async(self) -> int:
        """Non-blocking distance measurement for asyncio apps.
        
        Returns:
            Distance in mm, via asyncio.to_thread().
        """
        ...

    # --- Calibration ---

    def calibrate(self, target_distance_mm: int, num_samples: int) -> int:
        """Calibrate offset by measuring a target at known distance.
        
        Returns:
            Calculated offset_mm value.
        """
        ...

    def set_offset(self, offset_mm: int) -> None:
        """Set the measurement offset in mm."""
        ...

    # --- Reliability (NEW) ---

    def health_check(self) -> bool:
        """Quick sensor health check.
        
        Verifies Model ID and performs a test measurement.
        Returns False if sensor is stuck (returns 0).
        """
        ...

    def reinitialize(self) -> None:
        """Full re-initialization for recovery from stuck state.
        
        Can be called at runtime without rebooting.
        
        ⚠️ NOT thread-safe — caller MUST stop ContinuousReader or
        DistanceMonitor before calling this method.
        """
        ...

    def check_connection(self) -> None:
        """Verify sensor is connected (Model ID = 0xEE)."""
        ...

    def reset(self) -> None:
        """Perform soft reset of the sensor."""
        ...

    # --- Context Manager ---

    def __enter__(self) -> "VL53L0X": ...
    def __exit__(self, *args) -> None: ...
```

### 3.2 ContinuousReader Class — DEFERRED TO PHASE 6

> **Status:** Deferred. Will be implemented as a separate `core/continuous.py` module in a future phase.
> **Reason:** `perception.py.DistanceMonitor` already handles continuous reading with velocity tracking and emergency stop. Adding `ContinuousReader` now would not benefit ninja_core integration.

See Phase 6 (§5.6) for the planned API.

### 3.3 I2CBus Class (Internal)

```python
class I2CBus:
    """Resilient, thread-safe I2C bus wrapper with automatic retry.
    
    All I2C operations go through this class. Thread-safe via
    threading.Lock() — required because DistanceMonitor and
    main thread may access I2C concurrently.
    
    On failure:
    1. Retry up to max_retries times with exponential backoff (10→20→50ms)
    2. On persistent failure, attempt bus recovery (close + reopen)
    3. Raise I2CError with clear diagnostic message
    """
    
    def __init__(
        self, 
        pi: pigpio.pi, 
        bus: int = 1, 
        address: int = 0x29,
        max_retries: int = 3
    ) -> None:
        self._lock = threading.Lock()  # ⭐ Thread safety
        ...

    def read_byte(self, register: int) -> int:  # acquires _lock
        ...
    def write_byte(self, register: int, value: int) -> None:  # acquires _lock
        ...
    def read_word_big_endian(self, register: int) -> int:  # acquires _lock
        ...
    def write_word_big_endian(self, register: int, value: int) -> None:  # acquires _lock
        ...
    def read_block(self, register: int, count: int) -> list[int]:  # acquires _lock
        ...
    def write_block(self, register: int, data: list[int]) -> None:  # acquires _lock
        ...
    def close(self) -> None: ...
```

---

## 4. Backward Compatibility

### 4.1 Requirements

**Zero changes to ninja_core.** All existing import paths, constructor signatures, and method interfaces must be preserved exactly.

### 4.2 Compatibility Matrix

| Requirement | Consumer | Solution |
|------------|----------|---------|
| `from pi0vl53l0x.driver import VL53L0X` | HAL DRIVER_REGISTRY | `driver.py` shim: `from .core.sensor import VL53L0X` |
| `VL53L0X(pi=self.pi)` | `hal.py` L253 | Exact constructor signature preserved |
| `.get_range() → int` | `perception.py` L42, L132 | Method on VL53L0X |
| `.get_data() → dict` | `api_wrappers.py` L39 | Method on VL53L0X (bug fixed) |
| `.close()` | `hal.py` L283 | Method on VL53L0X (enhanced) |
| `.initialize()` | Sensor ABC | Method on VL53L0X (hardened) |
| `__enter__` / `__exit__` | CLI context manager | Preserved |

### 4.3 Import Shim (`driver.py`)

```python
"""Backward-compatibility shim.

This module preserves the import path `pi0vl53l0x.driver.VL53L0X`
used by ninja_core's DRIVER_REGISTRY.
"""
from .core.sensor import VL53L0X  # noqa: F401

__all__ = ["VL53L0X"]
```

---

## 5. Implementation Phases

### Phase 1: Scaffold & I2C Module

**Goal:** Create project structure and the foundational I2C layer.

**Files to create:**
- `pyproject.toml` — project metadata, dependencies (click, ninja_utils — NO numpy, pigpio as **optional**)
- `src/pi0vl53l0x/__init__.py` — exports
- `src/pi0vl53l0x/core/__init__.py`
- `src/pi0vl53l0x/core/i2c.py` — `I2CBus` class with retry logic
- `src/pi0vl53l0x/registers.py` — semantic register constants
- `tests/__init__.py`
- `tests/test_i2c.py` — unit tests (mocked pigpio)

**Implementation details for `core/i2c.py`:**
```python
class I2CBus:
    def __init__(self, pi, bus=1, address=0x29, max_retries=3):
        if not pi.connected:
            raise ConnectionError("pigpiod is not connected")
        self.pi = pi
        self.handle = pi.i2c_open(bus, address)
        self._bus = bus
        self._address = address
        self._max_retries = max_retries
        self._closed = False
        self._lock = threading.Lock()  # ⭐ Thread safety for concurrent access

    def read_byte(self, register):
        with self._lock:  # ⭐ All I2C ops are serialized
            for attempt in range(self._max_retries):
                try:
                    value = self.pi.i2c_read_byte_data(self.handle, register)
                    return int(value)
                except Exception as e:
                    if attempt == self._max_retries - 1:
                        raise I2CError(f"I2C read_byte(0x{register:02X}) "
                                       f"failed after {self._max_retries} attempts") from e
                    time.sleep(0.01 * (2 ** attempt))  # 10ms, 20ms, 40ms

    # Similar retry pattern for write_byte, read_word, write_word, etc.

    def read_word_big_endian(self, register):
        """Read 16-bit value in VL53L0X native big-endian byte order."""
        val = self._read_word_raw(register)
        return ((val & 0xFF) << 8) | (val >> 8)  # Swap bytes

    def close(self):
        if not self._closed:
            self.pi.i2c_close(self.handle)
            self._closed = True
```

**Implementation details for `registers.py`:**

Replace the ~330 lines of obfuscated `VALUE_XX`/`REG_XX` constants with ~60 semantic names:

```python
# --- Identification ---
IDENTIFICATION_MODEL_ID = 0xC0          # Expected value: 0xEE

# --- System Control ---
SYSRANGE_START = 0x00
SYSTEM_SEQUENCE_CONFIG = 0x01
SYSTEM_INTERRUPT_CONFIG_GPIO = 0x0A
SYSTEM_INTERRUPT_CLEAR = 0x0B
RESULT_INTERRUPT_STATUS = 0x13
RESULT_RANGE_STATUS = 0x14

# --- Reset ---
SOFT_RESET_GO2_SOFT_RESET_N = 0xBF
FIRMWARE_BOOT_STATUS = 0x01              # Bit 0 = firmware booted

# --- GPIO ---
GPIO_HV_MUX_ACTIVE_HIGH = 0x84

# --- Signal Rate ---
MSRC_CONFIG_CONTROL = 0x60
FINAL_RANGE_CFG_MIN_COUNT_RATE_RTN_LIMIT = 0x44

# --- SPAD ---
GLOBAL_CFG_SPAD_ENABLES_REF_0 = 0xB0
GLOBAL_CFG_REF_EN_START_SELECT = 0xB6
DYN_SPAD_REF_EN_START_OFFSET = 0x4F
DYN_SPAD_NUM_REQUESTED_REF_SPAD = 0x4E

# --- Timing ---
PRE_RANGE_CONFIG_VCSEL_PERIOD = 0x50
PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x51
FINAL_RANGE_CONFIG_VCSEL_PERIOD = 0x70
FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x71

# --- Calibration ---
VHV_CFG_PAD_SCL_SDA_EXTSUP_HV = 0x89

# --- Communication ---
I2C_STANDARD_MODE = 0x88

# --- Constants ---
INTERRUPT_STATUS_MASK = 0x07
GPIO_INTERRUPT_CONFIG = 0x04
SPAD_COUNT_MASK = 0x7F
SPAD_APERTURE_BIT = 0x80
SPAD_START_INDEX_APERTURE = 12
SPAD_MAP_BITS_PER_BYTE = 8
SPAD_TOTAL_COUNT = 48
SPAD_NUM_REQUESTED_REF = 0x2C
CALIBRATION_VHV_INIT = 0x40
TIMEOUT_LIMIT = 2.0
```

**Verification:** `uv run pytest tests/test_i2c.py -v`

---

### Phase 2: Core Sensor Driver

**Goal:** Rewrite VL53L0X class from scratch with hardened initialization.

**Files to create:**
- `src/pi0vl53l0x/core/sensor.py` — VL53L0X class
- `src/pi0vl53l0x/driver.py` — backward-compat shim
- `tests/test_sensor.py` — unit tests (mocked pigpio)

**Hardened initialization sequence:**

```
Step 1:  Check pi.connected
Step 2:  I2CBus() — opens I2C with retry
Step 3:  check_connection() — verify Model ID = 0xEE
Step 4:  reset() — soft reset (write 0x00, wait, write 0x01)
Step 5:  ⭐ _wait_for_firmware_boot() — poll reg 0x01 bit 0 (up to 1.0s, configurable)
Step 6:  ⭐ Clear SYSRANGE_START (0x00) + SYSTEM_INTERRUPT_CLEAR (0x01)
Step 7:  _set_registers() — initial register configuration
Step 8:  ⭐ VHV config WITH RETRY (3 attempts, no silent catch)
Step 9:  _setup_spad() — SPAD configuration (with existing 5-retry)
Step 10: _configure_interrupt() — GPIO interrupt setup
Step 11: _set_timing_and_calibrate() — timing budget + ref calibration
Step 12: ⭐ _flush_stale_state() — dummy measurement, discard result
```

Steps marked ⭐ are **new additions** that fix the reboot issue.

**Key method implementations:**

```python
def _wait_for_firmware_boot(self, timeout_s: float = 1.0) -> None:
    """Poll register 0x01 until firmware boot is confirmed.
    
    Default timeout increased from 500ms to 1.0s to handle cold boot.
    """
    start = time.time()
    while True:
        if self.i2c.read_byte(R.FIRMWARE_BOOT_STATUS) & 0x01:
            self.__log.debug("Firmware boot confirmed")
            return
        if time.time() - start > timeout_s:
            raise TimeoutError(
                "VL53L0X firmware did not boot within "
                f"{timeout_s}s after reset"
            )
        time.sleep(0.005)  # 5ms poll interval

def _flush_stale_state(self) -> None:
    """Perform a dummy measurement to clear any stale state."""
    try:
        self.get_range()
        self.__log.debug("Stale state flushed (dummy measurement)")
    except Exception:
        self.i2c.write_byte(R.SYSTEM_INTERRUPT_CLEAR, 0x01)
        self.__log.debug("Flushed stale interrupt")

def close(self) -> None:
    """Properly shut down sensor and close I2C."""
    if self._closed:
        return
    try:
        self.i2c.write_byte(R.SYSRANGE_START, 0x00)
        self.i2c.write_byte(R.SYSTEM_INTERRUPT_CLEAR, 0x01)
    except Exception:
        pass  # Best-effort cleanup
    finally:
        self.i2c.close()
        self._closed = True

def get_data(self) -> dict[str, Any]:
    """Get sensor data — OFFSET BUG FIXED."""
    try:
        # get_range() returns (raw - offset)
        distance = self.get_range()
        raw_value = distance + self.offset_mm  # True raw value
        return {
            "distance_mm": distance,
            "is_valid": 0 < distance < 8190,
            "raw_value": raw_value,
            "timestamp": time.time(),
        }
    except Exception as e:
        self.__log.error("Failed to get distance: %s", e)
        return {
            "distance_mm": -1,
            "is_valid": False,
            "raw_value": None,
            "timestamp": time.time(),
        }

def health_check(self) -> bool:
    """Quick sensor health check."""
    try:
        model_id = self.i2c.read_byte(R.IDENTIFICATION_MODEL_ID)
        if model_id != 0xEE:
            return False
        distance = self.get_range()
        return distance > 0
    except Exception:
        return False

def reinitialize(self) -> None:
    """Full re-initialization for runtime recovery.
    
    ⚠️ NOT thread-safe — caller MUST stop ContinuousReader or
    DistanceMonitor before calling this method.
    """
    self.__log.warning("Reinitializing sensor...")
    self.reset()
    self._wait_for_firmware_boot()
    self._clear_stale_state()
    self._set_registers()
    self._configure_vhv()
    self._setup_spad()
    self._configure_interrupt()
    self._set_timing_and_calibrate()
    self._flush_stale_state()
    self.__log.info("Sensor reinitialized successfully")
```

**Verification:** `uv run pytest tests/test_sensor.py -v`

---

### Phase 3: Config Manager

**Goal:** Add config management. *(ContinuousReader moved to Phase 6.)*

**Files to create:**
- `src/pi0vl53l0x/config/__init__.py`
- `src/pi0vl53l0x/config/config_manager.py` — project-relative config
- `tests/test_config.py`

**ConfigManager implementation (pi0servo pattern):**

```python
class ConfigManager:
    DEFAULT_FILENAME = "vl53l0x.json"
    DEFAULT_CONFIG = {"offset_mm": 0}

    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / self.DEFAULT_FILENAME
        self._path = config_path

    def load(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text())
        return dict(self.DEFAULT_CONFIG)

    def save(self, config: dict) -> None:
        self._path.write_text(json.dumps(config, indent=2))

    def show(self) -> str:
        return json.dumps(self.load(), indent=2)
```

**Verification:** `uv run pytest tests/test_config.py -v`

---

### Phase 4: CLI Module

**Goal:** Create interactive CLI tool for standalone testing.

**Files to create:**
- `src/pi0vl53l0x/cli/__init__.py`
- `src/pi0vl53l0x/cli/sensor_tool.py`
- `src/pi0vl53l0x/__main__.py`

**CLI commands:**

| Command | Description |
|---------|-------------|
| `get` | Read distance (options: `--count`, `--interval`) |
| `performance` | Measure readings per second (option: `--count`) |
| `calibrate` | Guided calibration (options: `--distance`, `--count`) |
| `test` | Quick sensor validation (init + 5 readings) |
| `status` | Sensor health report (model ID, connection, test reading) |
| `config show` | Display current config |
| `config export <file>` | Export config to file |
| `config import <file>` | Import config from file |

**Entry point (pyproject.toml):**
```toml
[project.scripts]
pi0vl53l0x = "pi0vl53l0x.__main__:main"
```

**Verification:** Manual testing of CLI commands on Raspberry Pi.

---

### Phase 5: Integration & Documentation

**Goal:** Verify ninja_core compatibility and update all documentation.

**Steps:**

1. **Import verification:**
   ```python
   from pi0vl53l0x.driver import VL53L0X  # DRIVER_REGISTRY path
   from pi0vl53l0x import VL53L0X         # Direct import
   ```

2. **Lint:** `uv run ruff check src/ tests/`

3. **Full test suite:** `uv run pytest tests/ -v`

4. **Documentation updates:**
   - `pi0vl53l0x/README.md` — new library documentation
   - `DevelopmentLog.md` — log the rebuild
   - `DevelopmentGuide.md` — update pi0vl53l0x section
   - `ProjectUpgradePlan.md` — mark phase complete

---

### Phase 6: ContinuousReader *(DEFERRED — Future)*

**Goal:** Add optional background continuous polling for standalone users.

**Files to create (future):**
- `src/pi0vl53l0x/core/continuous.py` — `ContinuousReader`
- `tests/test_continuous.py`

**Scope clarification:**

| Feature | ContinuousReader (driver) | DistanceMonitor (ninja_core) |
|---------|--------------------------|------------------------------|
| Background polling | ✅ simple thread | ✅ with velocity tracking |
| Thread-safe cache | ✅ `latest` property | ✅ `_current_distance` |
| Velocity tracking | ❌ | ✅ Robot-specific |
| Emergency stop | ❌ | ✅ Robot-specific |
| Health auto-recovery | ❌ | ✅ Can call `reinitialize()` |

> **Note:** `reinitialize()` is NOT thread-safe. Caller must stop the reader/monitor before calling it.

---

## 6. Testing Strategy

### 6.1 Unit Tests (PC/Mac — mocked pigpio)

All tests use a mocked `pigpio.pi()` so they run without hardware.

| Test File | Coverage |
|-----------|----------|
| `test_i2c.py` | Retry on failure, backoff timing, bus recovery, byte-swap endian, close guard, **thread safety** (concurrent read/write) |
| `test_sensor.py` | Init sequence (boot polling, VHV retry, **cleanup on failure**), get_range() **exception contract**, get_data() correctness (offset fix), health_check(), reinitialize(), async via asyncio, error propagation, context manager |
| `test_config.py` | Load/save, default path resolution, missing file handling, export/import |

```bash
cd pi0vl53l0x && uv run pytest tests/ -v
```

### 6.2 Manual Hardware Tests (Raspberry Pi)

| Test | Command | Pass Criteria |
|------|---------|---------------|
| Basic reading | `uv run pi0vl53l0x get --count 10` | Readings within ±20mm of known distance |
| **Reboot survival** | **Reboot Pi → immediately run `get`** | **No "returns 0" issue** |
| Performance | `uv run pi0vl53l0x performance --count 100` | ~30-40 Hz, zero I2C errors |
| Calibration | `uv run pi0vl53l0x calibrate --distance 200` | Offset saved, subsequent reads accurate |
| Health check | `uv run pi0vl53l0x status` | Reports healthy sensor |
| Integration | `uv run ninja_core server` | "Distance sensor initialized.", live web readings |

---

## 7. Dependencies

### Required (pyproject.toml)

```toml
[project]
dependencies = [
    "click",
    "ninja_utils",
]

[project.optional-dependencies]
pi = ["pigpio"]  # RPi-only — requires pigpiod daemon
dev = [
    "pytest",
    "ruff",
]
```

> **Note:** `numpy` is **removed**. Replaced by `statistics.mean()` from the Python standard library.

---

## 8. Development Workflow

### Stage 1: PC/Mac Development
1. Write code following the phase plan
2. Run unit tests with mocked pigpio: `uv run pytest tests/ -v`
3. Lint: `uv run ruff check src/ tests/`

### Stage 2: Raspberry Pi Validation
1. Transfer code to RPi Zero 2W
2. Install: `cd pi0vl53l0x && uv pip install -e .`
3. Run manual hardware tests from §6.2
4. Run ninja_core integration test
