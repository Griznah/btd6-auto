"""
Handles selection and placement of monkeys and heroes.
"""

from .input import click, cursor_resting_spot
from .config_utils import get_vision_config
import logging
import time
from .vision import (
    retry_action,
    confirm_selection,
    verify_placement_change,
    handle_vision_error,
)


def get_regions_for_monkey():
    """
    Extract regions and thresholds for monkey placement from vision config.
    Returns:
        dict: Dictionary of relevant regions and thresholds.
    """
    vision = get_vision_config()
    from .vision import rect_to_region

    return {
        "max_attempts": vision.get("max_attempts", 3),
        "select_threshold": vision.get("select_threshold", 40.0),
        "place_threshold": vision.get("place_threshold", 85.0),
        "select_region": rect_to_region(
            vision.get("select_region", [925, 800, 1135, 950])
        ),
        "place_region_1": rect_to_region(
            vision.get("place_region_1", [35, 65, 415, 940])
        ),
        "place_region_2": rect_to_region(
            vision.get("place_region_2", [1260, 60, 1635, 940])
        ),
    }


def get_regions_for_hero():
    """
    Extract regions and thresholds for hero placement from vision config.
    Returns:
        dict: Dictionary of relevant regions and thresholds.
    """
    vision = get_vision_config()
    from .vision import rect_to_region

    return {
        "max_attempts": vision.get("max_attempts", 3),
        "select_threshold": vision.get("select_threshold", 40.0),
        "place_threshold": vision.get("place_threshold", 85.0),
        "select_region": rect_to_region(
            vision.get("select_region", [935, 800, 200, 150])
        ),
        "place_region_1": rect_to_region(
            vision.get("place_region_1", [35, 65, 415, 940])
        ),
        "place_region_2": rect_to_region(
            vision.get("place_region_2", [1260, 60, 1635, 940])
        ),
    }


def place_monkey(
    coords: tuple[int, int], monkey_key: str, delay: float = 0.2
) -> None:
    """
    Place a monkey at the given screen coordinates by sending the selection key and performing a click.

    Parameters:
        coords (tuple[int, int]): (x, y) screen coordinates where the monkey should be placed.
        monkey_key (str): Key or key sequence used to select the monkey before placing.
        delay (float): Seconds to wait after sending the selection key and used for the click timing (default 0.2).

    Notes:
        This function performs real input actions (keyboard send and mouse click) and is intended for Windows environments where the required input libraries are available. Failures are logged and not raised.
    """
    try:
        import keyboard

        cursor_resting_spot()  # Move cursor to resting spot before action

        regions = get_regions_for_monkey()
        max_attempts = regions["max_attempts"]
        select_threshold = regions["select_threshold"]
        place_threshold = regions["place_threshold"]
        select_region = regions["select_region"]
        place_region_1 = regions["place_region_1"]
        place_region_2 = regions["place_region_2"]

        def select_monkey():
            keyboard.send(monkey_key)
            time.sleep(delay)

        selection_success = retry_action(
            select_monkey,
            select_region,
            select_threshold,
            max_attempts=max_attempts,
            delay=delay,
            confirm_fn=confirm_selection,
        )
        if not selection_success:
            logging.error(f"Monkey selection failed for key {monkey_key}")
            handle_vision_error()
            return

        def do_place():
            click(coords[0], coords[1], delay=delay)

        placement_success_1 = retry_action(
            do_place,
            place_region_1,
            place_threshold,
            max_attempts=max_attempts,
            delay=delay,
            confirm_fn=verify_placement_change,
        )
        placement_success_2 = retry_action(
            do_place,
            place_region_2,
            place_threshold,
            max_attempts=max_attempts,
            delay=delay,
            confirm_fn=verify_placement_change,
        )
        if not (placement_success_1 or placement_success_2):
            logging.error(f"Monkey placement failed at {coords}")
            handle_vision_error()
            return
    except Exception:
        logging.exception(
            f"Failed to place monkey at {coords} with key {monkey_key}"
        )


def place_hero(
    coords: tuple[int, int], hero_key: str, delay: float = 0.2
) -> None:
    """
    Selects the specified hero key and clicks at the given screen coordinates to place the hero.

    Parameters:
        coords (tuple[int, int]): Screen (x, y) coordinates where the hero will be placed.
        hero_key (str): Keyboard key used to select the hero.
        delay (float): Seconds to wait after pressing the key and before clicking (default 0.2).
    """
    try:
        import keyboard

        cursor_resting_spot()  # Move cursor to resting spot before action

        regions = get_regions_for_hero()
        max_attempts = regions["max_attempts"]
        select_threshold = regions["select_threshold"]
        place_threshold = regions["place_threshold"]
        select_region = regions["select_region"]
        place_region_1 = regions["place_region_1"]
        place_region_2 = regions["place_region_2"]

        def select_hero():
            keyboard.press(hero_key)
            time.sleep(delay)
            keyboard.release(hero_key)

        selection_success = retry_action(
            select_hero,
            select_region,
            select_threshold,
            max_attempts=max_attempts,
            delay=delay,
            confirm_fn=confirm_selection,
        )
        if not selection_success:
            logging.error(f"Hero selection failed for key {hero_key}")
            handle_vision_error()
            return

        def do_place():
            click(coords[0], coords[1], delay=delay)

        # Confirm placement: success if either region passes
        placement_success_1 = retry_action(
            do_place,
            place_region_1,
            place_threshold,
            max_attempts=max_attempts,
            delay=delay,
            confirm_fn=verify_placement_change,
        )
        placement_success_2 = retry_action(
            do_place,
            place_region_2,
            place_threshold,
            max_attempts=max_attempts,
            delay=delay,
            confirm_fn=verify_placement_change,
        )
        if not (placement_success_1 or placement_success_2):
            logging.error(f"Hero placement failed at {coords}")
            handle_vision_error()
            return
    except Exception:
        logging.exception(
            f"Failed to place hero at {coords} with key {hero_key}"
        )
