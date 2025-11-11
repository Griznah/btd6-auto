import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_keyboard_and_pyautogui():
    """
    Automatically mocks keyboard and pyautogui functions for all tests.
    This fixture ensures that calls to keyboard and pyautogui do not affect the system
    or require actual user input during test execution. It is applied to all tests by default.
    """
    with (
        patch("keyboard.send"),
        patch("keyboard.press"),
        patch("keyboard.release"),
        patch("pyautogui.click"),
        patch("pyautogui.moveTo"),
        patch("pyautogui.press"),
        patch("pyautogui.keyDown"),
        patch("pyautogui.keyUp"),
    ):
        yield
