"""Unit tests for pi0disp.config.config_manager module."""

import json
import os
import tempfile

import pytest

from pi0disp.config.config_manager import DEFAULT_CONFIG, DISPLAY_PROFILES, ConfigManager


class TestConfigManager:
    """Tests for ConfigManager."""

    def setup_method(self):
        """Create a temporary config file for each test."""
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, "display.json")
        self.cm = ConfigManager.__new__(ConfigManager)
        self.cm._config_path = self.config_path
        self.cm._config = {}

    def teardown_method(self):
        """Clean up temporary files."""
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.tmpdir)

    def test_load_defaults_when_no_file(self):
        """Should return defaults when display.json doesn't exist."""
        config = self.cm.load()
        assert config["dc_pin"] == 14
        assert config["rst_pin"] == 15
        assert config["backlight_pin"] == 16
        assert config["width"] == 240
        assert config["height"] == 320

    def test_save_and_load(self):
        """Should persist config to JSON and reload it."""
        self.cm._config = DEFAULT_CONFIG.copy()
        self.cm._config["brightness"] = 75
        self.cm.save()

        # Create a new manager pointing to same file
        cm2 = ConfigManager.__new__(ConfigManager)
        cm2._config_path = self.config_path
        cm2._config = {}
        config = cm2.load()
        assert config["brightness"] == 75

    def test_get(self):
        """get() should return config value or default."""
        self.cm._config = DEFAULT_CONFIG.copy()
        assert self.cm.get("dc_pin") == 14
        assert self.cm.get("nonexistent", "fallback") == "fallback"

    def test_set(self):
        """set() should update value and save."""
        self.cm._config = DEFAULT_CONFIG.copy()
        self.cm.set("brightness", 50)
        assert self.cm._config["brightness"] == 50
        # File should be written
        assert os.path.exists(self.config_path)

    def test_export_config(self):
        """export_config() should write JSON to target path."""
        self.cm._config = DEFAULT_CONFIG.copy()
        export_path = os.path.join(self.tmpdir, "export.json")
        self.cm.export_config(export_path)
        assert os.path.exists(export_path)
        with open(export_path) as f:
            data = json.load(f)
        assert data["dc_pin"] == 14
        os.remove(export_path)

    def test_import_config(self):
        """import_config() should read JSON and save locally."""
        import_path = os.path.join(self.tmpdir, "import.json")
        config = DEFAULT_CONFIG.copy()
        config["brightness"] = 30
        with open(import_path, "w") as f:
            json.dump(config, f)

        result = self.cm.import_config(import_path)
        assert result["brightness"] == 30
        # Should also be saved to our config_path
        assert os.path.exists(self.config_path)
        os.remove(import_path)

    def test_import_nonexistent(self):
        """import_config() should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            self.cm.import_config("/nonexistent/path.json")

    def test_init_config_non_interactive(self):
        """init_config(interactive=False) should create defaults."""
        config = self.cm.init_config(interactive=False)
        assert config["dc_pin"] == 14
        assert config["rst_pin"] == 15
        assert config["backlight_pin"] == 16
        assert config["display_profile"] == "st7789v_2inch8"
        assert os.path.exists(self.config_path)

    def test_display_profiles_valid(self):
        """All display profiles should have required keys."""
        required_keys = {"name", "width", "height", "x_offset", "y_offset", "speed_hz"}
        for key, profile in DISPLAY_PROFILES.items():
            assert required_keys.issubset(
                profile.keys()
            ), f"Profile {key} missing keys"
            assert profile["width"] == 240
            assert profile["height"] == 320

    def test_load_corrupted_json(self):
        """Should fall back to defaults on corrupted JSON."""
        with open(self.config_path, "w") as f:
            f.write("{invalid json")
        config = self.cm.load()
        assert config == DEFAULT_CONFIG
