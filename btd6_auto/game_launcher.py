"""
Handles launching the game and map selection.
"""

import os
import logging
## Config values are now passed in as arguments
from .vision import capture_screen, find_element_on_screen, is_mostly_black
from .input import click
from .overlay import show_overlay_text

DATA_IMAGE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'images')

def get_image_path(name):
    """Helper to get full path for image asset."""
    return os.path.join(DATA_IMAGE_PATH, name)

def start_map(map_config, global_config):
    """
    Automate starting the selected map with chosen difficulty and mode.
    Config values are passed in as arguments.
    """
    if not activate_btd6_window(map_config, global_config):
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
    pyautogui.click(80, 170) # 1080p coords
    logging.info("Clicked at (80, 170) to open map search box.")
    time.sleep(0.5)
    pyautogui.click(830, 50) # 1080p coords

    # Step 3: Enter map name and select
    pyautogui.typewrite(map_config.get("map_name", "Monkey Meadow"), interval=0.05)
    logging.info(f"Entered map name: {map_config.get('map_name', 'Monkey Meadow')}")
    time.sleep(0.05)
    #pyautogui.click(360, 225) # 720p coords
    #logging.info("Clicked at (360, 225) to select map.")
    pyautogui.click(550, 350) # 1080p coords
    logging.info("Clicked at (550, 350) to select map.")
    time.sleep(0.5) # let next screen load

    # Step 4: Continue with difficulty and mode selection using image matching
    # Step 4: Continue with difficulty and mode selection using image matching
    difficulty = map_config.get("difficulty", "Easy")
    mode = map_config.get("mode", "Standard")
    # Map difficulty/mode to image filenames
    difficulty_img = f"button_{difficulty.lower()}1080p.png"
    mode_img = f"button_{mode.lower().replace(' ', '_')}1080p.png"
    for img_name, desc in [(difficulty_img, f"{difficulty} difficulty"), (mode_img, f"{mode} mode/start")]:
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
        #show_overlay_text(f"Loading: {elapsed:.1f}s", 0.5) # showing how long we have waited
    else:
        logging.error("Loading screen did not disappear in time.")
        return False
    logging.info("Map started successfully.")
    return True


import pygetwindow as gw
import time

def activate_btd6_window(map_config=None, global_config=None) -> bool:
    """
    Activate the BTD6 game window before automation (Windows-only).
    Uses config values if provided.
    Returns:
        bool: True if successful, False otherwise.
    """
    window_title = None
    if map_config and "game_settings" in map_config:
        window_title = map_config["game_settings"].get("window_title")
    if not window_title and global_config and "window_title" in global_config:
        window_title = global_config["window_title"]
    if not window_title:
        window_title = "BloonsTD6"
    try:
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            print(f"Error: Could not find window with title '{window_title}'. (Windows-only)")
            return False
        win = windows[0]
        win.activate()
        time.sleep(0.5)  # Wait for the window to come to the foreground
        print(f"Activated window: {win.title}")
        return True
    except Exception as e:
        print(f"Exception during window activation: {e}")
        return False
