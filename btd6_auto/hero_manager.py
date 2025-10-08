"""
Handles hero selection and placement.
"""

from .input import click
from config import CLICK_DELAY
import logging

def select_hero(hero_name):
    pass

def place_hero(coords: tuple[int, int], hero_key: str) -> None:
    """
    Simulate mouse action to place hero at given coordinates (Windows-only).
    Uses input utilities and config for delays.
    """
    try:
        import keyboard
        keyboard.press(hero_key)
        time.sleep(CLICK_DELAY)
        keyboard.release(hero_key)
        click(coords[0], coords[1], delay=CLICK_DELAY)
    except Exception as e:
        logging.error(f"Failed to place hero at {coords} with key {hero_key}: {e}")
