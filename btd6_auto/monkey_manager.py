"""
Handles monkey selection and placement.
"""
import pyautogui
import keyboard
import time

def select_monkey(monkey_type):
    pass

def place_monkey(coords: tuple[int, int], monkey_key: str) -> None:
    """
    Simulate mouse action to place monkey at given coordinates (Windows-only).
    """
    keyboard.send(monkey_key)
    time.sleep(0.2)
    pyautogui.moveTo(coords[0], coords[1], duration=0.2)
    pyautogui.click()
