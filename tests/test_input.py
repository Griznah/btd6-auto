"""
Unit tests for input.py utilities.
Covers cursor_resting_spot edge cases and expected behavior.
"""

import pytest
from unittest.mock import patch
from btd6_auto import input


@pytest.mark.parametrize(
    "config_value,expected",
    [
        ([100, 200], (100, 200)),
        ((300, 400), (300, 400)),
        (None, (1035, 900)),
        ("invalid", (1035, 900)),
        ([1], (1035, 900)),
    ],
)
def test_cursor_resting_spot_valid_and_invalid(config_value, expected):
    """
    Test cursor_resting_spot with valid, invalid, and missing config values.
    Should always return a tuple of coordinates, defaulting to (1035, 900) on error.
    """
    with patch(
        "btd6_auto.input.get_vision_config",
        return_value={"cursor_resting_spot": config_value},
    ):
        with patch("pyautogui.moveTo") as mock_move:
            result = input.cursor_resting_spot()
            assert result == expected
            mock_move.assert_called_with(
                expected[0], expected[1], duration=0.1
            )


def test_cursor_resting_spot_exception():
    """
    Test cursor_resting_spot handles exceptions gracefully and returns default.
    """
    with patch(
        "btd6_auto.input.get_vision_config", side_effect=Exception("fail")
    ):
        with patch("pyautogui.moveTo") as mock_move:
            result = input.cursor_resting_spot()
            assert result == (1035, 900)
            mock_move.assert_not_called()
