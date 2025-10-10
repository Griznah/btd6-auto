"""
Handles launching the game and map selection.
"""


import os
import logging
from .config import selected_map, selected_difficulty, selected_mode
from .vision import capture_screen, find_element_on_screen
from .input import click

DATA_IMAGE_PATH = os.path.join(os.path.dirname(__file__), '..\data\images')

def get_image_path(name):
    """Helper to get full path for image asset."""
    return os.path.join(DATA_IMAGE_PATH, name)

def start_map():
    """
    Automate starting the selected map with chosen difficulty and mode.
    Steps:
    1. Click 'Play' button
    2. Select map (Monkey Meadow)
    3. Select difficulty (Easy)
    4. Select mode (Standard)
    """
    if not activate_btd6_window():
        logging.error("BTD6 window not activated.")
        return False

    steps = [
        ("button_play.png", "Play button"),
        ("map_monkey_meadow.png", "Monkey Meadow map"),
        ("button_easy.png", "Easy difficulty"),
        ("button_standard.png", "Standard mode/start"),
    ]

    for img_name, desc in steps:
        img_path = get_image_path(img_name)
        screen = capture_screen()
        coords = find_element_on_screen(img_path)
        if coords:
            click(*coords)
            logging.info(f"Clicked {desc} at {coords}")
        else:
            logging.error(f"Could not find {desc} on screen.")
            return False
    logging.info("Map started successfully.")
    return True


import pygetwindow as gw
from config import BTD6_WINDOW_TITLE

def activate_btd6_window() -> bool:
    """
    Activate the BTD6 game window before automation (Windows-only).
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        windows = gw.getWindowsWithTitle(BTD6_WINDOW_TITLE)
        if not windows:
            print(f"Error: Could not find window with title '{BTD6_WINDOW_TITLE}'. (Windows-only)")
            return False
        win = windows[0]
        win.activate()
        print(f"Activated window: {win.title}")
        return True
    except Exception as e:
        print(f"Exception during window activation: {e}")
        return False
