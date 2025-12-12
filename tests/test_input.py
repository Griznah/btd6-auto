"""
Unit tests for input.py utilities.
Covers cursor_resting_spot edge cases and unselect() function behavior.
Tests keyboard input simulation, error handling, and timing controls.
"""

import pytest
from unittest.mock import patch, call
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


def test_unselect_default_delay():
    """
    Test unselect() with default delay parameter.
    Should call keyboard.send('esc') exactly once and time.sleep with default delay.
    """
    with patch("keyboard.send") as mock_keyboard_send, \
         patch("time.sleep") as mock_sleep:

        input.unselect()

        # Verify keyboard.send is called exactly once with 'esc'
        mock_keyboard_send.assert_called_once_with('esc')

        # Verify time.sleep is called exactly once with default delay of 0.2
        mock_sleep.assert_called_once_with(0.2)


def test_unselect_custom_delay():
    """
    Test unselect() with custom delay parameter.
    Should call keyboard.send('esc') exactly once and time.sleep with custom delay.
    """
    custom_delay = 0.5

    with patch("keyboard.send") as mock_keyboard_send, \
         patch("time.sleep") as mock_sleep:

        input.unselect(delay=custom_delay)

        # Verify keyboard.send is called exactly once with 'esc'
        mock_keyboard_send.assert_called_once_with('esc')

        # Verify time.sleep is called exactly once with custom delay
        mock_sleep.assert_called_once_with(custom_delay)


def test_unselect_keyboard_exception():
    """
    Test unselect() handles keyboard module exceptions gracefully.
    Should catch the exception and log it without crashing.
    """
    with patch("keyboard.send", side_effect=Exception("Keyboard error")) as mock_keyboard_send, \
         patch("time.sleep") as mock_sleep, \
         patch("logging.exception") as mock_logging:

        input.unselect()

        # Verify keyboard.send was attempted
        mock_keyboard_send.assert_called_once_with('esc')

        # Verify time.sleep is NOT called when keyboard.send fails (exception stops execution)
        mock_sleep.assert_not_called()

        # Verify exception was logged
        mock_logging.assert_called_once_with("Failed to press ESC key for unselect")


def test_unselect_time_sleep_exception():
    """
    Test unselect() handles time.sleep exceptions gracefully.
    Should catch the exception and log it without crashing.
    """
    with patch("keyboard.send") as mock_keyboard_send, \
         patch("time.sleep", side_effect=Exception("Sleep interrupted")) as mock_sleep, \
         patch("logging.exception") as mock_logging:

        input.unselect(delay=0.3)

        # Verify keyboard.send was called successfully
        mock_keyboard_send.assert_called_once_with('esc')

        # Verify time.sleep was attempted with correct delay
        mock_sleep.assert_called_once_with(0.3)

        # Verify exception was logged
        mock_logging.assert_called_once_with("Failed to press ESC key for unselect")


def test_unselect_keyboard_import_error():
    """
    Test unselect() handles keyboard import error gracefully.
    This tests the case where the keyboard module fails to import.
    """
    with patch("builtins.__import__", side_effect=ImportError("No keyboard module")) as mock_import, \
         patch("logging.exception") as mock_logging:

        input.unselect()

        # Verify exception was logged
        mock_logging.assert_called_once_with("Failed to press ESC key for unselect")


def test_unselect_with_zero_delay():
    """
    Test unselect() with zero delay parameter.
    Should handle edge case of delay=0 correctly.
    """
    with patch("keyboard.send") as mock_keyboard_send, \
         patch("time.sleep") as mock_sleep:

        input.unselect(delay=0.0)

        # Verify keyboard.send is called exactly once with 'esc'
        mock_keyboard_send.assert_called_once_with('esc')

        # Verify time.sleep is called exactly once with zero delay
        mock_sleep.assert_called_once_with(0.0)


def test_unselect_multiple_calls():
    """
    Test unselect() called multiple times to ensure proper isolation between calls.
    Each call should be independent and use the correct delay.
    """
    with patch("keyboard.send") as mock_keyboard_send, \
         patch("time.sleep") as mock_sleep:

        # First call with default delay
        input.unselect()

        # Second call with custom delay
        input.unselect(delay=0.7)

        # Verify keyboard.send was called exactly twice
        assert mock_keyboard_send.call_count == 2
        mock_keyboard_send.assert_has_calls([call('esc'), call('esc')])

        # Verify time.sleep was called exactly twice with correct delays
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(0.2), call(0.7)])
