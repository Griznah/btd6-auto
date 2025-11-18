"""
Handles selection and placement of monkeys and heroes.
"""

from .input import move_and_click, cursor_resting_spot
from .config_utils import get_vision_config
import logging
import time
from .vision import (
    retry_action,
    confirm_selection,
    verify_placement_change,
    handle_vision_error,
    capture_region,
)


def try_targeting_success(
    coords: tuple[int, int],
    targeting_region_1,
    targeting_region_2,
    targeting_threshold,
    max_attempts,
    delay,
    confirm_fn,
) -> bool:
    """
    Attempt a targeting click at the given coordinates and verify success by checking for UI changes in two regions, retrying up to max_attempts with delay between attempts.
    
    Parameters:
        coords (tuple[int, int]): (x, y) coordinates to click.
        targeting_region_1: First screen region to capture and compare for a post-click change.
        targeting_region_2: Second screen region to capture and compare for a post-click change.
        targeting_threshold (float): Threshold passed to confirm_fn to decide if a region changed sufficiently.
        max_attempts (int): Number of click-and-check attempts to perform.
        delay (float): Delay after each click before capturing post-action regions and between attempts.
        confirm_fn (Callable): Function that compares two region images and the threshold, returning (bool, details).
    
    Returns:
        bool: True if either region confirms targeting success within the allowed attempts, False otherwise.
    """
    pre_img_1 = None
    pre_img_2 = None
    try:
        pre_img_1 = capture_region(targeting_region_1)
        pre_img_2 = capture_region(targeting_region_2)
    except Exception:
        logging.exception("Error capturing pre-click regions for targeting.")

    for _ in range(1, max_attempts + 1):
        # Perform the click action to select the target
        move_and_click(coords[0], coords[1], delay=delay)
        # Check region 1
        post_img_1 = None
        try:
            post_img_1 = capture_region(targeting_region_1)
        except Exception:
            logging.exception("Error capturing region 1 for targeting.")
        success_1 = False
        if pre_img_1 is not None and post_img_1 is not None:
            success_1, _ = confirm_fn(
                pre_img_1, post_img_1, targeting_threshold
            )
        # Check region 2
        post_img_2 = None
        try:
            post_img_2 = capture_region(targeting_region_2)
        except Exception:
            logging.exception("Error capturing region 2 for targeting.")
        success_2 = False
        if pre_img_2 is not None and post_img_2 is not None:
            success_2, _ = confirm_fn(
                pre_img_2, post_img_2, targeting_threshold
            )
        if success_1 or success_2:
            return True
        time.sleep(delay)
    return False


def get_regions_for_monkey():
    """
    Retrieve vision regions and thresholds used for monkey selection and placement.
    
    Returns:
        dict: Mapping with keys:
            - max_attempts (int): Maximum targeting attempts (default 3).
            - select_threshold (float): Threshold for confirming selection (default 40.0).
            - place_threshold (float): Threshold for confirming placement (default 85.0).
            - select_region (tuple): Region for selection checks as returned by rect_to_region (default rect [925, 800, 1135, 950]).
            - place_region_1 (tuple): Primary placement verification region (default rect [35, 65, 415, 940]).
            - place_region_2 (tuple): Secondary placement verification region (default rect [1260, 60, 1635, 940]).
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
    Retrieve vision regions and thresholds used for hero selection and placement.
    
    Returns:
        dict: Mapping with keys:
            - max_attempts (int): Number of placement attempts to try.
            - select_threshold (float): Threshold used to confirm hero selection.
            - place_threshold (float): Threshold used to confirm hero placement.
            - select_region (tuple): Region rectangle for selection, converted by `rect_to_region`.
            - place_region_1 (tuple): First region rectangle to verify placement, converted by `rect_to_region`.
            - place_region_2 (tuple): Second region rectangle to verify placement, converted by `rect_to_region`.
    """
    vision = get_vision_config()
    from .vision import rect_to_region

    return {
        "max_attempts": vision.get("max_attempts", 3),
        "select_threshold": vision.get("select_threshold", 40.0),
        "place_threshold": vision.get("place_threshold", 85.0),
        "select_region": rect_to_region(
            vision.get("select_region", [935, 800, 1135, 950])
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
    Place a monkey by selecting it with a keyboard key and clicking the specified screen coordinates, verifying placement via vision and retrying as configured.
    
    This function sends the selection key, moves the cursor to the configured resting spot, attempts placement at `coords` with vision-based verification (including retries), and invokes the configured vision error handler on failure. It performs real input actions and logs failures instead of raising exceptions.
    
    Parameters:
        coords (tuple[int, int]): Target screen (x, y) coordinates for the monkey placement.
        monkey_key (str): Keyboard key or key sequence used to select the monkey before placement.
        delay (float): Seconds to wait after sending the selection key and between attempts (default 0.2).
    """
    try:
        import keyboard

        cursor_resting_spot()  # Move cursor to resting spot before action

        regions = get_regions_for_monkey()
        max_attempts = regions["max_attempts"]
        select_threshold = regions["select_threshold"]
        targeting_threshold = regions["place_threshold"]
        select_region = regions["select_region"]
        targeting_region_1 = regions["place_region_1"]
        targeting_region_2 = regions["place_region_2"]

        def select_monkey():
            """
            Send the configured monkey selection key to the input system and pause for the configured delay.
            """
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

        targeting_success = try_targeting_success(
            coords,
            targeting_region_1,
            targeting_region_2,
            targeting_threshold,
            max_attempts,
            delay,
            verify_placement_change,
        )
        if not targeting_success:
            logging.error(f"Monkey targeting failed at {coords}")
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
    Selects a hero by keyboard key and places it at the given screen coordinates while verifying selection and placement with vision checks.
    
    Parameters:
        coords (tuple[int, int]): Screen (x, y) coordinates where the hero should be placed.
        hero_key (str): Keyboard key used to select the hero.
        delay (float): Seconds to wait after pressing the key and before performing placement actions (default 0.2).
    """
    try:
        import keyboard

        cursor_resting_spot()  # Move cursor to resting spot before action

        regions = get_regions_for_hero()
        max_attempts = regions["max_attempts"]
        select_threshold = regions["select_threshold"]
        targeting_threshold = regions["place_threshold"]
        select_region = regions["select_region"]
        targeting_region_1 = regions["place_region_1"]
        targeting_region_2 = regions["place_region_2"]

        def select_hero():
            """
            Presses and releases the configured hero key to select a hero.
            
            Holds the key down for the configured delay before releasing it; uses `hero_key` and `delay` from the enclosing scope.
            """
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

        targeting_success = try_targeting_success(
            coords,
            targeting_region_1,
            targeting_region_2,
            targeting_threshold,
            max_attempts,
            delay,
            verify_placement_change,
        )
        if not targeting_success:
            logging.error(f"Hero targeting failed at {coords}")
            handle_vision_error()
            return
    except Exception:
        logging.exception(
            f"Failed to place hero at {coords} with key {hero_key}"
        )