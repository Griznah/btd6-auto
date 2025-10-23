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
    Place a monkey at the given screen coordinates by sending the selection key and performing a click.
    
    Parameters:
        coords (tuple[int, int]): (x, y) screen coordinates where the monkey should be placed.
        monkey_key (str): Key or key sequence used to select the monkey before placing.
        delay (float): Seconds to wait after sending the selection key and used for the click timing (default 0.2).
    
    Notes:
        This function performs real input actions (keyboard send and mouse click) and is intended for Windows environments where the required input libraries are available. Failures are logged and not raised.
    """
    try:
        import keyboard
        logging.debug(f"Selecting monkey with key '{monkey_key}'")
        keyboard.send(monkey_key)
        time.sleep(delay)
        logging.debug(f"Placing monkey at coordinates {coords}")
        click(coords[0], coords[1], delay=delay)
    except Exception as e:
        logging.error(f"Failed to place monkey at {coords} with key {monkey_key}: {e}")

def place_hero(coords: tuple[int, int], hero_key: str, delay: float = 0.2) -> None:
    """
    Selects the specified hero key and clicks at the given screen coordinates to place the hero.
    
    Parameters:
        coords (tuple[int, int]): Screen (x, y) coordinates where the hero will be placed.
        hero_key (str): Keyboard key used to select the hero.
        delay (float): Seconds to wait after pressing the key and before clicking (default 0.2).
    """
    try:
        import keyboard
        logging.debug(f"Selecting hero with key '{hero_key}'")
        keyboard.press(hero_key)
        time.sleep(delay)
        keyboard.release(hero_key)
        logging.debug(f"Placing hero at coordinates {coords}")
        click(coords[0], coords[1], delay=delay)
    except Exception as e:
        logging.error(f"Failed to place hero at {coords} with key {hero_key}: {e}")