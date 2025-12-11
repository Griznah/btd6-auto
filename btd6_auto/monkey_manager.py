"""
Handles selection and placement of monkeys and heroes.
"""

from .config_utils import get_vision_config
import logging
import time
import numpy as np
from .vision import (
    retry_action,
    confirm_selection,
    verify_image_difference,
    handle_vision_error,
    capture_region,
)
from .input import move_and_click, cursor_resting_spot
from .debug_manager import DebugManager

# Module-level debug manager for monkey placement operations
_DEBUG_MANAGER = DebugManager({})


def try_targeting_success(
    coords: tuple[int, int],
    targeting_region_1,
    targeting_region_2,
    targeting_threshold,
    max_attempts,
    delay,
    confirm_fn,
) -> tuple[bool, str | None, np.ndarray | None]:
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
        tuple: (success: bool, region_id: str | None, pre_img: np.ndarray | None)
            - success (bool): True if either region confirms targeting success within the allowed attempts, False otherwise.
            - region_id (str | None): 'region1' or 'region2' if success, None otherwise.
            - pre_img (np.ndarray | None): The pre-captured image of the successful region, or None if not successful.
    """
    operation_id = _DEBUG_MANAGER.start_performance_tracking("targeting_success")
    _DEBUG_MANAGER.log_detailed("MonkeyManager", "Starting targeting success attempt",
                              coords=coords, max_attempts=max_attempts,
                              targeting_threshold=targeting_threshold, delay=delay)

    pre_img_1 = None
    pre_img_2 = None
    try:
        pre_capture_id = _DEBUG_MANAGER.start_performance_tracking("pre_capture_targeting")
        pre_img_1 = capture_region(targeting_region_1)
        pre_img_2 = capture_region(targeting_region_2)
        _DEBUG_MANAGER.finish_performance_tracking(pre_capture_id)
        _DEBUG_MANAGER.log_verbose("MonkeyManager", "Pre-targeting images captured",
                                  data={
                                      "region_1_shape": pre_img_1.shape if pre_img_1 is not None else None,
                                      "region_2_shape": pre_img_2.shape if pre_img_2 is not None else None
                                  })
    except Exception as e:
        _DEBUG_MANAGER.log_error("MonkeyManager", e,
                                context={"operation": "pre_capture", "coords": coords})
        logging.exception("Error capturing pre-click regions for targeting.")

    for attempt in range(1, max_attempts + 1):
        _DEBUG_MANAGER.add_checkpoint(operation_id, f"targeting_attempt_{attempt}")
        _DEBUG_MANAGER.log_detailed("MonkeyManager", f"Targeting attempt {attempt}/{max_attempts}",
                                  attempt=attempt, max_attempts=max_attempts, coords=coords)

        click_start = time.time()
        move_and_click(coords[0], coords[1], delay=delay)
        click_time = time.time() - click_start

        _DEBUG_MANAGER.log_verbose("MonkeyManager", "Targeting click executed",
                                  data={"attempt": attempt, "click_time": click_time, "coords": coords})

        # Check region 1
        region1_capture_id = _DEBUG_MANAGER.start_performance_tracking("region1_capture")
        post_img_1 = None
        try:
            post_img_1 = capture_region(targeting_region_1)
        except Exception as e:
            _DEBUG_MANAGER.log_error("MonkeyManager", e,
                                    context={"operation": "region1_capture", "attempt": attempt, "coords": coords})
            logging.exception("Error capturing region 1 for targeting.")
        region1_time = _DEBUG_MANAGER.finish_performance_tracking(region1_capture_id)

        success_1 = False
        diff_1 = None
        if pre_img_1 is not None and post_img_1 is not None:
            success_1, diff_1 = confirm_fn(pre_img_1, post_img_1, targeting_threshold)
            _DEBUG_MANAGER.log_vision_result("targeting_region1", success_1,
                                            confidence=diff_1,
                                            processing_time=region1_time,
                                            match_info={
                                                "attempt": attempt,
                                                "coords": coords,
                                                "threshold": targeting_threshold
                                            })

        if success_1:
            _DEBUG_MANAGER.finish_performance_tracking(operation_id)
            _DEBUG_MANAGER.log_action("targeting_success", f"region1_at_{coords}", True,
                                    details={"attempt": attempt, "region": "region1", "diff": diff_1})
            return True, "region1", post_img_1

        # Check region 2
        region2_capture_id = _DEBUG_MANAGER.start_performance_tracking("region2_capture")
        post_img_2 = None
        try:
            post_img_2 = capture_region(targeting_region_2)
        except Exception as e:
            _DEBUG_MANAGER.log_error("MonkeyManager", e,
                                    context={"operation": "region2_capture", "attempt": attempt, "coords": coords})
            logging.exception("Error capturing region 2 for targeting.")
        region2_time = _DEBUG_MANAGER.finish_performance_tracking(region2_capture_id)

        success_2 = False
        diff_2 = None
        if pre_img_2 is not None and post_img_2 is not None:
            success_2, diff_2 = confirm_fn(pre_img_2, post_img_2, targeting_threshold)
            _DEBUG_MANAGER.log_vision_result("targeting_region2", success_2,
                                            confidence=diff_2,
                                            processing_time=region2_time,
                                            match_info={
                                                "attempt": attempt,
                                                "coords": coords,
                                                "threshold": targeting_threshold
                                            })

        if success_2:
            _DEBUG_MANAGER.finish_performance_tracking(operation_id)
            _DEBUG_MANAGER.log_action("targeting_success", f"region2_at_{coords}", True,
                                    details={"attempt": attempt, "region": "region2", "diff": diff_2})
            return True, "region2", post_img_2

        time.sleep(delay)

    total_time = _DEBUG_MANAGER.finish_performance_tracking(operation_id)
    _DEBUG_MANAGER.log_error("MonkeyManager", Exception("Targeting failed after all attempts"),
                            context={
                                "coords": coords,
                                "max_attempts": max_attempts,
                                "targeting_threshold": targeting_threshold,
                                "total_time": total_time
                            })
    return False, None, None


def get_regions_for_monkey():
    """
    Retrieve vision regions and thresholds used for monkey selection and placement.

    Returns:
        dict: Mapping with keys:
            - max_attempts (int): Maximum targeting attempts (default 3).
            - select_threshold (float): Threshold for confirming selection (default 40.0).
            - place_threshold (float): Threshold for confirming placement (default 85.0).
            - select_region (tuple): Region for selection checks as returned by rect_to_region (default rect [925, 800, 1135, 950]).
            - target_region_1 (tuple): Primary placement verification region (default rect [35, 65, 415, 940]).
            - target_region_2 (tuple): Secondary placement verification region (default rect [1260, 60, 1635, 940]).
    """
    vision = get_vision_config()
    from .vision import rect_to_region

    return {
        "max_attempts": vision.get("max_attempts", 3),
        "select_threshold": vision.get("select_threshold", 40.0),
        "place_threshold": vision.get("place_threshold", 85.0),
        "select_region": rect_to_region(vision.get("select_region", [925, 800, 1135, 950])),
        "target_region_1": rect_to_region(vision.get("target_region_1", [35, 65, 415, 940])),
        "target_region_2": rect_to_region(
            vision.get("target_region_2", [1260, 60, 1635, 940])
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
            - target_region_1 (tuple): First region rectangle to verify placement, converted by `rect_to_region`.
            - target_region_2 (tuple): Second region rectangle to verify placement, converted by `rect_to_region`.
    """
    vision = get_vision_config()
    from .vision import rect_to_region

    return {
        "max_attempts": vision.get("max_attempts", 3),
        "select_threshold": vision.get("select_threshold", 40.0),
        "place_threshold": vision.get("place_threshold", 85.0),
        "select_region": rect_to_region(vision.get("select_region", [935, 800, 1135, 950])),
        "target_region_1": rect_to_region(vision.get("target_region_1", [35, 65, 415, 940])),
        "target_region_2": rect_to_region(
            vision.get("target_region_2", [1260, 60, 1635, 940])
        ),
    }


