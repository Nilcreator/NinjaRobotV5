# pi0vl53l0x

A robust Python driver for the VL53L0X Time-of-Flight distance sensor using pigpio.

## Features

- **Hardened initialization** — firmware boot polling (up to 1.0s) prevents "returns 0 after reboot" issue
- **Thread-safe I2C** — `threading.Lock` serializes all bus access, safe for multi-threaded use
- **Automatic retry** — exponential backoff (10→20→50ms) with bus recovery on persistent failure
- **Defined exception contract** — `I2CError`, `TimeoutError`, `RuntimeError` for clear error handling
- **Async ready** — `get_range_async()` for asyncio integration
- **Config management** — JSON-based offset storage with export/import
- **Interactive CLI** — 8 commands for standalone testing without writing code
- **100% backward compatible** — drop-in replacement for ninja_core integration

## Directory Structure

```
pi0vl53l0x/
├── pyproject.toml              # Package metadata, dependencies, CLI entry point
├── README.md                   # This document
├── LICENSE
├── tests/                      # Unit tests (60 tests total)
│   ├── test_i2c.py             # I2C bus wrapper tests (22 tests)
│   ├── test_sensor.py          # VL53L0X driver tests (22 tests)
│   └── test_config.py          # Config manager tests (16 tests)
└── src/pi0vl53l0x/
    ├── __init__.py              # Package exports (VL53L0X, ConfigManager, I2CError)
    ├── __main__.py              # Entry point for `python -m pi0vl53l0x`
    ├── registers.py             # ~60 semantic register constants
    ├── driver.py                # Backward-compat shim (re-exports VL53L0X from core)
    ├── core/                    # Core sensor modules
    │   ├── __init__.py
    │   ├── i2c.py               # Thread-safe I2C bus wrapper with retry + recovery
    │   └── sensor.py            # VL53L0X driver (~1000 lines, implements Sensor ABC)
    ├── config/                  # Configuration management
    │   ├── __init__.py
    │   └── config_manager.py    # JSON load/save/export/import
    └── cli/                     # CLI commands
        ├── __init__.py
        └── sensor_tool.py       # Click CLI tool (8 commands)
```

## Requirements

- Python ≥ 3.9
- `click` — CLI framework
- `ninja_utils` — logging and Sensor ABC
- `pigpio` — Raspberry Pi I2C (optional, required only on RPi)

## Installation

### Using `uv sync` (Recommended)

```bash
# On development machine (Mac/PC) — pigpio not needed:
cd pi0vl53l0x
uv sync

# On Raspberry Pi — includes pigpio:
cd pi0vl53l0x
uv sync --extra pi
```

> **Note:** `uv sync` automatically creates a `.venv` and installs all dependencies from `pyproject.toml`. Use `--extra pi` to include the `pigpio` optional dependency required on Raspberry Pi.

### Using `uv pip install` (Alternative)

```bash
# On development machine (Mac/PC):
uv pip install -e ./pi0vl53l0x

# On Raspberry Pi (with pigpio):
uv pip install -e "./pi0vl53l0x[pi]"
```

### As part of NinjaRobotV5 (root project)

```bash
cd NinjaRobotV5
uv sync    # pigpio is a main dependency — installed automatically
```

## Quick Start

### Python API

```python
import pigpio
from pi0vl53l0x import VL53L0X

pi = pigpio.pi()
sensor = VL53L0X(pi)  # Auto-initializes with firmware boot polling

# Single measurement
distance = sensor.get_range()
print(f"Distance: {distance} mm")

# Structured data with validity check
data = sensor.get_data()
if data["is_valid"]:
    print(f"Distance: {data['distance_mm']} mm (raw: {data['raw_value']} mm)")

# Calibration at known distance
offset = sensor.calibrate(target_distance_mm=100, num_samples=10)
sensor.set_offset(offset)

# Health check and recovery
if not sensor.health_check():
    sensor.reinitialize()

sensor.close()
pi.stop()
```

### Context Manager

```python
with VL53L0X(pi) as sensor:
    distance = sensor.get_range()
```

### Async Support

```python
distance = await sensor.get_range_async()
```

### Using with ninja_core (HAL Integration)

The library is loaded automatically by `ninja_core/hal.py` via the driver registry:

```python
# ninja_core imports it as:
from pi0vl53l0x.driver import VL53L0X
sensor = VL53L0X(pi)  # driver.py is a shim that re-exports from core.sensor
```

No changes to `ninja_core` are needed — both import paths work identically.

## API Reference

### VL53L0X (Constructor)

```python
VL53L0X(
    pi: pigpio.pi,
    i2c_bus: int = 1,
    i2c_address: int = 0x29,
    debug: bool = False,
    config_file_path: str | None = None,
    firmware_boot_timeout: float = 1.0,
)
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `pi` | (required) | Shared pigpio connection |
| `i2c_bus` | `1` | I2C bus number |
| `i2c_address` | `0x29` | 7-bit I2C address |
| `debug` | `False` | Enable debug logging |
| `config_file_path` | `None` | Path to JSON config with `offset_mm` |
| `firmware_boot_timeout` | `1.0` | Firmware boot timeout in seconds |

> **Note:** The constructor auto-calls `initialize()`. If init fails, the I2C handle is cleaned up automatically.

### Measurement Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get_range()` | `int` | Single-shot distance in mm (with offset applied) |
| `get_data()` | `dict` | `{"distance_mm", "is_valid", "raw_value", "timestamp"}` |
| `get_ranges(num_samples)` | `list[int]` | Multiple consecutive measurements |
| `get_range_async()` | `int` | Async version (runs in thread pool executor) |

