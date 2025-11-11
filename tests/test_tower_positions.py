import pytest
from btd6_auto.config_loader import get_tower_positions_for_map, ConfigLoader


@pytest.fixture(autouse=True)
def invalidate_config_loader_cache():
    """
    Automatically invalidates the ConfigLoader and get_tower_positions_for_map caches before each test.
    Ensures tests run with fresh configuration data and no cached state.
    """
    ConfigLoader.invalidate_cache()
    get_tower_positions_for_map.cache_clear()


# Use a real map config that exists in the repo for this test
EXISTING_MAP = "Test Map"


def test_get_tower_positions_for_map_success():
    """
    Test that get_tower_positions_for_map returns a non-empty dictionary of positions for a valid map.
    Verifies that keys are strings and values are tuples of length 2.
    """
    positions = get_tower_positions_for_map(EXISTING_MAP)
    assert isinstance(positions, dict)
    assert positions  # Should not be empty
    # Check keys are strings and values are tuples of length 2
    for k, v in positions.items():
        assert isinstance(k, str)
        assert isinstance(v, tuple)
        assert len(v) == 2


# Optionally, add a test for a map with no buy section


def test_get_tower_positions_for_map_empty(monkeypatch):
    """
    Test that get_tower_positions_for_map returns an empty dictionary when the map config is empty.
    Uses monkeypatch to simulate an empty config for a fake map name.
    """
    monkeypatch.setattr(ConfigLoader, "load_map_config", lambda _name: {})
    positions = get_tower_positions_for_map("FakeMap")
    assert positions == {}
