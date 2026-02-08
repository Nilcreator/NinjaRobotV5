"""Unit tests for config module."""

import json

import pytest

from pi0servo.config import ConfigManager, get_default_config_path
from pi0servo.core import ServoCalibration


class TestConfigManager:
    """Test ConfigManager class."""

    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a temporary config path."""
        return tmp_path / "test_servo.json"

    @pytest.fixture
    def manager(self, temp_config):
        """Create a ConfigManager with temp path."""
        return ConfigManager(temp_config)

    def test_default_path(self):
        """Default path is relative to package."""
        path = get_default_config_path()
        assert path.name == "servo.json"
        assert path.parent.name == "pi0servo"

    def test_init_with_path(self, temp_config):
        """ConfigManager accepts custom path."""
        mgr = ConfigManager(temp_config)
        assert mgr.config_path == temp_config

    def test_exists_false(self, manager):
        """exists() returns False when file doesn't exist."""
        assert manager.exists() is False

    def test_save_creates_file(self, manager):
        """save() creates config file."""
        cal = ServoCalibration(pulse_center=1550, speed=100)
        manager.set_calibration(20, cal)
        assert manager.save() is True
        assert manager.exists() is True

    def test_load_restores_data(self, manager, temp_config):
        """load() restores saved calibrations."""
        # Save data
        cal = ServoCalibration(pulse_center=1550, speed=100)
        manager.set_calibration(20, cal)
        manager.save()

        # Load in new manager
        manager2 = ConfigManager(temp_config)
        assert manager2.load() is True
        loaded_cal = manager2.get_calibration(20)
        assert loaded_cal.pulse_center == 1550
        assert loaded_cal.speed == 100

    def test_get_calibration_default(self, manager):
        """get_calibration returns safe defaults for unknown pins."""
        cal = manager.get_calibration(99)
        # Safe defaults: all pulses set to center (1500) to prevent unexpected movement
        assert cal.pulse_min == 1500
        assert cal.pulse_max == 1500
        assert cal.speed == 80

    def test_set_and_get_calibration(self, manager):
        """set_calibration stores data correctly."""
        cal = ServoCalibration(
            pulse_min=600,
            pulse_max=2400,
            pulse_center=1500,
            angle_min=-85.0,
            angle_max=85.0,
            angle_center=5.0,
            speed=90,
        )
        manager.set_calibration(20, cal)

        loaded = manager.get_calibration(20)
        assert loaded.pulse_min == 600
        assert loaded.pulse_max == 2400
        assert loaded.angle_center == 5.0
        assert loaded.speed == 90

    def test_get_all_calibrations(self, manager):
        """get_all_calibrations returns all stored data."""
        manager.set_calibration(20, ServoCalibration(speed=100))
        manager.set_calibration(21, ServoCalibration(speed=90))

        all_cals = manager.get_all_calibrations()
        assert len(all_cals) == 2
        assert 20 in all_cals
        assert 21 in all_cals

    def test_remove_calibration(self, manager):
        """remove_calibration deletes pin data."""
        manager.set_calibration(20, ServoCalibration())
        assert manager.remove_calibration(20) is True
        assert manager.remove_calibration(20) is False  # Already removed

    def test_clear(self, manager):
        """clear() removes all calibrations."""
        manager.set_calibration(20, ServoCalibration())
        manager.set_calibration(21, ServoCalibration())
        manager.clear()

        all_cals = manager.get_all_calibrations()
        assert len(all_cals) == 0

    def test_load_invalid_json(self, manager, temp_config):
        """load() handles invalid JSON gracefully."""
        temp_config.write_text("not valid json")
        assert manager.load() is False

    def test_load_missing_file(self, manager):
        """load() returns False for missing file."""
        assert manager.load() is False

    def test_speed_field_persisted(self, manager, temp_config):
        """speed field is correctly persisted and loaded."""
        cal = ServoCalibration(speed=42)
        manager.set_calibration(20, cal)
        manager.save()

        # Read raw JSON to verify
        with open(temp_config) as f:
            data = json.load(f)
        assert data["20"]["speed"] == 42

        # Load and verify
        manager.load()
        assert manager.get_calibration(20).speed == 42
