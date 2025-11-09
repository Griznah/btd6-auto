import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_keyboard_and_pyautogui():
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
