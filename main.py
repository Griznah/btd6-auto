"""
Main entry point for BTD6 Automation Bot
Windows-only version
"""

import logging
import time
import numpy as np
import pyautogui

# Import configuration loader and modules
from btd6_auto.config_loader import ConfigLoader
from btd6_auto.config import KILL_SWITCH
from btd6_auto.game_launcher import activate_btd6_window, load_map
from btd6_auto.input import esc_listener
from btd6_auto.overlay import show_overlay_text
from btd6_auto.monkey_manager import place_monkey, place_hero
from btd6_auto.vision import capture_screen, read_currency_amount

# Options
pyautogui.PAUSE = 0.1  # Pause after each PyAutoGUI call
pyautogui.FAILSAFE = True  # Move mouse to top-left to abort

def main() -> None:
    """
    Main automation loop for BTD6 Automation Bot
    """
    # Load configs
    global_config = ConfigLoader.load_global_config()
    map_name = global_config.get("default_map", "Monkey Meadow")
    try:
        map_config = ConfigLoader.load_map_config(map_name)
    except Exception:
        logging.warning(f"Could not load map config for '{map_name}', falling back to 'Monkey Meadow'.")
        map_config = ConfigLoader.load_map_config("Monkey Meadow")

    logging.basicConfig(level=getattr(logging, global_config.get("automation", {}).get("logging_level", "INFO")),
                        format='%(asctime)s %(levelname)s: %(message)s')
    logging.info("BTD6 Automation Bot starting, press ESC to exit at any time.")

    # Start killswitch listener
    esc_listener()
    try:
        while not KILL_SWITCH:
            # Load map
            logging.info("Entry for loading map")
            if not load_map(map_config, global_config):
                logging.error("Exiting due to failure to load map.")
                return

            # Place hero after map loads
            logging.info("Entry for hero placement")
            time.sleep(map_config.get("timing", {}).get("placement_delay", 0.5))
            hero = map_config["hero"]
            hero_pos = hero["position"]
            if isinstance(hero_pos, dict):
                hero_pos = (hero_pos["x"], hero_pos["y"])
            place_hero(hero_pos, hero["key_binding"])
            time.sleep(map_config.get("timing", {}).get("placement_delay", 0.5))

            # Place pre-play monkeys before starting the map
            logging.info("Entry for pre_play_actions")
            pre_play_actions = map_config.get("pre_play_actions", [])
            for action in sorted(pre_play_actions, key=lambda a: a.get("step", 0)):
                if action["action"] == "buy":
                    monkey_pos = action["position"]
                    if isinstance(monkey_pos, dict):
                        monkey_pos = (monkey_pos["x"], monkey_pos["y"])
                    key_binding = action["key_binding"] if "key_binding" in action else global_config.get("default_monkey_key", "q")
                    place_monkey(monkey_pos, key_binding)
                    time.sleep(map_config.get("timing", {}).get("placement_delay", 0.5))

            logging.info("Opening hero and monkey sequence complete. Press ESC to exit at any time.")

            while not KILL_SWITCH:
                currency = read_currency_amount(debug=False)
                logging.debug(f"Current currency: {currency}")
                currency_string = str(currency)
                #show_overlay_text(currency_string, 0.5)
                time.sleep(global_config.get("automation", {}).get("pause_between_actions", 0.2))

            # Place monkeys and upgrades as per actions, in order
            for action in sorted(map_config.get("actions", []), key=lambda a: a.get("step", 0)):
                if action["action"] == "buy":
                    monkey_pos = action["position"]
                    if isinstance(monkey_pos, dict):
                        monkey_pos = (monkey_pos["x"], monkey_pos["y"])
                    key_binding = action["key_binding"] if "key_binding" in action else global_config.get("default_monkey_key", "q")
                    place_monkey(monkey_pos, key_binding)
                    time.sleep(map_config.get("timing", {}).get("placement_delay", 0.5))
                elif action["action"] == "upgrade":
                    # Implement upgrade logic here
                    time.sleep(map_config.get("timing", {}).get("upgrade_delay", 0.5))

            #break  # Remove or modify for continuous automation
    except Exception as e:
        logging.exception(f"Automation error: {e}")

if __name__ == "__main__":
    main()
