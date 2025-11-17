"""
Unit tests for monkey_manager.py vision-based error handling and placement logic.
"""

import pytest
from btd6_auto import monkey_manager


@pytest.fixture
def mock_config(monkeypatch):
    monkeypatch.setattr(
        monkey_manager,
        "get_vision_config",
        lambda: {
            "max_attempts": 2,
            "select_threshold": 40.0,
            "place_threshold": 85.0,
            "select_region": [925, 800, 1135, 950],
            "place_region_1": [35, 65, 415, 940],
            "place_region_2": [1260, 60, 1635, 940],
        },
    )


@pytest.fixture
def mock_vision(monkeypatch):
    monkeypatch.setattr(monkey_manager, "retry_action", lambda *a, **kw: True)
    monkeypatch.setattr(
        monkey_manager, "confirm_selection", lambda *a, **kw: (True, 50.0)
    )
    monkeypatch.setattr(
        monkey_manager,
        "verify_placement_change",
        lambda *a, **kw: (True, 90.0),
    )
    monkeypatch.setattr(monkey_manager, "handle_vision_error", lambda: None)


@pytest.fixture
def mock_click(monkeypatch):
    monkeypatch.setattr(monkey_manager, "click", lambda x, y, delay=0.2: None)


@pytest.mark.usefixtures("mock_config", "mock_vision", "mock_click")
def test_place_monkey_success():
    # Should not raise or call error handler
    monkey_manager.place_monkey((100, 200), "q")


@pytest.mark.usefixtures("mock_config", "mock_vision", "mock_click")
def test_place_hero_success():
    # Should not raise or call error handler
    monkey_manager.place_hero((300, 400), "u")


@pytest.mark.usefixtures("mock_config", "mock_click")
def test_place_monkey_failure(monkeypatch):
    monkeypatch.setattr(
        monkey_manager, "retry_action", lambda *a, **kw: False
    )
    called = {}
    monkeypatch.setattr(
        monkey_manager,
        "handle_vision_error",
        lambda: called.setdefault("error", True),
    )
    monkey_manager.place_monkey((100, 200), "q")
    assert called.get("error")


@pytest.mark.usefixtures("mock_config", "mock_click")
def test_place_hero_failure(monkeypatch):
    monkeypatch.setattr(
        monkey_manager, "retry_action", lambda *a, **kw: False
    )
    called = {}
    monkeypatch.setattr(
        monkey_manager,
        "handle_vision_error",
        lambda: called.setdefault("error", True),
    )
    monkey_manager.place_hero((300, 400), "u")
    assert called.get("error")
