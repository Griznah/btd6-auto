"""
Input automation (pyautogui).
"""

# Placeholder for input automation logic
from pynput import keyboard as pynput_keyboard

KILL_SWITCH = False

def esc_listener():
    """
    Listen for ESC key to set killswitch flag (Windows-only).
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

def type_text(text):
    pass

import pyautogui
import keyboard
import time

def place_monkey(coords: tuple[int, int], monkey_key: str) -> None:
    """
    Simulate mouse action to place monkey at given coordinates (Windows-only).
    """
    keyboard.send(monkey_key)
    time.sleep(0.2)
    pyautogui.moveTo(coords[0], coords[1], duration=0.2)
    pyautogui.click()

def place_hero(coords: tuple[int, int], hero_key: str) -> None:
    """
    Simulate mouse action to place hero at given coordinates (Windows-only).
    Hero selection is wonky compared to monkey selection, making a workaround with key press.
    """
    keyboard.press(hero_key)
    time.sleep(0.2)
    keyboard.release(hero_key)
    pyautogui.moveTo(coords[0], coords[1], duration=0.2)
    pyautogui.click()
