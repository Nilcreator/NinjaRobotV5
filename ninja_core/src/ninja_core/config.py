"""
Centralized configuration management for NinjaRobotV4.

This module defines the data structures for the robot's configuration using Pydantic
and provides functions to load, save, and manage the config file.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field


# --- Data Models for Configuration ---


class ServoCalibration(BaseModel):
    """Stores calibration data for a single servo."""

    min_pulse: int = 500
    center_pulse: int = 1500
    max_pulse: int = 2500
    angle_range: int = 180
    speed: int = 80  # Speed limit percentage (0-100)


class ServosConfig(BaseModel):
    """Configuration for all servos."""

    pins: Dict[str, int] = Field(
        default_factory=dict, description="Mapping of servo names to GPIO pin numbers."
    )
    calibration: Dict[str, ServoCalibration] = Field(
        default_factory=dict,
        description="Calibration data for each servo, keyed by pin number as a string.",
    )


class BuzzerConfig(BaseModel):
    """Configuration for the buzzer."""

    pin: Optional[int] = Field(None, description="The GPIO pin for the buzzer.")


class DisplayConfig(BaseModel):
    """Configuration for the ST7789V display."""

    dc: Optional[int] = Field(14, description="The DC (Data/Command) pin.")
    rst: Optional[int] = Field(15, description="The RST (Reset) pin.")
    blk: Optional[int] = Field(16, description="The BLK (Backlight) pin.")
    rotation: int = Field(90, description="Display rotation in degrees (0, 90, 180, 270).")


class SensorConfig(BaseModel):
    """Placeholder for sensor-related settings."""

    # Future settings: I2C address, offsets, etc.
    pass


class NinjaConfig(BaseModel):
    """The root configuration model for the entire robot."""

    servos: ServosConfig = Field(default_factory=ServosConfig)
    buzzer: BuzzerConfig = Field(default_factory=BuzzerConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    sensors: SensorConfig = Field(default_factory=SensorConfig)
    movements: Dict[str, list] = Field(
        default_factory=dict, description="Named servo movement sequences."
    )
    api_keys: Dict[str, str] = Field(
        default_factory=dict, description="API keys for services like Google Gemini."
    )


# --- Configuration Management Functions ---

CONFIG_FILE_PATH = Path("config.json")


def save_config(config: NinjaConfig, path: Path = CONFIG_FILE_PATH):
    """Saves the configuration object to a JSON file."""
    with open(path, "w") as f:
        json.dump(config.model_dump(), f, indent=4)


def load_config(path: Path = CONFIG_FILE_PATH) -> NinjaConfig:
    """
    Loads the configuration from a JSON file.

    If the file does not exist, it creates a default configuration file.
    """
    if not path.exists():
        print(f"Configuration file not found. Creating default config at '{path}'")
        default_config = NinjaConfig()
        save_config(default_config, path)
        return default_config

    with open(path, "r") as f:
        data = json.load(f)
        return NinjaConfig.model_validate(data)


def import_and_update_config():
    """
    Loads the main config, updates it from hardware files, and saves it.

    If servo.json does not exist, it populates the servo calibration with
    a hardcoded default set.
    """
    config = load_config()
    servo_config_path = Path("servo.json")
    buzzer_config_path = Path("buzzer.json")
    made_changes = False

    # --- Import servo calibration ---
    if servo_config_path.exists():
        print(f"Found servo config at '{servo_config_path}'. Importing...")
        with open(servo_config_path, "r") as f:
            servo_data = json.load(f)

        new_calibs = {}

        if isinstance(servo_data, dict):
            # pi0servo format: {"20": {"pulse_min": 500, ...}, "21": {...}}
            for pin_str, calib_data in servo_data.items():
                try:
                    int(pin_str)  # Validate it's a pin number
                except ValueError:
                    continue  # Skip non-numeric keys like metadata

                # Map pi0servo field names to ninja_core field names
                mapped_data = {
                    "min_pulse": calib_data.get(
                        "min_pulse", calib_data.get("pulse_min", 500)
                    ),
                    "center_pulse": calib_data.get(
                        "center_pulse", calib_data.get("pulse_center", 1500)
                    ),
                    "max_pulse": calib_data.get(
                        "max_pulse", calib_data.get("pulse_max", 2500)
                    ),
                    "speed": calib_data.get("speed", 80),
                }
                new_calibs[pin_str] = ServoCalibration.model_validate(mapped_data)

        elif isinstance(servo_data, list):
            # Legacy list format: [{"pin": 20, "min_pulse": 500, ...}, ...]
            for s in servo_data:
                if s.get("pin") is not None:
                    new_calibs[str(s["pin"])] = ServoCalibration.model_validate(s)

        if new_calibs and config.servos.calibration != new_calibs:
            config.servos.calibration = new_calibs
            made_changes = True
            print(f"...imported calibration for {len(new_calibs)} servos.")
        else:
            print("...servo import complete (no changes detected).")
    else:
        print(
            f"Info: '{servo_config_path}' not found. Applying default servo calibration."
        )
        default_calib = {
            "20": {"min_pulse": 500, "center_pulse": 1500, "max_pulse": 2500},
            "21": {"min_pulse": 500, "center_pulse": 1500, "max_pulse": 2500},
            "22": {"min_pulse": 500, "center_pulse": 1500, "max_pulse": 2500},
            "23": {"min_pulse": 500, "center_pulse": 1500, "max_pulse": 2500},
            "24": {"min_pulse": 500, "center_pulse": 1500, "max_pulse": 2500},
            "25": {"min_pulse": 500, "center_pulse": 1500, "max_pulse": 2500},
            "26": {"min_pulse": 500, "center_pulse": 1500, "max_pulse": 2500},
            "27": {"min_pulse": 500, "center_pulse": 1500, "max_pulse": 2500},
        }
        # Validate and assign the default data
        validated_defaults = {
            k: ServoCalibration.model_validate(v) for k, v in default_calib.items()
        }
        if config.servos.calibration != validated_defaults:
            config.servos.calibration = validated_defaults
            made_changes = True
        print("...default servo calibration applied.")

    # --- Import buzzer pin ---
    if buzzer_config_path.exists():
        with open(buzzer_config_path, "r") as f:
            buzzer_data = json.load(f)

        if "pin" in buzzer_data and config.buzzer.pin != buzzer_data["pin"]:
            print(f"Found buzzer config at '{buzzer_config_path}'. Importing...")
            config.buzzer.pin = buzzer_data["pin"]
            made_changes = True
            print("...buzzer import complete.")
    else:
        print(f"Info: Buzzer config '{buzzer_config_path}' not found. Skipping.")

    # --- Save changes if any were made ---
    if made_changes:
        save_config(config)
        print("\nConfiguration updated and saved to config.json!")
    else:
        print("\nNo configuration changes were detected.")


def set_api_key(service: str, key: str):
    """
    Sets an API key for a specific service and saves the configuration.
    """
    config = load_config()
    config.api_keys[service] = key
    save_config(config)
    print(f"API key for '{service}' has been saved.")
