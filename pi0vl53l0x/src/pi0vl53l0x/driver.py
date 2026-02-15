"""Backward-compatibility shim for pi0vl53l0x.driver.

ninja_core's DRIVER_REGISTRY imports VL53L0X from this module:
    from pi0vl53l0x.driver import VL53L0X

This shim re-exports VL53L0X from the new core.sensor module
so existing import paths continue to work unchanged.
"""

from pi0vl53l0x.core.sensor import VL53L0X

__all__ = ["VL53L0X"]
