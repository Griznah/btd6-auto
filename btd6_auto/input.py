
"""
Input automation utilities for BTD6 automation bot.
Centralizes mouse/keyboard actions and error handling.
"""


import pyautogui
import time
import logging
import os  # For hard termination
from pynput import keyboard as pynput_keyboard
from .config import CLICK_DELAY, KILL_SWITCH


def esc_listener():
    """
    Listen for ESC key to set killswitch flag (Windows-only).
    Performs hard termination using os._exit(0) for immediate exit.
    Returns:
        pynput.keyboard.Listener: The listener object.
    """
    from btd6_auto import config
    def on_press(key):
        if key == pynput_keyboard.Key.esc:
            logging.info("ESC pressed! Exiting...")
            config.KILL_SWITCH = True
            # Hard terminate the process immediately
            os._exit(0)
    listener = pynput_keyboard.Listener(on_press=on_press)
    listener.start()
    return listener


def click(x: int, y: int, delay: float = CLICK_DELAY) -> None:
    """
    Move mouse to (x, y) and click, with optional delay.
    Args:
        x (int): X coordinate.
        y (int): Y coordinate.
        delay (float): Delay after click.
    """
    try:
        pyautogui.moveTo(x, y)
        pyautogui.click()
        time.sleep(delay)
    except Exception as e:
        logging.error(f"Failed to click at ({x}, {y}): {e}")

def type_text(text: str, interval: float = 0.05) -> None:
    """
    Type text using pyautogui.
    Args:
        text (str): The text to type.
        interval (float): Delay between key presses.
    """
    try:
        pyautogui.write(text, interval=interval)
    except Exception as e:
        logging.error(f"Failed to type text '{text}': {e}")
