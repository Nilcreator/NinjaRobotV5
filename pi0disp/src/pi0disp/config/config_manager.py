"""
Configuration manager for pi0disp display settings.

Manages display pin assignments, display profile, and rendering settings
via a project-relative display.json file.
"""

import json
import os
from typing import Any

# Display profile definitions
DISPLAY_PROFILES = {
    "st7789v_2inch8": {
        "name": "ST7789V 2.8-inch IPS TFT 240×320",
        "width": 240,
        "height": 320,
        "x_offset": 0,
        "y_offset": 0,
        "speed_hz": 32_000_000,
    },
    "waveshare_2inch": {
        "name": "Waveshare 2.0-inch IPS LCD 240×320",
        "width": 240,
        "height": 320,
        "x_offset": 0,
        "y_offset": 0,
        "speed_hz": 32_000_000,
    },
}

# Default pin assignments (BCM GPIO)
DEFAULT_PINS = {
    "dc_pin": 14,
    "rst_pin": 15,
    "backlight_pin": 16,
}

# Default configuration
DEFAULT_CONFIG = {
    "display_profile": "st7789v_2inch8",
    "dc_pin": DEFAULT_PINS["dc_pin"],
    "rst_pin": DEFAULT_PINS["rst_pin"],
    "backlight_pin": DEFAULT_PINS["backlight_pin"],
    "width": 240,
    "height": 320,
    "rotation": 90,
    "brightness": 100,
    "spi_speed_mhz": 32,
}


class ConfigManager:
    """Manages display configuration persistence via display.json.

    Follows the same pattern as pi0servo.ConfigManager.
    """

    def __init__(self, config_file: str = "display.json") -> None:
        """Initialize the config manager.

        Args:
            config_file: Path to the configuration file.
                         Resolved relative to this file's directory.
        """
        # Resolve relative to the pi0disp package root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )))
        self._config_path = os.path.join(base_dir, config_file)
        self._config: dict = {}

    @property
    def config_path(self) -> str:
        """Path to the configuration file."""
        return self._config_path

    def load(self) -> dict:
        """Load configuration from display.json.

        Returns:
            The loaded config dict. Falls back to defaults if file not found.
        """
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r") as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()
        return self._config

    def save(self) -> None:
        """Save current configuration to display.json."""
        with open(self._config_path, "w") as f:
            json.dump(self._config, f, indent=4)
            f.write("\n")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            The configuration value.
        """
        if not self._config:
            self.load()
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save.

        Args:
            key: Configuration key.
            value: Value to set.
        """
        if not self._config:
            self.load()
        self._config[key] = value
        self.save()

    def export_config(self, path: str) -> None:
        """Export configuration to a file.

        Args:
            path: Target file path.
        """
        if not self._config:
            self.load()
        with open(path, "w") as f:
            json.dump(self._config, f, indent=4)
            f.write("\n")

    def import_config(self, path: str) -> dict:
        """Import configuration from a file.

        Args:
            path: Source file path.

        Returns:
            The imported config dict.

        Raises:
            FileNotFoundError: If source file does not exist.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r") as f:
            self._config = json.load(f)
        self.save()
        return self._config

    def init_config(self, interactive: bool = True) -> dict:
        """Initialize display configuration.

        When interactive=True, prompts the user step by step:
          1. Select display profile (ST7789V 2.8-inch / Waveshare 2.0-inch)
          2. Set DC pin (default: 14)
          3. Set RST pin (default: 15)
          4. Set BLK pin (default: 16)
          5. Set rotation (default: 90)
          6. Set brightness (default: 100)

        When interactive=False, creates display.json with all defaults.

        Args:
            interactive: If True, prompt the user. If False, use defaults.

        Returns:
            The configuration dict.
        """
        if not interactive:
            self._config = DEFAULT_CONFIG.copy()
            self.save()
            return self._config

        # --- Interactive Setup ---
        print()
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║               pi0disp — Display Initialization               ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print()

        # 1. Select display profile
        print("Select your display module:")
        profiles = list(DISPLAY_PROFILES.items())
        for i, (key, profile) in enumerate(profiles, 1):
            print(f"  {i}. {profile['name']}")

        choice = _prompt_int("Choice", 1, 1, len(profiles))
        profile_key = profiles[choice - 1][0]
        profile = DISPLAY_PROFILES[profile_key]

        # 2. Pin configuration
        print()
        print("--- Pin Configuration (BCM GPIO numbers) ---")
        print()
        dc_pin = _prompt_int("  DC pin", DEFAULT_PINS["dc_pin"], 0, 27)
        rst_pin = _prompt_int("  RST pin", DEFAULT_PINS["rst_pin"], 0, 27)
        blk_pin = _prompt_int("  BLK pin", DEFAULT_PINS["backlight_pin"], 0, 27)

        # 3. Display settings
        print()
        print("--- Display Settings ---")
        print()
        rotation = _prompt_choice(
            "  Rotation (0/90/180/270)", 90, [0, 90, 180, 270]
        )
        brightness = _prompt_int("  Brightness (0-100%)", 100, 0, 100)

        # Build config
        self._config = {
            "display_profile": profile_key,
            "dc_pin": dc_pin,
            "rst_pin": rst_pin,
            "backlight_pin": blk_pin,
            "width": profile["width"],
            "height": profile["height"],
            "rotation": rotation,
            "brightness": brightness,
            "spi_speed_mhz": profile["speed_hz"] // 1_000_000,
        }

        self.save()

        # Summary
        print()
        print(f"✅ Configuration saved to {os.path.basename(self._config_path)}")
        print()
        print(f"  Display:    {profile['name']}")
        print(f"  Resolution: {profile['width']} × {profile['height']}")
        print(f"  Pins:       DC={dc_pin}, RST={rst_pin}, BLK={blk_pin}")
        print(f"  Rotation:   {rotation}°")
        print(f"  Brightness: {brightness}%")
        print()

        return self._config


def _prompt_int(
    label: str, default: int, min_val: int, max_val: int
) -> int:
    """Prompt for an integer value with validation."""
    while True:
        try:
            raw = input(f"{label} [{default}]: ").strip()
            if not raw:
                return default
            value = int(raw)
            if min_val <= value <= max_val:
                return value
            print(f"  ⚠️  Must be between {min_val} and {max_val}")
        except ValueError:
            print("  ⚠️  Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            print()
            return default


def _prompt_choice(label: str, default: int, choices: list) -> int:
    """Prompt for a value from a list of choices."""
    while True:
        try:
            choices_str = "/".join(str(c) for c in choices)
            raw = input(f"{label} [{default}]: ").strip()
            if not raw:
                return default
            value = int(raw)
            if value in choices:
                return value
            print(f"  ⚠️  Must be one of: {choices_str}")
        except ValueError:
            print("  ⚠️  Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            print()
            return default
