"""
Main entry point for BTD6 Automation Bot MVP
Windows-only version
"""


import logging
import time
import numpy as np
import pyautogui

# Import configuration and modules
from btd6_auto.config import (
    MONKEY_TYPE, HERO_TYPE,
    MONKEY_COORDS, HERO_COORDS,
    MONKEY_KEY, HERO_KEY, BTD6_WINDOW_TITLE, KILL_SWITCH
)
from btd6_auto.game_launcher import activate_btd6_window, start_map
from btd6_auto.input import esc_listener
from btd6_auto.monkey_manager import place_monkey, place_hero
from btd6_auto.vision import capture_screen


# Options
pyautogui.PAUSE = 0.1  # Pause after each PyAutoGUI call
pyautogui.FAILSAFE = True  # Move mouse to top-left to abort



def main() -> None:
    """
    Main automation loop for BTD6 Automation Bot (Windows-only).
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    logging.info("BTD6 Automation Bot MVP starting (Windows-only)...")

    # Start killswitch listener
    esc_listener()
    try:
        while not KILL_SWITCH:
            # Activate BTD6 window and start map
            #if not activate_btd6_window():
            #    logging.error("Exiting due to missing game window.")
            #    return

            if not start_map():
                logging.error("Exiting due to failure to start map.")
                return

            # Place hero and monkey after map is started
            time.sleep(7)  # Wait for map to load
            place_hero(HERO_COORDS, HERO_KEY)
            time.sleep(0.5)  # Wait for hero to be placed
            place_monkey(MONKEY_COORDS, MONKEY_KEY)
            time.sleep(0.5)  # Wait for monkey to be placed
            logging.info("Automation step complete. Press ESC to exit.")
            break  # Remove or modify for continuous automation
    except Exception as e:
        logging.exception(f"Automation error: {e}")


if __name__ == "__main__":
    main()
