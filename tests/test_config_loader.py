import os
import pytest
from btd6_auto import config_loader

TEST_MAP = "Monkey Meadow"

class TestConfigLoader:
    def test_load_global_config(self):
        config = config_loader.ConfigLoader.load_global_config()
        assert isinstance(config, dict)
        assert "automation" in config
        assert "image_recognition" in config
        assert "error_handling" in config

    def test_load_map_config_success(self):
        config = config_loader.ConfigLoader.load_map_config(TEST_MAP)
        assert isinstance(config, dict)
        assert config["map_name"] == TEST_MAP
        assert "hero" in config
        assert "actions" in config

    def test_load_map_config_not_found(self):
        with pytest.raises(FileNotFoundError):
            config_loader.ConfigLoader.load_map_config("Nonexistent Map")

    def test_validate_config_success(self):
        config = config_loader.ConfigLoader.load_map_config(TEST_MAP)
        required = ["map_name", "hero", "actions"]
        assert config_loader.ConfigLoader.validate_config(config, required)

    def test_validate_config_missing_fields(self):
        config = {"map_name": TEST_MAP}
        required = ["map_name", "hero", "actions"]
        with pytest.raises(ValueError):
            config_loader.ConfigLoader.validate_config(config, required)

    def test_windows_path_handling(self):
        # Should not raise, even with case/space differences
        config = config_loader.ConfigLoader.load_map_config("monkey meadow")
        assert config["map_name"].lower() == TEST_MAP.lower()
