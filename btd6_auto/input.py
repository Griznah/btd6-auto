"""
Input automation utilities for BTD6 automation bot.
Centralizes mouse/keyboard actions and error handling.
"""

import pyautogui
import time
import logging
import os  # For hard termination
from pynput import keyboard as pynput_keyboard

# Import shared state for kill switch
from .state import SharedState
from .config_utils import get_vision_config


def killswitch():
    """
    Start a keyboard listener that activates a hard kill switch when the specified key is pressed.

    When the key is pressed, sets SharedState.KILL_SWITCH to True and terminates the process immediately using os._exit(0).

    Returns:
        pynput.keyboard.Listener: The started listener instance.
    """

    def on_press(key):
        """
        Handle a keyboard key press and trigger an immediate hard shutdown when the specified key is pressed.

        If the pressed key is the specified key, logs an informational message, sets KILL_SWITCH to True (using SharedState), and immediately terminates the process using os._exit(0).

        Parameters:
            key: The key event object received from the keyboard listener.
        """
        if key == pynput_keyboard.Key.end:
            logging.info("KILLSWITCH pressed! Exiting...")
            # Set the shared KILL_SWITCH variable
            SharedState.KILL_SWITCH = True
            # Hard terminate the process immediately
            os._exit(0)

    listener = pynput_keyboard.Listener(on_press=on_press)
    listener.start()
    return listener


def move_and_click(x: int, y: int, delay: float = 0.2) -> None:
    """
    Move the mouse to the given screen coordinates and perform a left click.

    Parameters:
        x (int): Horizontal screen coordinate in pixels.
        y (int): Vertical screen coordinate in pixels.
        delay (float): Seconds to wait after the click (default 0.2).
    """
    try:
        logging.debug(f"Moving mouse to ({x}, {y})")
        pyautogui.moveTo(x, y, delay)
        logging.debug(f"Clicking at ({x}, {y})")
        pyautogui.click(x, y)
        logging.debug(f"Sleeping for {delay} seconds after click")
        time.sleep(delay)
    except Exception:
        logging.exception(f"Failed to move to and click at ({x}, {y})")


def type_text(text: str, interval: float = 0.05) -> None:
    """
    Simulate typing the given text into the active application.

    Parameters:
        text (str): The string to type.
        interval (float): Delay in seconds between individual key presses (defaults to 0.05).
    """
    try:
        pyautogui.write(text, interval=interval)
    except Exception:
        logging.exception(f"Failed to type text '{text}'.")


def cursor_resting_spot() -> tuple[int, int]:
    """
    Move the cursor to the resting spot coordinates specified in the global configuration.

    Retrieves the 'cursor_resting_spot' from the vision configuration. If not found,
    defaults to (1035, 900). Handles both list and tuple formats. Logs the action and
    any exceptions encountered.

    Returns:
        tuple[int, int]: The coordinates where the cursor was moved.
    """
    try:
        vision_config = get_vision_config()
        resting_spot = vision_config.get("cursor_resting_spot", (1035, 900))
        if isinstance(resting_spot, list) and len(resting_spot) == 2:
            resting_spot = (resting_spot[0], resting_spot[1])
        elif not (isinstance(resting_spot, tuple) and len(resting_spot) == 2):
            logging.warning("Invalid resting_spot format, using default (1035, 900).")
            resting_spot = (1035, 900)
        logging.debug(f"Moving cursor to resting spot at {resting_spot}")
        pyautogui.moveTo(resting_spot[0], resting_spot[1], duration=0.1)
        return resting_spot
    except Exception:
        logging.exception("Failed to move cursor to resting spot.")
        return (1035, 900)
