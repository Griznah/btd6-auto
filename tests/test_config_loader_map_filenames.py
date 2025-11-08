import pytest
from btd6_auto.config_loader import ConfigLoader

# Test data
EXISTING_MAPS = [
    ("Pat's Pond", "pats_pond.json"),
    ("X Factor", "x_factor.json"),
]

NON_EXISTENT_MAP = "Nonexistent Map"

def test_get_map_filename_success():
    for display_name, expected_filename in EXISTING_MAPS:
        filename = ConfigLoader.get_map_filename(display_name)
        assert filename == expected_filename


def test_get_map_filename_failure():
    with pytest.raises(KeyError):
        ConfigLoader.get_map_filename(NON_EXISTENT_MAP)


def test_load_map_config_success():
    for display_name, _ in EXISTING_MAPS:
        config = ConfigLoader.load_map_config(display_name)
        assert isinstance(config, dict)
        # The placeholder files have a 'placeholder' key
        assert "placeholder" in config


def test_load_map_config_file_not_found(monkeypatch):
    # Patch get_map_filename to return a file that doesn't exist
    monkeypatch.setattr(
        ConfigLoader, "get_map_filename", lambda _name: "does_not_exist.json"
    )
    with pytest.raises(FileNotFoundError):
        ConfigLoader.load_map_config("Pat's Pond")


def test_load_map_config_key_error():
    with pytest.raises(FileNotFoundError):
        ConfigLoader.load_map_config(NON_EXISTENT_MAP)
