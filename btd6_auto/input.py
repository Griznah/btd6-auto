
"""
Input automation utilities for BTD6 automation bot.
Centralizes mouse/keyboard actions and error handling.
"""


import pyautogui
import time
import logging
from pynput import keyboard as pynput_keyboard
from config import CLICK_DELAY


KILL_SWITCH = False


def esc_listener():
    """
    Listen for ESC key to set killswitch flag (Windows-only).
    Returns:
        pynput.keyboard.Listener: The listener object.
    """
    def on_press(key):
        global KILL_SWITCH
        if key == pynput_keyboard.Key.esc:
            print("ESC pressed! Exiting...")
            KILL_SWITCH = True
            return False  # Stop listener
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
