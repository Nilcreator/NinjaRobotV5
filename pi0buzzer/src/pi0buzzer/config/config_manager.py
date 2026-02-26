"""
BuzzerConfigManager — JSON configuration management for pi0buzzer.

Provides structured load/save/validate with error recovery, matching
the pattern used by pi0disp and pi0servo ConfigManagers.

Default config file: ``buzzer.json`` in the current working directory.
"""

import json
import logging
import os
import shutil
from typing import Any, Optional

try:
    from ninja_utils import get_logger
    log = get_logger(__name__)
except ImportError:
    log = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "pin": 17,
    "volume": 128,
}

# Validation constraints
_MIN_PIN = 0
_MAX_PIN = 27
_MIN_VOLUME = 0
_MAX_VOLUME = 255


def get_default_config_filepath() -> str:
    """Return the default config file path (``buzzer.json``)."""
    return os.path.join(os.getcwd(), "buzzer.json")


class BuzzerConfigManager:
    """Manages buzzer configuration stored as JSON.

    Args:
        config_path: Path to the config file. Defaults to ``buzzer.json``
            in the current working directory.

    Example::

        cm = BuzzerConfigManager()
        cm.load()
        print(cm.get_pin())
        cm.set_pin(18)
        cm.save()
    """

    def __init__(self, config_path: Optional[str] = None):
        self.path = config_path or get_default_config_filepath()
        self._config: dict[str, Any] = dict(DEFAULT_CONFIG)

    @property
    def config(self) -> dict[str, Any]:
        """Return a copy of the current configuration."""
        return dict(self._config)

    def load(self) -> dict[str, Any]:
        """Load configuration from the JSON file.

        If the file does not exist or is corrupt, falls back to defaults.

        Returns:
            The loaded (or default) configuration dictionary.
        """
        if not os.path.exists(self.path):
            log.info("Config file not found: %s. Using defaults.", self.path)
            self._config = dict(DEFAULT_CONFIG)
            return self.config

        try:
            with open(self.path, "r") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                log.warning("Invalid config format. Using defaults.")
                self._config = dict(DEFAULT_CONFIG)
                return self.config

            # Merge with defaults (fill missing keys)
            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            self._config = merged
            log.info("Config loaded from %s", self.path)
            return self.config

        except (json.JSONDecodeError, OSError) as e:
            log.error("Failed to load config from %s: %s", self.path, e)
            self._config = dict(DEFAULT_CONFIG)
            return self.config

    def save(self) -> None:
        """Save the current configuration to the JSON file.

        Creates parent directories if they don't exist.
        """
        try:
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            with open(self.path, "w") as f:
                json.dump(self._config, f, indent=2)

            log.info("Config saved to %s", self.path)
        except OSError as e:
            log.error("Failed to save config to %s: %s", self.path, e)

    # ------------------------------------------------------------------
    # Pin management
    # ------------------------------------------------------------------

    def get_pin(self) -> int:
        """Return the configured GPIO pin number."""
        return self._config.get("pin", DEFAULT_CONFIG["pin"])

    def set_pin(self, pin: int) -> None:
        """Set the GPIO pin number.

        Args:
            pin: BCM GPIO pin number (0–27).

        Raises:
            ValueError: If pin is out of valid range.
        """
        if not (_MIN_PIN <= pin <= _MAX_PIN):
            raise ValueError(
                f"Pin must be between {_MIN_PIN} and {_MAX_PIN}, got {pin}"
            )
        self._config["pin"] = pin

    # ------------------------------------------------------------------
    # Volume management
    # ------------------------------------------------------------------

    def get_volume(self) -> int:
        """Return the configured PWM volume (duty cycle 0–255)."""
        return self._config.get("volume", DEFAULT_CONFIG["volume"])

    def set_volume(self, volume: int) -> None:
        """Set the PWM volume (duty cycle).

        Args:
            volume: Value between 0 (silent) and 255 (max).

        Raises:
            ValueError: If volume is out of valid range.
        """
        if not (_MIN_VOLUME <= volume <= _MAX_VOLUME):
            raise ValueError(
                f"Volume must be between {_MIN_VOLUME} and {_MAX_VOLUME}, "
                f"got {volume}"
            )
        self._config["volume"] = volume

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_config(self, path: str) -> None:
        """Export configuration to a file.

        Saves current in-memory config to disk first, then copies to destination.

        Args:
            path: Destination file path.
        """
        try:
            # Save current in-memory state to disk before copying
            self.save()
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            shutil.copy2(self.path, path)
            log.info("Config exported to %s", path)
        except OSError as e:
            log.error("Failed to export config: %s", e)
            raise

    def import_config(self, path: str) -> None:
        """Import configuration from a file.

        Args:
            path: Source file path.

        Raises:
            FileNotFoundError: If the source file doesn't exist.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")

        try:
            with open(path, "r") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("Invalid config format in imported file.")

            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            self._config = merged
            log.info("Config imported from %s", path)
        except (json.JSONDecodeError, OSError) as e:
            log.error("Failed to import config from %s: %s", path, e)
            raise

    # ------------------------------------------------------------------
    # Interactive init
    # ------------------------------------------------------------------

    def init_config(self, pin: int) -> None:
        """Initialize configuration with the given pin and save.

        Args:
            pin: BCM GPIO pin number for the buzzer.
        """
        self.set_pin(pin)
        self.save()
        log.info("Buzzer config initialized: pin=%s", pin)
