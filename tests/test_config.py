from __future__ import annotations

import pytest

from ninja_core.config import (
    DEFAULT_BLE_NAME,
    MAX_BLE_NAME_BYTES,
    load_config,
    set_robot_name,
)


def test_load_config_defaults_bluetooth_name(tmp_path):
    config_path = tmp_path / "config.json"

    config = load_config(config_path)

    assert config.bluetooth.name == DEFAULT_BLE_NAME


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
