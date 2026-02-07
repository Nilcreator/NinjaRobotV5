"""Configuration manager for servo calibration data.

Manages JSON-based configuration with support for per-servo calibration
including the new 'speed' field.
"""

import json
from pathlib import Path
from typing import Any

from ..core.servo import ServoCalibration

# Default config filename (relative to library)
DEFAULT_CONFIG_FILE = "servo.json"


def get_default_config_path() -> Path:
    """Get the default config file path (relative to this package).

    Returns:
        Path to default servo.json location
    """
    # Look for config in the package's parent (library root) first
    package_dir = Path(__file__).parent.parent
    return package_dir / DEFAULT_CONFIG_FILE


class ConfigManager:
    """Manages servo calibration configuration persistence.

    Loads and saves ServoCalibration data to/from JSON files.
    Supports the new 'speed' field for per-servo speed limits.
    """

    def __init__(self, config_path: str | Path | None = None):
        """Initialize ConfigManager.

        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            self._config_path = get_default_config_path()
        else:
            self._config_path = Path(config_path)

        self._data: dict[int, dict[str, Any]] = {}

    @property
    def config_path(self) -> Path:
        """Current config file path."""
        return self._config_path

    @config_path.setter
    def config_path(self, value: str | Path):
        """Set config file path."""
        self._config_path = Path(value)

    def exists(self) -> bool:
        """Check if config file exists."""
        return self._config_path.exists()

    def load(self) -> bool:
        """Load configuration from file.

        Returns:
            True if loaded successfully, False if file doesn't exist or error
        """
        if not self._config_path.exists():
            return False

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # Convert string keys to int (JSON only supports string keys)
            self._data = {}
            for key, value in raw_data.items():
                try:
                    pin = int(key)
                    self._data[pin] = value
                except ValueError:
                    # Skip non-numeric keys (e.g., metadata)
                    pass

            return True
        except (json.JSONDecodeError, OSError):
            return False

    def save(self) -> bool:
        """Save configuration to file.

        Returns:
            True if saved successfully, False on error
        """
        try:
            # Ensure parent directory exists
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert int keys to strings for JSON
            json_data = {str(k): v for k, v in self._data.items()}

            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)

            return True
        except OSError:
            return False

    def get_calibration(self, pin: int) -> ServoCalibration:
        """Get calibration for a specific pin.

        Args:
            pin: GPIO pin number

        Returns:
            ServoCalibration for the pin (defaults if not configured)
        """
        if pin not in self._data:
            return ServoCalibration()

        data = self._data[pin]
        return ServoCalibration(
            pulse_min=data.get("pulse_min", 500),
            pulse_max=data.get("pulse_max", 2500),
            pulse_center=data.get("pulse_center", 1500),
            angle_min=data.get("angle_min", -90.0),
            angle_max=data.get("angle_max", 90.0),
            angle_center=data.get("angle_center", 0.0),
            speed=data.get("speed", 80),  # New V5 field
        )

    def set_calibration(self, pin: int, calibration: ServoCalibration):
        """Set calibration for a specific pin.

        Args:
            pin: GPIO pin number
            calibration: ServoCalibration to store
        """
        self._data[pin] = {
            "pulse_min": calibration.pulse_min,
            "pulse_max": calibration.pulse_max,
            "pulse_center": calibration.pulse_center,
            "angle_min": calibration.angle_min,
            "angle_max": calibration.angle_max,
            "angle_center": calibration.angle_center,
            "speed": calibration.speed,
        }

    def get_all_calibrations(self) -> dict[int, ServoCalibration]:
        """Get all stored calibrations.

        Returns:
            Dict mapping pin numbers to ServoCalibration objects
        """
        return {pin: self.get_calibration(pin) for pin in self._data.keys()}

    def remove_calibration(self, pin: int) -> bool:
        """Remove calibration for a specific pin.

        Args:
            pin: GPIO pin number

        Returns:
            True if removed, False if not found
        """
        if pin in self._data:
            del self._data[pin]
            return True
        return False

    def clear(self):
        """Clear all calibrations (does not save automatically)."""
        self._data = {}
