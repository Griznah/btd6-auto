import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_keyboard_and_pyautogui():
    """
    Automatically mocks keyboard and pyautogui functions for all tests.
    This fixture ensures that calls to keyboard and pyautogui do not affect the system
    or require actual user input during test execution. It is applied to all tests by default.
    """
    # Use create=True so patching works even if the attribute does not exist (e.g., when keyboard is mocked)
    with (
        patch("keyboard.send", create=True),
        patch("keyboard.press", create=True),
        patch("keyboard.release", create=True),
        patch("pyautogui.click", create=True),
        patch("pyautogui.moveTo", create=True),
        patch("pyautogui.press", create=True),
        patch("pyautogui.keyDown", create=True),
        patch("pyautogui.keyUp", create=True),
    ):
        yield
