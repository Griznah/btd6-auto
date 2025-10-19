
"""
Handles selection and placement of monkeys and heroes.
"""


from .input import click
import logging
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

def place_monkey(coords: tuple[int, int], monkey_key: str, delay: float = 0.2) -> None:
    """
    Simulate mouse action to place monkey at given coordinates (Windows-only).
    Uses input utilities and config for delays.
    """
    try:
        import keyboard
        keyboard.send(monkey_key)
        time.sleep(delay)
        click(coords[0], coords[1], delay=delay)
    except Exception as e:
        logging.error(f"Failed to place monkey at {coords} with key {monkey_key}: {e}")

def place_hero(coords: tuple[int, int], hero_key: str, delay: float = 0.2) -> None:
    """
    Simulate mouse action to place hero at given coordinates (Windows-only).
    Uses input utilities and config for delays.
    """
    try:
        import keyboard
        keyboard.press(hero_key)
        time.sleep(delay)
        keyboard.release(hero_key)
        click(coords[0], coords[1], delay=delay)
    except Exception as e:
        logging.error(f"Failed to place hero at {coords} with key {hero_key}: {e}")
