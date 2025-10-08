"""
Main entry point for BTD6 Automation Bot MVP
Windows-only version
"""

import pyautogui  # Mouse/keyboard automation (Windows)
import cv2        # Image recognition
import numpy as np
import PIL        # Image format conversion
import pyscreeze  # Screenshot support
import pygetwindow as gw  # Window management (Windows)
from pynput import keyboard as pynput_keyboard # Keyboard event listener
import keyboard  # Keyboard automation (Windows)
import time

# --- Windows-only Constants for MVP ---
MAP_NAME = "Monkey Meadow"
MONKEY_TYPE = "Dart Monkey"
HERO_TYPE = "Quincy"

# Example coordinates (update for actual game window)
MONKEY_COORDS = (440, 355)
SELECT_MONKEY_COORDS = (1215, 145)
HERO_COORDS = (320, 250)
SELECT_HERO_COORDS = (1145, 145)
MONKEY_KEY = 'q'  # Key to select Dart Monkey
HERO_KEY = 'u'    # Key to select Hero

# Window title for BTD6 (Windows)
BTD6_WINDOW_TITLE = "BloonsTD6"

# Global killswitch flag
KILL_SWITCH = False

# Options
pyautogui.PAUSE = 0.1  # Pause after each PyAutoGUI call
pyautogui.FAILSAFE = True  # Move mouse to top-left to abort

def activate_btd6_window() -> bool:
    """
    Activate the BTD6 game window before automation (Windows-only).
    Returns True if successful, False otherwise.
    """
    windows = gw.getWindowsWithTitle(BTD6_WINDOW_TITLE)
    if not windows:
        print(f"Error: Could not find window with title '{BTD6_WINDOW_TITLE}'. (Windows-only)")
        return False
    win = windows[0]
    win.activate()
    print(f"Activated window: {win.title}")
    return True

def esc_listener():
    """
    Listen for ESC key to set killswitch flag (Windows-only).
    """
    def on_press(key):
        global KILL_SWITCH
        if key == pynput_keyboard.Key.esc:
            print("ESC pressed! Exiting...")
            KILL_SWITCH = True
            return False  # Stop listener
    listener = pynput_keyboard.Listener(on_press=on_press)
    listener.start()
    return listener

def capture_screen(region=None) -> np.ndarray:
    """
    Capture a screenshot of the specified region (Windows-only).
    region: (left, top, width, height) or None for full screen
    Returns: OpenCV image (numpy array)
    """
    screenshot = pyautogui.screenshot(region=region)
    # Convert PIL image to OpenCV format
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    return img

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

def main() -> None:
    """
    Main automation loop for BTD6 Automation Bot (Windows-only).
    """
    print("BTD6 Automation Bot MVP starting (Windows-only)...")

    # Start killswitch listener
    esc_listener()

    # Activate BTD6 window
    if not activate_btd6_window():
        print("Exiting due to missing game window.")
        return

    # Example: Capture full screen
    screen_img = capture_screen()
    print(f"Captured screen shape: {screen_img.shape}")

    # Example: Place monkey and hero
    while not KILL_SWITCH:
        pyautogui.moveTo(300, 300, duration=0.1)
        place_hero(HERO_COORDS, HERO_KEY)
        place_monkey(MONKEY_COORDS, MONKEY_KEY)
        print("Automation step complete. Press ESC to exit.")
        break  # Remove or modify for continuous automation

if __name__ == "__main__":
    main()
