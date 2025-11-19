"""
Unit tests for monkey_manager.py vision-based error handling and placement logic.
"""

import pytest
from btd6_auto import monkey_manager


@pytest.fixture
def mock_config(monkeypatch):
    """
    Mock get_vision_config in monkey_manager to return a fixed vision configuration used by the tests.
    
    The mocked configuration contains:
    - max_attempts: 2
    - select_threshold: 40.0
    - place_threshold: 85.0
    - select_region: [925, 800, 1135, 950]
    - place_region_1: [35, 65, 415, 940]
    - place_region_2: [1260, 60, 1635, 940]
    """
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
    """
    Pytest fixture that stubs monkey_manager vision functions to simulate successful vision outcomes.
    
    Replaces:
    - `retry_action` with a callable that always returns `True`.
    - `confirm_selection` with a callable that returns `(True, 50.0)`.
    - `verify_placement_change` with a callable that returns `(True, 90.0)`.
    - `handle_vision_error` with a no-op callable.
    
    This fixture does not return a value; it mutates the monkey_manager module via the provided `monkeypatch`.
    """
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
    """
    Patch monkey_manager.move_and_click to a no-op for tests.
    
    Parameters:
        monkeypatch: pytest's monkeypatch fixture used to replace the move_and_click function with a lambda that does nothing.
    """
    monkeypatch.setattr(
        monkey_manager, "move_and_click", lambda x, y, delay=0.2: None
    )


@pytest.mark.usefixtures("mock_config", "mock_vision", "mock_click")
def test_place_monkey_success():
    """
    Test successful placement of a monkey.
    Scenario: Vision and click actions succeed, no error handler is called.
    Expected outcome: No exceptions, no error handling triggered.
    """
    monkey_manager.place_monkey((100, 200), "q")


@pytest.mark.usefixtures("mock_config", "mock_vision", "mock_click")
def test_place_hero_success():
    """
    Test successful placement of a hero.
    Scenario: Vision and click actions succeed, no error handler is called.
    Expected outcome: No exceptions, no error handling triggered.
    """
    monkey_manager.place_hero((300, 400), "u")


@pytest.mark.usefixtures("mock_config", "mock_click")
def test_place_monkey_failure(monkeypatch):
    """
    Test monkey placement failure triggers error handler.
    Scenario: Vision retry fails, error handler should be called.
    Expected outcome: Error handler is triggered and sets 'error' flag.
    """
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
    """
    Test hero placement failure triggers error handler.
    Scenario: Vision retry fails, error handler should be called.
    Expected outcome: Error handler is triggered and sets 'error' flag.
    """
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


@pytest.mark.usefixtures("mock_config", "mock_click")
def test_place_monkey_targeting_failure(monkeypatch):
    """
    Test monkey placement targeting failure triggers error handler.
    Scenario: retry_action succeeds, but try_targeting_success fails, error handler should be called.
    Expected outcome: Error handler is triggered and sets 'error' flag.
    """
    monkeypatch.setattr(monkey_manager, "retry_action", lambda *a, **kw: True)
    monkeypatch.setattr(
        monkey_manager, "try_targeting_success", lambda *a, **kw: False
    )
    monkeypatch.setattr(monkey_manager, "cursor_resting_spot", lambda: None)
    called = {}
    monkeypatch.setattr(
        monkey_manager,
        "handle_vision_error",
        lambda: called.setdefault("error", True),
    )
    import sys

    class MockKeyboard:
        def send(self, *a, **kw):
            pass

    sys.modules["keyboard"] = MockKeyboard()
    monkey_manager.place_monkey((100, 200), "q")
    assert called.get("error")


@pytest.mark.usefixtures("mock_config", "mock_click")
def test_place_hero_targeting_failure(monkeypatch):
    """
    Test hero placement targeting failure triggers error handler.
    Scenario: retry_action succeeds, but try_targeting_success fails, error handler should be called.
    Expected outcome: Error handler is triggered and sets 'error' flag.
    """
    monkeypatch.setattr(monkey_manager, "retry_action", lambda *a, **kw: True)
    monkeypatch.setattr(
        monkey_manager, "try_targeting_success", lambda *a, **kw: False
    )
    monkeypatch.setattr(monkey_manager, "cursor_resting_spot", lambda: None)
    called = {}
    monkeypatch.setattr(
        monkey_manager,
        "handle_vision_error",
        lambda: called.setdefault("error", True),
    )
    import sys

    class MockKeyboard:
        def press(self, *a, **kw):
            pass

        def release(self, *a, **kw):
            pass

    sys.modules["keyboard"] = MockKeyboard()
    monkey_manager.place_hero((300, 400), "u")
    assert called.get("error")
