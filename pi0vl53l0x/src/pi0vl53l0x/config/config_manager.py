"""Configuration manager for VL53L0X sensor settings.

Provides load/save functionality for sensor configuration (offset_mm,
calibration data) using JSON files. Supports project-relative paths
and export/import for backup.

Backward compatible with the original load_config/save_config functions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)

# Default config file name
CONFIG_FILE_NAME = "vl53l0x.json"

# Default configuration values
DEFAULT_CONFIG: dict[str, Any] = {
    "offset_mm": 0,
}


def get_default_config_filepath() -> Path:
    """Get the default config file path (project-relative).

    Returns config file path relative to this module's directory.
    This ensures portability across different installations.

    Returns:
        Path to the default config file.
    """
    return Path(__file__).parent / CONFIG_FILE_NAME


def load_config(filepath: Path | str | None = None) -> dict[str, Any]:
    """Load configuration from a JSON file.

    If the file does not exist, returns an empty dict.
    This is backward compatible with the original function.

    Args:
        filepath: Path to the config file. Defaults to
            project-relative vl53l0x.json.

    Returns:
        Configuration dictionary.
    """
    if filepath is None:
        filepath = get_default_config_filepath()
    filepath = Path(filepath)

    if not filepath.exists():
        logger.debug("Config file not found: %s — using defaults", filepath)
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = cast(dict[str, Any], json.load(f))
        logger.debug("Loaded config from %s: %s", filepath, config)
        return config
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load config from %s: %s", filepath, exc)
        return {}


def save_config(
    filepath: Path | str | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    """Save configuration to a JSON file.

    Creates parent directories if they don't exist.

    Args:
        filepath: Path to save the config file. Defaults to
            project-relative vl53l0x.json.
        config: Configuration dictionary to save.
    """
    if filepath is None:
        filepath = get_default_config_filepath()
    filepath = Path(filepath)

    if config is None:
        config = DEFAULT_CONFIG.copy()

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    logger.debug("Saved config to %s", filepath)


class ConfigManager:
    """High-level configuration manager for VL53L0X sensor.

    Wraps the load/save functions and provides a convenient
    interface for managing sensor config (offset, calibration).

    Args:
        config_path: Path to the config file. If None,
            uses the project-relative default.
    """

    def __init__(self, config_path: Path | str | None = None) -> None:
        if config_path is None:
            self._path = get_default_config_filepath()
        else:
            self._path = Path(config_path)
        self._config: dict[str, Any] = {}
        self.load()

    @property
    def path(self) -> Path:
        """The config file path."""
        return self._path

    @property
    def config(self) -> dict[str, Any]:
        """The current configuration dictionary."""
        return self._config

    def load(self) -> dict[str, Any]:
        """Load config from file.

        Returns:
            The loaded configuration dictionary.
        """
        self._config = load_config(self._path)
        return self._config

    def save(self) -> None:
        """Save current config to file."""
        save_config(self._path, self._config)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            The configuration value.
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a config value.

        Args:
            key: Configuration key.
            value: Value to set.
        """
        self._config[key] = value

    def export_config(self, export_path: Path | str) -> None:
        """Export current config to a different file (backup).

        Args:
            export_path: Path to export the config to.
        """
        save_config(Path(export_path), self._config)
        logger.info("Config exported to %s", export_path)

    def import_config(self, import_path: Path | str) -> dict[str, Any]:
        """Import config from a file and apply it.

        Args:
            import_path: Path to import config from.

        Returns:
            The imported configuration dictionary.
        """
        self._config = load_config(Path(import_path))
        logger.info("Config imported from %s", import_path)
        return self._config
