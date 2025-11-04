"""
Input automation utilities for BTD6 automation bot.
Centralizes mouse/keyboard actions and error handling.
"""


import pyautogui
import time
import logging
import os  # For hard termination
from pynput import keyboard as pynput_keyboard


def esc_listener():
    """
    Start a keyboard listener that triggers a killswitch when the Escape key is pressed.
    
    On Escape press, sets KILL_SWITCH to True and immediately terminates the process (Windows-only).
    
    Returns:
        pynput.keyboard.Listener: The started listener instance.
    """
    def on_press(key):
        """
        Handle a keyboard key press and trigger an immediate hard shutdown when ESC is pressed.
        
        If the pressed key is the ESC key, logs an informational message, sets KILL_SWITCH to True (using globals()), and immediately terminates the process using os._exit(0).
        
        Parameters:
            key: The key event object received from the keyboard listener.
        """
        if key == pynput_keyboard.Key.esc:
            logging.info("ESC pressed! Exiting...")
            # Set the global KILL_SWITCH variable
            globals()["KILL_SWITCH"] = True
            # Hard terminate the process immediately
            os._exit(0)
    listener = pynput_keyboard.Listener(on_press=on_press)
    listener.start()
    return listener


def click(x: int, y: int, delay: float = 0.2) -> None:
    """
    Move the mouse to the specified screen coordinates and perform a left click.
    
    Parameters:
        x (int): Horizontal screen coordinate in pixels.
        y (int): Vertical screen coordinate in pixels.
        delay (float): Seconds to wait after the click (default 0.2).
    """
    try:
        logging.debug(f"Moving mouse to ({x}, {y})")
        pyautogui.moveTo(x, y)
        logging.debug(f"Clicking at ({x}, {y})")
        pyautogui.click()
        logging.debug(f"Sleeping for {delay} seconds after click")
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