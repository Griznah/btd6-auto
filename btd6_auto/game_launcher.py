"""
Handles launching the game and map selection.
"""

# Placeholder for game launch and map selection logic

def launch_game():
    pass

def select_map(map_name):
    pass


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