def select_monkey(monkey_key: str, delay: float = 0.2) -> None:
    """
    Send the configured monkey selection key to the input system and pause for the configured delay.
    Can be called from other modules.
    """
    import keyboard

    keyboard.send(monkey_key)
    time.sleep(delay)


def place_monkey(coords: tuple[int, int], monkey_key: str, delay: float = 0.2) -> None:
    """
    Place a monkey by selecting it with a keyboard key and clicking the specified screen coordinates, verifying placement via vision and retrying as configured.

    This function sends the selection key, moves the cursor to the configured resting spot, attempts placement at `coords` with vision-based verification (including retries), and invokes the configured vision error handler on failure. It performs real input actions and logs failures instead of raising exceptions.

    Parameters:
        coords (tuple[int, int]): Target screen (x, y) coordinates for the monkey placement.
        monkey_key (str): Keyboard key or key sequence used to select the monkey before placement.
        delay (float): Seconds to wait after sending the selection key and between attempts (default 0.2).
    """
    operation_id = _DEBUG_MANAGER.start_performance_tracking("place_monkey")
    _DEBUG_MANAGER.log_detailed("MonkeyManager", "Starting monkey placement",
                              coords=coords, monkey_key=monkey_key, delay=delay)

    try:
        cursor_start = time.time()
        cursor_resting_spot()  # Move cursor to resting spot before action
        cursor_time = time.time() - cursor_start
        _DEBUG_MANAGER.log_verbose("MonkeyManager", "Cursor moved to resting spot",
                                  data={"cursor_time": cursor_time})

        regions = get_regions_for_monkey()
        max_attempts = regions["max_attempts"]
        select_threshold = regions["select_threshold"]
        targeting_threshold = regions["place_threshold"]
        select_region = regions["select_region"]
        targeting_region_1 = regions["target_region_1"]
        targeting_region_2 = regions["target_region_2"]

        _DEBUG_MANAGER.log_verbose("MonkeyManager", "Retrieved monkey regions",
                                  data={
                                      "max_attempts": max_attempts,
                                      "select_threshold": select_threshold,
                                      "targeting_threshold": targeting_threshold
                                  })

        # Monkey selection phase
        selection_id = _DEBUG_MANAGER.start_performance_tracking("monkey_selection")
        _DEBUG_MANAGER.log_detailed("MonkeyManager", "Starting monkey selection",
                                  monkey_key=monkey_key, select_threshold=select_threshold)

        selection_success = retry_action(
            lambda: select_monkey(monkey_key, delay),
            select_region,
            select_threshold,
            max_attempts=max_attempts,
            delay=delay,
            confirm_fn=confirm_selection,
            debug_manager=_DEBUG_MANAGER,
            operation_name="monkey_selection",
        )

        selection_time = _DEBUG_MANAGER.finish_performance_tracking(selection_id)

        if not selection_success:
            error_msg = f"Monkey selection failed for key {monkey_key}"
            _DEBUG_MANAGER.log_error("MonkeyManager", Exception(error_msg),
                                    context={
                                        "coords": coords,
                                        "monkey_key": monkey_key,
                                        "max_attempts": max_attempts,
                                        "selection_time": selection_time
                                    })
            logging.error(error_msg)
            handle_vision_error()
            return

        _DEBUG_MANAGER.log_action("monkey_selection", monkey_key, True,
                                details={"coords": coords, "selection_time": selection_time})

        # Targeting/placement phase
        targeting_id = _DEBUG_MANAGER.start_performance_tracking("monkey_targeting")
        _DEBUG_MANAGER.log_detailed("MonkeyManager", "Starting monkey targeting",
                                  coords=coords, targeting_threshold=targeting_threshold)

        targeting_success, region_id, targeted_img = try_targeting_success(
            coords,
            targeting_region_1,
            targeting_region_2,
            targeting_threshold,
            max_attempts,
            delay,
            verify_image_difference,
        )

        targeting_time = _DEBUG_MANAGER.finish_performance_tracking(targeting_id)

        if not targeting_success:
            error_msg = f"Monkey targeting failed at {coords}"
            _DEBUG_MANAGER.log_error("MonkeyManager", Exception(error_msg),
                                    context={
                                        "coords": coords,
                                        "monkey_key": monkey_key,
                                        "max_attempts": max_attempts,
                                        "targeting_threshold": targeting_threshold,
                                        "targeting_time": targeting_time
                                    })
            logging.error(error_msg)
            handle_vision_error()
            return

        total_time = _DEBUG_MANAGER.finish_performance_tracking(operation_id)
        _DEBUG_MANAGER.log_action("place_monkey", f"monkey_{monkey_key}", True,
                                details={
                                    "coords": coords,
                                    "region_id": region_id,
                                    "selection_time": selection_time,
                                    "targeting_time": targeting_time,
                                    "total_time": total_time
                                })

    except Exception as e:
        _DEBUG_MANAGER.log_error("MonkeyManager", e,
                                context={"coords": coords, "monkey_key": monkey_key, "delay": delay})
        logging.exception(f"Failed to place monkey at {coords} with key {monkey_key}")


