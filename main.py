"""
Main entry point for BTD6 Automation Bot
Windows-only version
"""

import logging
import time
#import sys

# import numpy as np
import pyautogui

# Import configuration loader and modules
from btd6_auto.config_loader import ConfigLoader
from btd6_auto.config import KILL_SWITCH
from btd6_auto.game_launcher import load_map
from btd6_auto.input import esc_listener

# from btd6_auto.overlay import show_overlay_text
from btd6_auto.monkey_manager import place_monkey, place_hero
from btd6_auto.vision import set_round_state
from btd6_auto.currency_reader import CurrencyReader
from btd6_auto.overlay import show_overlay_text

# Options
pyautogui.PAUSE = 0.1  # Pause after each PyAutoGUI call
pyautogui.FAILSAFE = True  # Move mouse to top-left to abort


def main() -> None:
    """
    Orchestrates the automation lifecycle for the BTD6 bot: load configuration, start the map, place hero and monkeys, and run configured actions while respecting the kill switch.

    This function:
    - Loads global and map configurations (falls back to "Monkey Meadow" on map-load failure) and initializes logging.
    - Starts an ESC listener that toggles a global killswitch to stop automation.
    - Repeatedly attempts to load the map; if loading fails the function exits.
    - Places the configured hero, executes any pre-play "buy" actions (monkey placements), and then enters a runtime loop that monitors currency and pauses between action cycles.
    - After runtime monitoring, processes the map's ordered actions (e.g., "buy" for monkey placement and placeholder handling for "upgrade") using configured timing and key bindings.
    - Logs unexpected exceptions encountered during automation.

    No value is returned.
    """
    # Load configs
    global_config = ConfigLoader.load_global_config()
    map_name = global_config.get("default_map", "Monkey Meadow")
    try:
        map_config = ConfigLoader.load_map_config(map_name)
    except Exception:
        logging.warning(
            f"Could not load map config for '{map_name}', falling back to 'Monkey Meadow'."
        )
        map_config = ConfigLoader.load_map_config("Monkey Meadow")

    logging.basicConfig(
        level=getattr(
            logging, global_config.get("automation", {}).get("logging_level", "INFO")
        ),
        format="%(asctime)s %(levelname)s: %(message)s",
    )
    logging.info("BTD6 Automation Bot starting, press ESC to exit at any time.")

    # Start killswitch listener
    esc_listener()
    try:
        # Load map once
        logging.info("Entry for loading map")
        if not load_map(map_config, global_config):
            logging.error("Exiting due to failure to load map.")
            return


        # Start currency reader thread
        currency_reader = CurrencyReader()
        currency_reader.start()

        # Show overlay message "Loading the CurrencyReader" for 2 seconds
        show_overlay_text("Loading the CurrencyReader", 2)
        
        # Wait for first nonzero currency value or timeout (5 seconds)
        ocr_timeout = 5.0
        ocr_start = time.time()
        while True:
            currency = currency_reader.get_currency()
            logging.info(f"currency in checker: {currency}")
            if currency > 0:
                #sys.exit(1)
                break
            if (time.time() - ocr_start) > ocr_timeout:
                logging.exception("Timeout: OCR did not return a nonzero currency value within 5 seconds.")
                break
            time.sleep(0.1)

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
        currency = currency_reader.get_currency()
        logging.info(f"Current currency 02: {currency}")
        pre_play_actions = map_config.get("pre_play_actions", [])
        for action in sorted(pre_play_actions, key=lambda a: a.get("step", 0)):
            if action["action"] == "buy":
                monkey_pos = action["position"]
                if isinstance(monkey_pos, dict):
                    monkey_pos = (monkey_pos["x"], monkey_pos["y"])
                key_binding = (
                    action["key_binding"]
                    if "key_binding" in action
                    else global_config.get("default_monkey_key", "q")
                )
                place_monkey(monkey_pos, key_binding)
                time.sleep(map_config.get("timing", {}).get("placement_delay", 0.5))

        logging.info(
            "Opening hero and monkey sequence complete. Press ESC to exit at any time."
        )

        currency = currency_reader.get_currency()
        logging.info(f"Current currency 03: {currency}")

        # Start the round
        try:
            set_round_state("start")
        except Exception:
            logging.exception("Unable to set round state(start map)")

        curr_check_count = 0
        while not KILL_SWITCH:
            if curr_check_count >= 25:
                break
            currency = currency_reader.get_currency()
            logging.info(f"Current currency 04: {currency}")
            curr_check_count += 1
            time.sleep(0.3)

        currency_reader.stop()

        if KILL_SWITCH:
            logging.info("Kill switch activated. Exiting before actions.")
            return

#        # Place monkeys and upgrades as per actions, in order
#        for action in sorted(
#            map_config.get("actions", []), key=lambda a: a.get("step", 0)
#        ):
#            if KILL_SWITCH:
#                logging.info("Kill switch activated. Exiting during actions.")
#                return
#            if action["action"] == "buy":
#                monkey_pos = action["position"]
#                if isinstance(monkey_pos, dict):
#                    monkey_pos = (monkey_pos["x"], monkey_pos["y"])
#                key_binding = (
#                    action["key_binding"]
#                    if "key_binding" in action
#                    else global_config.get("default_monkey_key", "q")
#                )
#                place_monkey(monkey_pos, key_binding)
#                time.sleep(map_config.get("timing", {}).get("placement_delay", 0.5))
#            elif action["action"] == "upgrade":
#                # Implement upgrade logic here
#                time.sleep(map_config.get("timing", {}).get("upgrade_delay", 0.5))

    except Exception as e:
        logging.exception(f"Automation error: {e}")


if __name__ == "__main__":
    main()
