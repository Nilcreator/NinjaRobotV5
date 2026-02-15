"""pi0vl53l0x — VL53L0X Time-of-Flight distance sensor driver.

This library provides a robust, thread-safe Python driver for the
VL53L0X sensor using pigpio for I2C communication on Raspberry Pi.

Exports:
    VL53L0X: Main sensor class implementing the Sensor ABC.

Usage:
    from pi0vl53l0x import VL53L0X
    # or for backward compatibility:
    from pi0vl53l0x.driver import VL53L0X
"""

from .core.sensor import VL53L0X

__all__ = ["VL53L0X"]
__version__ = "2.0.0"