def select_hero(hero_key: str, delay: float = 0.2) -> None:
    """
    Presses and releases the configured hero key to select a hero.
    Can be called from other modules.
    """
    import keyboard

    keyboard.press(hero_key)
    time.sleep(delay)
    keyboard.release(hero_key)


def place_hero(coords: tuple[int, int], hero_key: str, delay: float = 0.2) -> None:
    """
    Selects a hero by keyboard key and places it at the given screen coordinates while verifying selection and placement with vision checks.

    Parameters:
        coords (tuple[int, int]): Screen (x, y) coordinates where the hero should be placed.
        hero_key (str): Keyboard key used to select the hero.
        delay (float): Seconds to wait after pressing the key and before performing placement actions (default 0.2).
    """
    operation_id = _DEBUG_MANAGER.start_performance_tracking("place_hero")
    _DEBUG_MANAGER.log_detailed("MonkeyManager", "Starting hero placement",
                              coords=coords, hero_key=hero_key, delay=delay)

    try:
        cursor_start = time.time()
        cursor_resting_spot()  # Move cursor to resting spot before action
        cursor_time = time.time() - cursor_start
        _DEBUG_MANAGER.log_verbose("MonkeyManager", "Cursor moved to resting spot for hero",
                                  data={"cursor_time": cursor_time})

        regions = get_regions_for_hero()
        max_attempts = regions["max_attempts"]
        select_threshold = regions["select_threshold"]
        targeting_threshold = regions["place_threshold"]
        select_region = regions["select_region"]
        targeting_region_1 = regions["target_region_1"]
        targeting_region_2 = regions["target_region_2"]

        _DEBUG_MANAGER.log_verbose("MonkeyManager", "Retrieved hero regions",
                                  data={
                                      "max_attempts": max_attempts,
                                      "select_threshold": select_threshold,
                                      "targeting_threshold": targeting_threshold
                                  })

        # Hero selection phase
        selection_id = _DEBUG_MANAGER.start_performance_tracking("hero_selection")
        _DEBUG_MANAGER.log_detailed("MonkeyManager", "Starting hero selection",
                                  hero_key=hero_key, select_threshold=select_threshold)

        selection_success = retry_action(
            lambda: select_hero(hero_key, delay),
            select_region,
            select_threshold,
            max_attempts=max_attempts,
            delay=delay,
            confirm_fn=confirm_selection,
            debug_manager=_DEBUG_MANAGER,
            operation_name="hero_selection",
        )

        selection_time = _DEBUG_MANAGER.finish_performance_tracking(selection_id)

        if not selection_success:
            error_msg = f"Hero selection failed for key {hero_key}"
            _DEBUG_MANAGER.log_error("MonkeyManager", Exception(error_msg),
                                    context={
                                        "coords": coords,
                                        "hero_key": hero_key,
                                        "max_attempts": max_attempts,
                                        "selection_time": selection_time
                                    })
            logging.error(error_msg)
            handle_vision_error()
            return

        _DEBUG_MANAGER.log_action("hero_selection", hero_key, True,
                                details={"coords": coords, "selection_time": selection_time})

        # Targeting/placement phase
        targeting_id = _DEBUG_MANAGER.start_performance_tracking("hero_targeting")
        _DEBUG_MANAGER.log_detailed("MonkeyManager", "Starting hero targeting",
                                  coords=coords, targeting_threshold=targeting_threshold)

        targeting_success, region_id, targeted_img = try_targeting_success(
            coords,
            targeting_region_1,
            targeting_region_2,
            targeting_threshold,
            max_attempts,
            delay,
            verify_image_difference,
        )

        targeting_time = _DEBUG_MANAGER.finish_performance_tracking(targeting_id)

        if not targeting_success:
            error_msg = f"Hero targeting failed at {coords}"
            _DEBUG_MANAGER.log_error("MonkeyManager", Exception(error_msg),
                                    context={
                                        "coords": coords,
                                        "hero_key": hero_key,
                                        "max_attempts": max_attempts,
                                        "targeting_threshold": targeting_threshold,
                                        "targeting_time": targeting_time
                                    })
            logging.error(error_msg)
            handle_vision_error()
            return

        total_time = _DEBUG_MANAGER.finish_performance_tracking(operation_id)
        _DEBUG_MANAGER.log_action("place_hero", f"hero_{hero_key}", True,
                                details={
                                    "coords": coords,
                                    "region_id": region_id,
                                    "selection_time": selection_time,
                                    "targeting_time": targeting_time,
                                    "total_time": total_time
                                })

    except Exception as e:
        _DEBUG_MANAGER.log_error("MonkeyManager", e,
                                context={"coords": coords, "hero_key": hero_key, "delay": delay})
        logging.exception(f"Failed to place hero at {coords} with key {hero_key}")
