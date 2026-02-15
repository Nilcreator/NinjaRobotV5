"""Unit tests for the ConfigManager.

Tests cover:
- Load/save to file
- Default path resolution
- Missing file handling
- Export/import
- ConfigManager class operations (get/set/load/save)
- Corrupt JSON handling
"""

import json

import pytest

from pi0vl53l0x.config.config_manager import (
    ConfigManager,
    get_default_config_filepath,
    load_config,
    save_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_config(tmp_path):
    """Create a temporary config file with test data."""
    config_file = tmp_path / "test_config.json"
    config = {"offset_mm": 15, "custom_key": "value"}
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f)
    return config_file


@pytest.fixture
def empty_dir(tmp_path):
    """Return a path to a non-existent config file in a temp dir."""
    return tmp_path / "no_config.json"


# ---------------------------------------------------------------------------
# load_config / save_config Function Tests
# ---------------------------------------------------------------------------


class TestLoadSave:
    """Tests for load_config and save_config functions."""

    def test_load_existing_config(self, tmp_config):
        """Should load config from existing JSON file."""
        config = load_config(tmp_config)
        assert config["offset_mm"] == 15
        assert config["custom_key"] == "value"

    def test_load_missing_file(self, empty_dir):
        """Should return empty dict if file does not exist."""
        config = load_config(empty_dir)
        assert config == {}

    def test_load_corrupt_json(self, tmp_path):
        """Should return empty dict on corrupt JSON."""
        corrupt = tmp_path / "corrupt.json"
        corrupt.write_text("not valid json {{{", encoding="utf-8")
        config = load_config(corrupt)
        assert config == {}

    def test_save_creates_file(self, tmp_path):
        """save_config should create the file."""
        filepath = tmp_path / "new_config.json"
        save_config(filepath, {"offset_mm": 42})
        assert filepath.exists()

        loaded = load_config(filepath)
        assert loaded["offset_mm"] == 42

    def test_save_creates_parent_dirs(self, tmp_path):
        """save_config should create parent directories."""
        filepath = tmp_path / "sub" / "dir" / "config.json"
        save_config(filepath, {"offset_mm": 99})
        assert filepath.exists()

    def test_save_default_config(self, tmp_path):
        """save_config with no config should save defaults."""
        filepath = tmp_path / "default.json"
        save_config(filepath)
        loaded = load_config(filepath)
        assert loaded["offset_mm"] == 0

    def test_load_accepts_string_path(self, tmp_config):
        """load_config should accept string path."""
        config = load_config(str(tmp_config))
        assert config["offset_mm"] == 15


# ---------------------------------------------------------------------------
# Default Path Tests
# ---------------------------------------------------------------------------


class TestDefaultPath:
    """Tests for default path resolution."""

    def test_default_path_is_project_relative(self):
        """Default config path should be relative to the module."""
        path = get_default_config_filepath()
        assert path.name == "vl53l0x.json"
        assert "config" in str(path.parent)


# ---------------------------------------------------------------------------
# ConfigManager Class Tests
# ---------------------------------------------------------------------------


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_init_loads_config(self, tmp_config):
        """ConfigManager should load config on init."""
        mgr = ConfigManager(tmp_config)
        assert mgr.get("offset_mm") == 15

    def test_init_missing_file(self, empty_dir):
        """ConfigManager should handle missing file gracefully."""
        mgr = ConfigManager(empty_dir)
        assert mgr.config == {}

    def test_get_with_default(self, empty_dir):
        """get() should return default for missing keys."""
        mgr = ConfigManager(empty_dir)
        assert mgr.get("nonexistent", 42) == 42

    def test_set_and_save(self, tmp_path):
        """set() + save() should persist config."""
        filepath = tmp_path / "mgr_config.json"
        mgr = ConfigManager(filepath)
        mgr.set("offset_mm", 25)
        mgr.save()

        # Load fresh to verify persistence
        mgr2 = ConfigManager(filepath)
        assert mgr2.get("offset_mm") == 25

    def test_path_property(self, tmp_config):
        """path property should return the config file path."""
        mgr = ConfigManager(tmp_config)
        assert mgr.path == tmp_config

    def test_export_config(self, tmp_config, tmp_path):
        """export_config should write config to a different file."""
        mgr = ConfigManager(tmp_config)
        export_path = tmp_path / "exported.json"
        mgr.export_config(export_path)

        exported = load_config(export_path)
        assert exported["offset_mm"] == 15

    def test_import_config(self, tmp_config, tmp_path):
        """import_config should load config from another file."""
        # Create a file to import
        import_file = tmp_path / "import.json"
        save_config(import_file, {"offset_mm": 77})

        # Start with a different config
        mgr = ConfigManager(tmp_config)
        assert mgr.get("offset_mm") == 15

        # Import overwrites
        mgr.import_config(import_file)
        assert mgr.get("offset_mm") == 77

    def test_reload(self, tmp_path):
        """load() should re-read config from disk."""
        filepath = tmp_path / "reload.json"
        save_config(filepath, {"offset_mm": 10})

        mgr = ConfigManager(filepath)
        assert mgr.get("offset_mm") == 10

        # Modify file externally
        save_config(filepath, {"offset_mm": 50})

        # Reload
        mgr.load()
        assert mgr.get("offset_mm") == 50
