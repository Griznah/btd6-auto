"""
Main entry point for BTD6 Automation Bot
Windows-only version
"""

import argparse
import logging
import time
import pyautogui
from btd6_auto.config_loader import ConfigLoader
from btd6_auto.game_launcher import load_map
from btd6_auto.input import esc_listener
from btd6_auto.state import SharedState
from btd6_auto.vision import set_round_state
from btd6_auto.currency_reader import CurrencyReader
from btd6_auto.overlay import show_overlay_text
from btd6_auto.actions import ActionManager, can_afford
from btd6_auto.debug_manager import DebugManager

# Options
pyautogui.PAUSE = 0.1  # Pause after each PyAutoGUI call
pyautogui.FAILSAFE = True  # Move mouse to top-left to abort
# KILL_SWITCH is now managed via SharedState


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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="BTD6 Automation Bot")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode (sets logging to DEBUG level)"
    )
    args = parser.parse_args()

    # Set debug state
    from btd6_auto.state import DebugState

    DebugState.DEBUG_ENABLED = args.debug

    # Load configs
    global_config = ConfigLoader.load_global_config()
    map_name = global_config.get("default_map", "Monkey Meadow")
    try:
        map_config = ConfigLoader.load_map_config(map_name)
    except Exception:
        logging.exception(
            f"Could not load map config for '{map_name}', falling back to 'Monkey Meadow'."
        )
        map_config = ConfigLoader.load_map_config("Monkey Meadow")

    # Initialize debug manager with configuration
    debug_config = global_config.get("debug", {})
    debug_config.update(
        {
            "enabled": args.debug or debug_config.get("enabled", False),
            "log_to_console": args.debug or debug_config.get("log_to_console", True),
            "log_to_file": debug_config.get("log_to_file", True),
            "level": 3
            if args.debug
            else debug_config.get("level", 1),  # 3 = VERBOSE, 1 = BASIC
        }
    )
    debug_manager = DebugManager(debug_config)

    # Set up logging to both file and STDOUT
    # Debug flag overrides config file setting
    if DebugState.DEBUG_ENABLED:
        log_level = logging.DEBUG
    else:
        log_level = getattr(
            logging,
            global_config.get("automation", {}).get("logging_level", "INFO"),
        )
    log_format = "%(asctime)s %(levelname)s: %(message)s"
    log_file = "btd6_automation.log"

    handlers = [
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        logging.StreamHandler(),
    ]
    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)

    # Log startup messages after logging is configured
    if DebugState.DEBUG_ENABLED:
        logging.info("Debug mode enabled via --debug flag")
    logging.info("BTD6 Automation Bot starting, press ESC to exit at any time.")

    # Log debug manager initialization
    debug_manager.log_basic(
        "Main",
        f"Debug manager initialized (enabled: {debug_config['enabled']}, level: {debug_config['level']})",
    )
    debug_manager.log_detailed(
        "Main",
        "Starting automation with configuration",
        map_name=map_name,
        debug_mode=DebugState.DEBUG_ENABLED,
    )

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

        # Show overlay message "Loading the CurrencyReader" for 3 seconds
        show_overlay_text("Loading the CurrencyReader", 3)

        # Wait for first nonzero currency value or timeout (8 seconds)
        ocr_timeout = 8.0
        ocr_start = time.time()
        while True:
            currency = currency_reader.get_currency()
            # logging.info(f"currency in checker: {currency}")
            if currency > 0:
                break
            if (time.time() - ocr_start) > ocr_timeout:
                logging.error(
                    "Timeout: OCR did not return a nonzero currency value within 8 seconds."
                )
                break
            time.sleep(0.1)

        # Use ActionManager for orchestration
        action_manager = ActionManager(
            map_config, global_config, currency_reader, debug_manager
        )

        # Run pre-play actions (hero and monkeys)
        debug_manager.log_basic("Main", "Starting pre-play actions")
        logging.info("Running pre-play actions (hero and monkeys)")

        pre_play_id = debug_manager.start_performance_tracking("pre_play_sequence")
        action_manager.run_pre_play()
        pre_play_time = debug_manager.finish_performance_tracking(pre_play_id)

        debug_manager.log_action(
            "pre_play_sequence", "all", True, details={"total_time": pre_play_time}
        )

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
        while not SharedState.KILL_SWITCH:
            if curr_check_count >= 5:
                break
            currency = currency_reader.get_currency()
            logging.info(f"Current currency 04: {currency}")
            curr_check_count += 1
            time.sleep(0.3)

        if SharedState.KILL_SWITCH:
            logging.info("Kill switch activated. Exiting before actions.")
            currency_reader.stop()
            return

        # --- Main action loop (buy/upgrade) ---
        main_loop_id = debug_manager.start_performance_tracking("main_action_loop")
        action_count = 0
        debug_manager.log_basic("Main", "Starting main action loop")

        while True:
            if SharedState.KILL_SWITCH:
                debug_manager.log_basic(
                    "Main", "Kill switch activated. Exiting main action loop."
                )
                logging.info("Kill switch activated. Exiting main action loop.")
                break

            next_action = action_manager.get_next_action()
            if not next_action:
                debug_manager.log_basic("Main", "All actions completed")
                logging.info("All actions completed.")
                break

            action_count += 1
            debug_manager.log_detailed(
                "Main",
                f"Processing action {action_count}",
                action_type=next_action.get("action"),
                step=next_action.get("step"),
                target=next_action.get("target"),
            )

            # Wait for enough money
            currency = currency_reader.get_currency()
            if not can_afford(currency, next_action, map_config):
                # debug_manager.log_verbose("Main", "Insufficient funds, waiting",
                #                        data={"currency": currency, "action": next_action})
                time.sleep(0.2)
                continue

            if next_action["action"] == "buy":
                debug_manager.log_detailed(
                    "Main",
                    f"Executing buy action with ${currency}",
                    target=next_action.get("target"),
                )
                logging.info(f"We have ${currency} to buy")
                action_manager.run_buy_action(next_action)
                currency = 0  # need to reset currency after buy to avoid double spending
            elif next_action["action"] == "upgrade":
                debug_manager.log_detailed(
                    "Main",
                    f"Executing upgrade action with ${currency}",
                    target=next_action.get("target"),
                    upgrade_path=next_action.get("upgrade_path"),
                )
                logging.info(f"We have ${currency} to upgrade")
                action_manager.run_upgrade_action(next_action)
                currency = 0  # need to reset currency after upgrade to avoid double spending
            else:
                debug_manager.log_basic(
                    "Main", f"Unknown action type: {next_action['action']}", "warning"
                )
                logging.warning(f"Unknown action type: {next_action['action']}")

            action_manager.mark_completed(next_action["step"])
            remaining_steps = action_manager.steps_remaining()
            debug_manager.log_detailed(
                "Main", f"Action {action_count} completed", remaining_steps=remaining_steps
            )
            logging.info(f"Steps remaining: {action_manager.steps_remaining()}")

        main_loop_time = debug_manager.finish_performance_tracking(main_loop_id)
        debug_manager.log_action(
            "main_action_loop",
            "all",
            True,
            details={"total_actions": action_count, "total_time": main_loop_time},
        )

        currency_reader.stop()
        debug_manager.log_basic("Main", "Automation completed successfully")
        debug_manager.log_performance_summary()

        logging.info(
            "Automation completed successfully.\nIn the future we will call End Map-logic here."
        )

    except Exception as e:
        if "currency_reader" in locals():
            currency_reader.stop()
        debug_manager.log_error(
            "Main",
            e,
            context={
                "map_name": map_name if "map_name" in locals() else "unknown",
                "action_count": action_count if "action_count" in locals() else 0,
            },
        )
        logging.exception("Automation error")


if __name__ == "__main__":
    main()
