"""
Handles hero selection and placement.
"""
import pyautogui
import keyboard
import time

def select_hero(hero_name):
    pass

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
