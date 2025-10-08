
"""
Handles selection and placement of monkeys and heroes.
"""
import pyautogui
import keyboard
import time

def select_monkey(monkey_type: str) -> None:
    """
    Select a monkey type.
    Parameters:
        monkey_type (str): The type of monkey to select.
    """
    pass

def select_hero(hero_name: str) -> None:
    """
    Select a hero by name.
    Parameters:
        hero_name (str): The name of the hero to select.
    """
    pass

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
