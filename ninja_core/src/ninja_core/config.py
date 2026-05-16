"""
Centralized configuration management for NinjaRobotV4.

This module defines the data structures for the robot's configuration using Pydantic
and provides functions to load, save, and manage the config file.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


DEFAULT_BLE_NAME = "NinjaRobot"
MAX_BLE_NAME_BYTES = 29
ROBOT_TYPE_OPTIONS = ("tire", "humanoid", "spider")
ROBOT_TYPE_LABELS = {
    "tire": "Tire",
    "humanoid": "Humanoid",
    "spider": "Spider",
}
DEFAULT_ROBOT_TYPE = "tire"
ROBOT_PROFILE_VERSION = "ninja-robot-profile-v1"
MAX_BCM_GPIO_PIN = 27


def normalize_ble_name(name: str) -> str:
    """Normalize and validate the BLE advertising name."""
    normalized = " ".join(name.strip().split())
    if not normalized:
        raise ValueError("Robot name cannot be empty.")

    encoded = normalized.encode("utf-8")
    if len(encoded) > MAX_BLE_NAME_BYTES:
        raise ValueError(
            f"Robot name must fit within {MAX_BLE_NAME_BYTES} UTF-8 bytes for BLE advertising."
        )

    return normalized


def normalize_robot_type(robot_type: str | None) -> str:
    """Normalize and validate the robot type stored in config.json."""
    normalized = (robot_type or DEFAULT_ROBOT_TYPE).strip().lower()
    if normalized not in ROBOT_TYPE_OPTIONS:
        options = ", ".join(ROBOT_TYPE_OPTIONS)
        raise ValueError(f"Robot type must be one of: {options}.")
    return normalized


def get_robot_type_options() -> tuple[tuple[str, str], ...]:
    """Return supported robot types as (value, label) pairs."""
    return tuple((value, ROBOT_TYPE_LABELS[value]) for value in ROBOT_TYPE_OPTIONS)


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
    """Configuration for the ST7789V display.

    Pin defaults are None to force explicit configuration via
    'ninja_core config import' (reads pi0disp/display.json).
    """

    dc: Optional[int] = Field(None, description="The DC (Data/Command) GPIO pin.")
    rst: Optional[int] = Field(None, description="The RST (Reset) GPIO pin.")
    blk: Optional[int] = Field(None, description="The BLK (Backlight) GPIO pin.")
    rotation: int = Field(90, description="Display rotation in degrees (0, 90, 180, 270).")


class SensorConfig(BaseModel):
    """Placeholder for sensor-related settings."""

    # Future settings: I2C address, offsets, etc.
    pass


class BluetoothConfig(BaseModel):
    """Configuration for Bluetooth Low Energy advertising."""

    name: str = Field(
        default=DEFAULT_BLE_NAME,
        description="Bluetooth advertising name shown during robot discovery.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_ble_name(value)


class NinjaConfig(BaseModel):
    """The root configuration model for the entire robot."""

    servos: ServosConfig = Field(default_factory=ServosConfig)
    buzzer: BuzzerConfig = Field(default_factory=BuzzerConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    bluetooth: BluetoothConfig = Field(default_factory=BluetoothConfig)
    robot_type: str = Field(
        default=DEFAULT_ROBOT_TYPE,
        description="Canonical NinjaRobot type: tire, humanoid, or spider.",
    )
    sensors: SensorConfig = Field(default_factory=SensorConfig)
    movements: Dict[str, list] = Field(
        default_factory=dict, description="Named servo movement sequences."
    )
    api_keys: Dict[str, str] = Field(
        default_factory=dict, description="API keys for services like Google Gemini."
    )

    @field_validator("robot_type")
    @classmethod
    def validate_robot_type(cls, value: str) -> str:
        return normalize_robot_type(value)


# --- Configuration Management Functions ---

CONFIG_FILE_PATH = Path("config.json")


def save_config(config: NinjaConfig, path: Path = CONFIG_FILE_PATH):
    """Saves the configuration object to a JSON file."""
    with open(path, "w") as f:
        json.dump(config.model_dump(), f, indent=4)


def _normalize_gpio_pin(value: Any) -> int | None:
    try:
        pin = int(value)
    except (TypeError, ValueError):
        return None

    if pin < 0 or pin > MAX_BCM_GPIO_PIN:
        return None
    return pin


def _model_dump_public(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    return value


def build_hardware_configuration(config: NinjaConfig) -> dict[str, Any]:
    """Build a non-secret hardware configuration snapshot for IDE clients."""
    servo_pin_values = [
        _normalize_gpio_pin(pin)
        for pin in config.servos.pins.values()
    ]
    servo_calibration_pins = [
        _normalize_gpio_pin(pin)
        for pin in config.servos.calibration.keys()
    ]
    gpio_pins = sorted(
        {
            pin
            for pin in [*servo_pin_values, *servo_calibration_pins]
            if pin is not None
        }
    )

    return {
        "servos": {
            "gpio_pins": gpio_pins,
            "pins": dict(config.servos.pins),
            "calibration": {
                str(pin): _model_dump_public(calibration)
                for pin, calibration in config.servos.calibration.items()
            },
        },
        "buzzer": _model_dump_public(config.buzzer),
        "display": _model_dump_public(config.display),
        "sensors": _model_dump_public(config.sensors),
    }


def build_robot_profile(config: NinjaConfig) -> dict[str, Any]:
    """Build the sanitized robot profile shared over BLE/web status."""
    robot_type = normalize_robot_type(config.robot_type)
    return {
        "robot_profile_version": ROBOT_PROFILE_VERSION,
        "name": config.bluetooth.name,
        "service_name": config.bluetooth.name,
        "display_name": config.bluetooth.name,
        "ble_name": config.bluetooth.name,
        "robot_type": robot_type,
        "robot_type_label": ROBOT_TYPE_LABELS[robot_type],
        "hardware_configuration": build_hardware_configuration(config),
    }


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


def set_robot_type(robot_type: str, path: Path = CONFIG_FILE_PATH) -> str:
    """Persist the configured NinjaRobot type."""
    normalized = normalize_robot_type(robot_type)
    config = load_config(path)
    config.robot_type = normalized
    save_config(config, path)
    print(f"NinjaRobot type set to {ROBOT_TYPE_LABELS[normalized]} ({normalized}).")
    return normalized


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

    # --- Import display settings ---
    display_config_path = Path("pi0disp") / "display.json"
    if display_config_path.exists():
        print(f"Found display config at '{display_config_path}'. Importing...")
        with open(display_config_path, "r") as f:
            disp_data = json.load(f)

        changed = False
        if "dc_pin" in disp_data and config.display.dc != disp_data["dc_pin"]:
            config.display.dc = disp_data["dc_pin"]
            changed = True
        if "rst_pin" in disp_data and config.display.rst != disp_data["rst_pin"]:
            config.display.rst = disp_data["rst_pin"]
            changed = True
        if "backlight_pin" in disp_data and config.display.blk != disp_data["backlight_pin"]:
            config.display.blk = disp_data["backlight_pin"]
            changed = True
        if "rotation" in disp_data and config.display.rotation != disp_data["rotation"]:
            config.display.rotation = disp_data["rotation"]
            changed = True

        if changed:
            made_changes = True
            print(
                f"...imported display pins: DC={config.display.dc}, "
                f"RST={config.display.rst}, BLK={config.display.blk}, "
                f"rotation={config.display.rotation}"
            )
        else:
            print("...display import complete (no changes detected).")
    else:
        print(
            f"Info: Display config '{display_config_path}' not found. Skipping.\n"
            f"  Tip: Run 'uv run pi0disp init' first to create display.json."
        )

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


def set_robot_name(name: str, path: Path = CONFIG_FILE_PATH) -> str:
    """
    Sets the BLE advertising name and saves the configuration.
    """
    normalized_name = normalize_ble_name(name)
    config = load_config(path)
    config.bluetooth.name = normalized_name
    save_config(config, path)
    print(
        f"Robot BLE name set to '{normalized_name}'. Restart the NinjaRobot BLE service "
        "or web server to apply the new advertising name."
    )
    return normalized_name
