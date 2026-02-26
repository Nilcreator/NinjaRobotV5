"""Unit tests for pi0buzzer.config.config_manager.BuzzerConfigManager."""

import json
import os

import pytest

from pi0buzzer.config.config_manager import BuzzerConfigManager, DEFAULT_CONFIG


class TestConfigManagerLoad:
    """Test load() method."""

    def test_load_defaults_when_no_file(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cfg = cm.load()
        assert cfg["pin"] == DEFAULT_CONFIG["pin"]
        assert cfg["volume"] == DEFAULT_CONFIG["volume"]

    def test_load_from_file(self, tmp_config):
        with open(tmp_config, "w") as f:
            json.dump({"pin": 18, "volume": 64}, f)

        cm = BuzzerConfigManager(tmp_config)
        cfg = cm.load()
        assert cfg["pin"] == 18
        assert cfg["volume"] == 64

    def test_load_merges_with_defaults(self, tmp_config):
        """Missing keys should be filled from defaults."""
        with open(tmp_config, "w") as f:
            json.dump({"pin": 22}, f)

        cm = BuzzerConfigManager(tmp_config)
        cfg = cm.load()
        assert cfg["pin"] == 22
        assert cfg["volume"] == DEFAULT_CONFIG["volume"]

    def test_load_handles_corrupt_json(self, tmp_config):
        with open(tmp_config, "w") as f:
            f.write("not valid json!!!")

        cm = BuzzerConfigManager(tmp_config)
        cfg = cm.load()
        # Should fall back to defaults
        assert cfg["pin"] == DEFAULT_CONFIG["pin"]

    def test_load_handles_non_dict_json(self, tmp_config):
        with open(tmp_config, "w") as f:
            json.dump([1, 2, 3], f)

        cm = BuzzerConfigManager(tmp_config)
        cfg = cm.load()
        assert cfg["pin"] == DEFAULT_CONFIG["pin"]


class TestConfigManagerSave:
    """Test save() method."""

    def test_save_creates_file(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        cm.save()
        assert os.path.exists(tmp_config)

    def test_save_writes_correct_content(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        cm.set_pin(22)
        cm.save()

        with open(tmp_config) as f:
            data = json.load(f)
        assert data["pin"] == 22

    def test_save_roundtrip(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        cm.set_pin(23)
        cm.set_volume(100)
        cm.save()

        cm2 = BuzzerConfigManager(tmp_config)
        cfg = cm2.load()
        assert cfg["pin"] == 23
        assert cfg["volume"] == 100


class TestConfigManagerPin:
    """Test pin management."""

    def test_get_pin_default(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        assert cm.get_pin() == DEFAULT_CONFIG["pin"]

    def test_set_pin_valid(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        cm.set_pin(22)
        assert cm.get_pin() == 22

    def test_set_pin_boundary(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        cm.set_pin(0)
        assert cm.get_pin() == 0
        cm.set_pin(27)
        assert cm.get_pin() == 27

    def test_set_pin_invalid_low(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        with pytest.raises(ValueError):
            cm.set_pin(-1)

    def test_set_pin_invalid_high(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        with pytest.raises(ValueError):
            cm.set_pin(28)


class TestConfigManagerVolume:
    """Test volume management."""

    def test_get_volume_default(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        assert cm.get_volume() == DEFAULT_CONFIG["volume"]

    def test_set_volume_valid(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        cm.set_volume(200)
        assert cm.get_volume() == 200

    def test_set_volume_boundaries(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        cm.set_volume(0)
        assert cm.get_volume() == 0
        cm.set_volume(255)
        assert cm.get_volume() == 255

    def test_set_volume_invalid(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        with pytest.raises(ValueError):
            cm.set_volume(-1)
        with pytest.raises(ValueError):
            cm.set_volume(256)


class TestConfigManagerExportImport:
    """Test export/import functionality."""

    def test_export_import_roundtrip(self, tmp_config, tmp_path):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        cm.set_pin(22)
        cm.set_volume(100)
        cm.save()

        export_path = str(tmp_path / "exported.json")
        cm.export_config(export_path)

        cm2 = BuzzerConfigManager(str(tmp_path / "new_config.json"))
        cm2.import_config(export_path)
        assert cm2.get_pin() == 22
        assert cm2.get_volume() == 100

    def test_import_nonexistent_file(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.load()
        with pytest.raises(FileNotFoundError):
            cm.import_config("/nonexistent/path.json")


class TestConfigManagerInitConfig:
    """Test init_config() method."""

    def test_init_config(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        cm.init_config(pin=22)
        assert cm.get_pin() == 22
        assert os.path.exists(tmp_config)

    def test_init_config_invalid_pin(self, tmp_config):
        cm = BuzzerConfigManager(tmp_config)
        with pytest.raises(ValueError):
            cm.init_config(pin=99)
