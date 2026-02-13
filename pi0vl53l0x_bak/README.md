# `pi0vl53l0x` Library

A Python library for the VL53L0X time-of-flight distance sensor, designed for Raspberry Pi using the `pigpio` library.

---

## V5 Changes

> [!NOTE]
> As of V5, this library implements the `Sensor` interface from `ninja_utils.interfaces`.

### Key Changes:
- **Implements `Sensor` ABC**: `initialize()`, `get_data()`, `close()` methods.
- **Standardized output**: `get_data()` returns a dictionary with `distance_mm`, `is_valid`, `raw_value`, `timestamp`.

### Example (V5):
```python
from pi0vl53l0x.driver import VL53L0X
import pigpio

pi = pigpio.pi()
sensor = VL53L0X(pi=pi)

# V5 standardized method
data = sensor.get_data()
print(f"Distance: {data['distance_mm']} mm, Valid: {data['is_valid']}")

# Legacy method still works
distance = sensor.get_range()

sensor.close()
pi.stop()
```

---

## Hardware Setup

Connect VL53L0X to I2C:
1. **VCC** → 3.3V
2. **GND** → GND
3. **SCL** → GPIO 3 (SCL)
4. **SDA** → GPIO 2 (SDA)

Enable I2C: `sudo raspi-config` → Interface Options → I2C

---

## CLI Usage

```bash
# Get distance readings
uv run pi0vl53l0x get --count 10 --interval 1.0

# Performance test
uv run pi0vl53l0x performance --count 100

# Calibrate
uv run pi0vl53l0x calibrate --distance 100
```