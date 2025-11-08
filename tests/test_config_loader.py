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

    def test_cache_invalidation_and_reload(self):
        # Load config to populate cache
        config1 = config_loader.ConfigLoader.load_global_config()
        # Verify cache is populated
        assert config_loader.ConfigLoader._global_config_cache is not None
        # Invalidate cache
        config_loader.ConfigLoader.invalidate_cache()
        # Verify cache is cleared
        assert config_loader.ConfigLoader._global_config_cache is None
        # Load again, should reload from disk
        config2 = config_loader.ConfigLoader.load_global_config()
        # Verify cache is repopulated
        assert config_loader.ConfigLoader._global_config_cache is not None
        assert config1 == config2

    @pytest.mark.parametrize(
        "variant",
        [
            "Monkey Meadow",
            "monkey meadow",
            "MonkeyMeadow",
            "Monkey'Meadow",
            "MONKEY MEADOW",
        ],
    )
    def test_get_map_filename_variations(self, variant):
        filename = config_loader.ConfigLoader.get_map_filename(variant)
        assert filename.lower() == "monkey_meadow.json"

    def test_get_map_filename_missing_map_filenames(self, monkeypatch):
        # Patch load_global_config to return a config without map_filenames
        monkeypatch.setattr(
            config_loader.ConfigLoader,
            "_global_config_cache",
            {"automation": {}, "image_recognition": {}, "error_handling": {}},
        )
        config_loader.ConfigLoader._display_to_filename_cache = None
        with pytest.raises(KeyError):
            config_loader.ConfigLoader.get_map_filename("Monkey Meadow")
