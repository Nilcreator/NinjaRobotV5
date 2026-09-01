from __future__ import annotations

import pytest

from ninja_core.config import (
    DEFAULT_BLE_NAME,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_ROBOT_TYPE,
    MAX_BLE_NAME_BYTES,
    build_hardware_configuration,
    build_robot_profile,
    load_config,
    set_gemini_configuration,
    set_robot_name,
    set_robot_type,
)


def test_load_config_defaults_bluetooth_name(tmp_path):
    config_path = tmp_path / "config.json"

    config = load_config(config_path)

    assert config.bluetooth.name == DEFAULT_BLE_NAME
    assert config.robot_type == DEFAULT_ROBOT_TYPE
    assert config.gemini.model == DEFAULT_GEMINI_MODEL


def test_set_gemini_configuration_persists_key_and_normalized_model(tmp_path, capsys):
    config_path = tmp_path / "config.json"

    selected = set_gemini_configuration(
        "  secret-key  ",
        "models/gemini-selected",
        path=config_path,
    )

    config = load_config(config_path)
    assert selected == "gemini-selected"
    assert config.api_keys["gemini"] == "secret-key"
    assert config.gemini.model == "gemini-selected"
    assert "secret-key" not in capsys.readouterr().out


def test_set_gemini_configuration_rejects_blank_key_without_creating_config(tmp_path):
    config_path = tmp_path / "config.json"

    with pytest.raises(ValueError, match="cannot be empty"):
        set_gemini_configuration("   ", "gemini-selected", path=config_path)

    assert config_path.exists() is False


def test_set_robot_name_persists_normalized_name(tmp_path, capsys):
    config_path = tmp_path / "config.json"

    saved_name = set_robot_name("  Classroom   Ninja   01  ", path=config_path)

    assert saved_name == "Classroom Ninja 01"
    assert load_config(config_path).bluetooth.name == "Classroom Ninja 01"
    assert "Restart the NinjaRobot BLE service or web server" in capsys.readouterr().out


def test_set_robot_name_rejects_blank_names(tmp_path):
    config_path = tmp_path / "config.json"

    with pytest.raises(ValueError, match="cannot be empty"):
        set_robot_name("   ", path=config_path)


def test_set_robot_name_rejects_names_that_exceed_ble_limit(tmp_path):
    config_path = tmp_path / "config.json"
    too_long_name = "N" * (MAX_BLE_NAME_BYTES + 1)

    with pytest.raises(ValueError, match="must fit within"):
        set_robot_name(too_long_name, path=config_path)


def test_set_robot_type_persists_normalized_type(tmp_path, capsys):
    config_path = tmp_path / "config.json"

    saved_type = set_robot_type("  Humanoid  ", path=config_path)

    assert saved_type == "humanoid"
    assert load_config(config_path).robot_type == "humanoid"
    assert "Humanoid" in capsys.readouterr().out


def test_set_robot_type_rejects_unknown_type(tmp_path):
    config_path = tmp_path / "config.json"

    with pytest.raises(ValueError, match="Robot type must be one of"):
        set_robot_type("dragon", path=config_path)


def test_build_hardware_configuration_redacts_keys_and_lists_servo_pins(tmp_path):
    config_path = tmp_path / "config.json"
    config = load_config(config_path)
    config.servos.pins = {"left": 12, "right": 13}
    config.servos.calibration = {
        "12": {"min_pulse": 500, "center_pulse": 1500, "max_pulse": 2500},
        "18": {"min_pulse": 600, "center_pulse": 1500, "max_pulse": 2400},
        "99": {"min_pulse": 600, "center_pulse": 1500, "max_pulse": 2400},
    }
    config.api_keys["gemini"] = "SECRET"
    config.gemini.model = "gemini-selected"

    hardware = build_hardware_configuration(config)

    assert hardware["servos"]["gpio_pins"] == [12, 13, 18]
    assert hardware["servos"]["pins"] == {"left": 12, "right": 13}
    assert "api_keys" not in hardware


def test_build_robot_profile_includes_robot_type_and_no_secrets(tmp_path):
    config_path = tmp_path / "config.json"
    config = load_config(config_path)
    config.robot_type = "spider"
    config.api_keys["gemini"] = "SECRET"

    profile = build_robot_profile(config)

    assert profile["robot_type"] == "spider"
    assert profile["robot_type_label"] == "Spider"
    assert profile["service_name"] == DEFAULT_BLE_NAME
    assert "api_keys" not in profile
    assert "gemini" not in profile
    assert "api_keys" not in profile["hardware_configuration"]