### Calibration & Configuration

| Method | Returns | Description |
|--------|---------|-------------|
| `set_offset(offset_mm)` | `None` | Set distance offset in mm |
| `calibrate(target_distance_mm, num_samples)` | `int` | Measure and return calculated offset |

### Health & Recovery

| Method | Returns | Description |
|--------|---------|-------------|
| `health_check()` | `bool` | Verify sensor responds (reads Model ID) |
| `reinitialize()` | `None` | Full re-init for recovery (NOT thread-safe) |
| `close()` | `None` | Release I2C handle |

### I2CBus

Thread-safe I2C wrapper used internally by VL53L0X.

```python
from pi0vl53l0x.core.i2c import I2CBus

bus = I2CBus(pi, bus=1, address=0x29, max_retries=3)
value = bus.read_byte(0xC0)  # Read Model ID register
bus.close()
```

| Method | Returns | Description |
|--------|---------|-------------|
| `read_byte(register)` | `int` | Read single byte |
| `write_byte(register, value)` | `None` | Write single byte |
| `read_word_big_endian(register)` | `int` | Read 16-bit word (byte-swap) |
| `write_word_big_endian(register, value)` | `None` | Write 16-bit word (byte-swap) |
| `read_block(register, count)` | `list[int]` | Read block of bytes |
| `write_block(register, data)` | `None` | Write block of bytes |
| `close()` | `None` | Close I2C handle |

### ConfigManager

```python
from pi0vl53l0x.config import ConfigManager

manager = ConfigManager()         # Uses default vl53l0x.json path
manager.load()                    # Load config from file
manager.set("offset_mm", 10)      # Set a value
manager.save()                    # Save to file
manager.export_config("backup.json")
manager.import_config("backup.json")
```

### Exception Contract

| Exception | When |
|-----------|------|
| `I2CError` | I2C bus failure after all retries exhausted |
| `TimeoutError` | Measurement/firmware boot did not complete within timeout |
| `RuntimeError` | Sensor not initialized |
| `ConnectionError` | Invalid Model ID (expected 0xEE) or connection failure |

## CLI Commands

**Entry Point:** `pi0vl53l0x <command>` or `uv run pi0vl53l0x <command>`

### Read Distance

```bash
# Single reading
pi0vl53l0x get

# 10 readings at 0.5s intervals
pi0vl53l0x get --count 10 --interval 0.5
```

### Performance Measurement

```bash
# Measure readings per second (100 samples)
pi0vl53l0x performance --count 100
```

### Calibration

```bash
# Place a target at exactly 100mm from sensor, then run:
pi0vl53l0x calibrate --distance 100 --count 10
```

### Quick Test

```bash
# Initialize sensor and take 5 test readings
pi0vl53l0x test
```

### Health Status

```bash
# Full sensor health report (Model ID, connection, test reading)
pi0vl53l0x status
```

### Configuration Management

```bash
# View current settings
pi0vl53l0x config show

# Backup configuration
pi0vl53l0x config export backup.json

# Restore configuration
pi0vl53l0x config import backup.json
```

### Global Options

```bash
# Enable debug logging
pi0vl53l0x --debug get --count 5

# Use custom config file
pi0vl53l0x --config-file custom.json get
```

## Testing

```bash
# Run all unit tests (60 tests)
uv run --extra dev pytest tests/ -v

# Lint check
uv run --extra dev ruff check src/ tests/
```

### Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_i2c.py` | 22 | I2C ops, retry, recovery, thread safety |
| `test_sensor.py` | 22 | Init, ranging, offset, health, async, compat |
| `test_config.py` | 16 | Load/save, export/import, corrupt JSON |

### Manual Testing on Raspberry Pi

1. Start pigpiod: `sudo pigpiod`
2. Quick test: `pi0vl53l0x test`
3. Health check: `pi0vl53l0x status`
4. Read distances: `pi0vl53l0x get -c 5`
5. Calibrate: `pi0vl53l0x calibrate -d 100 -c 10`

## Architecture

```
┌──────────────────────────────────────────────┐
│                  ninja_core                   │
│     hal.py → from pi0vl53l0x.driver import   │
│              VL53L0X (backward-compat shim)   │
└─────────────────────┬────────────────────────┘
                      │
┌─────────────────────▼────────────────────────┐
│              pi0vl53l0x package                │
│                                               │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ core/    │  │ config/  │  │ cli/       │  │
│  │  i2c.py  │  │ config_  │  │ sensor_    │  │
│  │  sensor  │  │ manager  │  │ tool.py    │  │
│  │  .py     │  │ .py      │  │            │  │
│  └────┬─────┘  └────┬─────┘  └────┬───────┘  │
│       │              │              │          │
│  registers.py   vl53l0x.json    click CLI     │
└──────────────────────────────────────────────┘
                      │
              pigpio I2C (bus 1)
                      │
              VL53L0X sensor (0x29)
```

## License

MIT License — © 2025 Chihkuang Chang
