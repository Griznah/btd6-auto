"""
Handles launching the game and map selection.
"""

import os
import logging
from .config import selected_map, selected_difficulty, selected_mode
from .vision import capture_screen, find_element_on_screen, is_mostly_black
from .input import click
from .overlay import show_overlay_text

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

    import time
    import pyautogui

    # Step 1: Click 'Play' button using image matching
    play_img = get_image_path("button_play1080p.png")
    screen = capture_screen()
    play_coords = find_element_on_screen(play_img)
    if play_coords:
        click(*play_coords)
        logging.info(f"Clicked Play button at {play_coords}")
    else:
        logging.error("Could not find Play button on screen.")
        return False

    # Step 2: Wait and click coordinates to open map search
    time.sleep(0.5)
    #pyautogui.click(55, 115) # 720p coords
    #logging.info("Clicked at (55, 115) to open map search box.")
    pyautogui.click(80, 170) # 1080p coords
    logging.info("Clicked at (80, 170) to open map search box.")
    time.sleep(0.5)
    #pyautogui.click(615, 30) # 720p coords
    #logging.info("Clicked at (615, 30) to focus map search input.")
    pyautogui.click(830, 50) # 1080p coords
    #logging.info("Clicked at (830, 50) to focus map search input.")

    # Step 3: Enter map name and select
    pyautogui.typewrite(selected_map, interval=0.05)
    logging.info(f"Entered map name: {selected_map}")
    time.sleep(0.05)
    #pyautogui.click(360, 225) # 720p coords
    #logging.info("Clicked at (360, 225) to select map.")
    pyautogui.click(550, 350) # 1080p coords
    logging.info("Clicked at (550, 350) to select map.")
    time.sleep(0.5) # let next screen load

    # Step 4: Continue with difficulty and mode selection using image matching
    for img_name, desc in [("button_easy1080p.png", "Easy difficulty"), ("button_standard1080p.png", "Standard mode/start")]:
        time.sleep(0.5) # let next screen load
        img_path = get_image_path(img_name)
        screen = capture_screen()
        coords = find_element_on_screen(img_path)
        if coords:
            click(*coords)
            logging.info(f"Clicked {desc} at {coords}")
        else:
            logging.error(f"Could not find {desc} on screen.")
            return False
    # Check for overwrite save prompt
    time.sleep(0.5)
    overwrite_img = get_image_path("overwrite_save1080p.png")
    screen = capture_screen()
    overwrite_coords = find_element_on_screen(overwrite_img)
    if overwrite_coords:
        logging.info(f"Found overwrite save prompt at {overwrite_coords}")
        ok_img = get_image_path("overwrite_ok1080p.png")
        ok_coords = find_element_on_screen(ok_img)
        if ok_coords:
            click(*ok_coords)
            logging.info(f"Clicked Overwrite OK at {ok_coords}")
        else:
            logging.error("Could not find Overwrite OK button on screen.")
            return False
    # Wait for loading screen to disappear (mostly black with some yellow/gold)
    max_wait = 15  # seconds
    poll_interval = 0.5
    elapsed = 0
    while elapsed < max_wait:
        img_bgr, _ = capture_screen()
        # Use vision.py logic: check if screen is "mostly black"
        # For example, vision.py could have: is_mostly_black(image, threshold=0.9)
        if img_bgr is None:
            logging.error("Failed to capture screen during loading check.")
            return False
        if not is_mostly_black(img_bgr, threshold=0.9):
            break
        time.sleep(poll_interval)
        elapsed += poll_interval
        show_overlay_text(f"Loading: {elapsed:.1f}s", 0.5) # showing how long we have waited
    else:
        logging.error("Loading screen did not disappear in time.")
        return False
    logging.info("Map started successfully.")
    return True


import pygetwindow as gw
import time
from .config import BTD6_WINDOW_TITLE

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
        time.sleep(0.5)  # Wait for the window to come to the foreground
        print(f"Activated window: {win.title}")
        return True
    except Exception as e:
        print(f"Exception during window activation: {e}")
        return False
