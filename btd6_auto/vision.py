"""
Screen capture with BetterCam and image recognition with OpenCV.
Functions for setting round state, reading currency via OCR, and finding elements on screen.
Will include error handling, logging and retry logic.
"""

import pytesseract
from PIL import Image

import cv2
import numpy as np
import logging
import os
import time
import math
from datetime import datetime
import keyboard
import bettercam

# Use ConfigLoader for config loading
from .config_loader import ConfigLoader
from .debug_manager import DebugManager


def make_unique_filename(prefix: str, folder: str = "screenshots") -> str:
    """
    Generate a unique filename with the given prefix and current timestamp.

    Parameters:
        prefix (str): Prefix for the filename.
        folder (str): Folder to save the file in.

    Returns:
        str: Unique filename in the format '{folder}\\{prefix}_{timestamp}.png'.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{prefix}_{timestamp}.png"
    return os.path.join(folder, filename)


def rect_to_region(rect):
    """
    Convert a rectangle from (left, top, right, bottom) to (left, top, width, height).

    Parameters:
        rect (tuple | list): Four numeric values in the order (left, top, right, bottom).

    Returns:
        tuple: A 4-tuple (left, top, width, height) where width = right - left and height = bottom - top.

    Raises:
        ValueError: If `rect` does not contain exactly four values or if computed width or height is less than or equal to zero.
    """
    if len(rect) != 4:
        raise ValueError(f"rect_to_region expects 4 values, got {rect}")
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid rectangle dimensions: {rect}")
    return (left, top, width, height)


# Vision-based error handling helpers for monkey selection/placement
def capture_region(region):
    """
    Capture a screenshot of a rectangular region from the screen using the module's BetterCam.

    Parameters:
        region (tuple): (left, top, width, height) coordinates of the capture rectangle. Coordinates must lie within a 1920x1080 screen.

    Returns:
        numpy.ndarray or None: BGR image array for the captured region, or `None` if the region is invalid or no frame could be captured.
    """
    # Only start performance tracking if debug manager is enabled
    # and not in verbose mode (to avoid interfering with timing-sensitive operations)
    if _DEBUG_MANAGER.enabled and _DEBUG_MANAGER.level.value < 3:
        operation_id = _DEBUG_MANAGER.start_performance_tracking("capture_region")
        _DEBUG_MANAGER.log_verbose(
            "Vision",
            "Starting region capture",
            data={"region": region, "max_retries": _CAPTURE_RETRIES},
        )
    else:
        operation_id = None

    left, top, width, height = region
    right = left + width
    bottom = top + height
    bettercam_region = (left, top, right, bottom)

    # Validate region bounds for 1920x1080 screen
    if not (0 <= left < right <= 1920 and 0 <= top < bottom <= 1080):
        error_msg = (
            f"capture_region: Invalid region {bettercam_region} (must be within 1920x1080)"
        )
        _DEBUG_MANAGER.log_error(
            "Vision",
            Exception(error_msg),
            context={"region": region, "bettercam_region": bettercam_region},
        )
        logging.error(error_msg)
        return None

    cam = _CAMERA
    img = None

    for attempt in range(_CAPTURE_RETRIES):
        # Skip debug checkpoints in verbose mode to reduce overhead
        if operation_id is not None:
            _DEBUG_MANAGER.add_checkpoint(operation_id, f"capture_attempt_{attempt + 1}")

        try:
            img = cam.grab(region=bettercam_region)
            # Only log verbose success messages if not in verbose mode
            if img is not None and operation_id is not None:
                _DEBUG_MANAGER.log_verbose(
                    "Vision",
                    f"Frame captured on attempt {attempt + 1}",
                    data={
                        "attempt": attempt + 1,
                        "shape": img.shape if img is not None else None,
                    },
                )
        except Exception as e:
            # Always log errors, but reduce context in verbose mode
            if _DEBUG_MANAGER.enabled and _DEBUG_MANAGER.level.value < 3:
                _DEBUG_MANAGER.log_error(
                    "Vision", e, context={"region": bettercam_region, "attempt": attempt + 1}
                )
            logging.exception("BetterCam grab error in capture_region")
            img = None

        if img is not None:
            break

        logging.info(
            f"capture_region: No new frame, retrying ({attempt + 1}/{_CAPTURE_RETRIES}) after {_CAPTURE_DELAY}s..."
        )
        time.sleep(_CAPTURE_DELAY)

    if img is None:
        error_msg = f"capture_region: No frame captured after {_CAPTURE_RETRIES} attempts."
        if operation_id is not None:
            _DEBUG_MANAGER.log_basic("Vision", error_msg, "warning")
        logging.warning(error_msg)
        return None

    # Handle BGRA/RGBA images and convert to BGR
    original_shape = img.shape
    if img.ndim == 3 and img.shape[2] == 4:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        conversion = "BGRA->BGR"
    elif img.ndim == 3 and img.shape[2] == 3:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        conversion = "RGB->BGR"
    else:
        img_bgr = img
        conversion = "none"

    # Only finish performance tracking if it was started
    if operation_id is not None:
        processing_time = _DEBUG_MANAGER.finish_performance_tracking(operation_id)
        _DEBUG_MANAGER.log_vision_result(
            "capture_region",
            True,
            processing_time=processing_time,
            match_info={
                "region": region,
                "original_shape": original_shape,
                "final_shape": img_bgr.shape,
                "conversion": conversion,
            },
        )

    return img_bgr


def calculate_image_difference(img1, img2):
    """
    Compute the percentage of differing pixels between two images.

    Parameters:
        img1 (np.ndarray): First image array.
        img2 (np.ndarray): Second image array; must have the same shape as `img1`.

    Returns:
        float: Percentage of pixels that differ between the images, in the range 0.0 to 100.0. Returns 100.0 if the images have different shapes.
    """
    operation_id = _DEBUG_MANAGER.start_performance_tracking("calculate_image_difference")

    shape1 = img1.shape if img1 is not None else None
    shape2 = img2.shape if img2 is not None else None

    _DEBUG_MANAGER.log_verbose(
        "Vision", "Calculating image difference", data={"shape1": shape1, "shape2": shape2}
    )

    if img1.shape != img2.shape:
        error_msg = "Image shapes do not match for comparison."
        _DEBUG_MANAGER.log_error(
            "Vision", Exception(error_msg), context={"shape1": shape1, "shape2": shape2}
        )
        logging.error(error_msg)
        return 100.0

    diff = cv2.absdiff(img1, img2)
    nonzero = np.count_nonzero(diff)
    total = diff.size
    percent_diff = (nonzero / total) * 100

    processing_time = _DEBUG_MANAGER.finish_performance_tracking(operation_id)
    _DEBUG_MANAGER.log_vision_result(
        "calculate_image_difference",
        True,
        confidence=percent_diff,
        processing_time=processing_time,
        match_info={
            "nonzero_pixels": int(nonzero),
            "total_pixels": int(total),
            "percent_diff": percent_diff,
        },
    )

    return percent_diff


def verify_image_difference(pre_img, post_img, threshold=85.0):
    """
    Determine whether the visual difference between two images meets a minimum percent threshold.

    Parameters:
        pre_img (np.ndarray): Image captured before the action.
        post_img (np.ndarray): Image captured after the action.
        threshold (float): Minimum percent difference required to consider the placement change successful.

    Returns:
        success (bool): `true` if the percent difference is greater than or equal to `threshold`, `false` otherwise.
        percent_diff (float): Percentage of pixels that differ between `pre_img` and `post_img`.
    """
    operation_id = _DEBUG_MANAGER.start_performance_tracking("verify_image_difference")
    _DEBUG_MANAGER.log_detailed("Vision", "Verifying image difference", threshold=threshold)

    percent_diff = calculate_image_difference(pre_img, post_img)
    success = percent_diff >= threshold

    processing_time = _DEBUG_MANAGER.finish_performance_tracking(operation_id)
    _DEBUG_MANAGER.log_vision_result(
        "verify_image_difference",
        success,
        confidence=percent_diff,
        processing_time=processing_time,
        match_info={
            "threshold": threshold,
            "percent_diff": percent_diff,
            "verification_type": "placement",
        },
    )

    logging.debug(f"Placement diff: {percent_diff:.2f}% (threshold: {threshold})")
    return success, percent_diff


def confirm_selection(pre_img, post_img, threshold=40.0):
    """
    Determine whether a selection change occurred by comparing two images.

    Parameters:
        pre_img (np.ndarray): Image captured before the action.
        post_img (np.ndarray): Image captured after the action.
        threshold (float): Minimum percent difference required to consider the selection confirmed.

    Returns:
        (bool, float): First element is `true` if the percent difference is greater than or equal to `threshold`, `false` otherwise; second element is the percent difference between the images.
    """
    operation_id = _DEBUG_MANAGER.start_performance_tracking("confirm_selection")
    _DEBUG_MANAGER.log_detailed("Vision", "Confirming selection change", threshold=threshold)

    percent_diff = calculate_image_difference(pre_img, post_img)
    success = percent_diff >= threshold

    processing_time = _DEBUG_MANAGER.finish_performance_tracking(operation_id)
    _DEBUG_MANAGER.log_vision_result(
        "confirm_selection",
        success,
        confidence=percent_diff,
        processing_time=processing_time,
        match_info={
            "threshold": threshold,
            "percent_diff": percent_diff,
            "verification_type": "selection",
        },
    )

    logging.info(f"Selection diff: {percent_diff:.2f}% (threshold: {threshold})")
    return success, percent_diff


def retry_action(
    action_fn,
    region,
    threshold,
    max_attempts=3,
    delay=0.3,
    confirm_fn=None,
    *args,
    **kwargs,
):
    """
    Retry an action until a vision-based confirmation indicates success or the maximum attempts are exhausted.

    Parameters:
        action_fn (callable): Function that performs the action to be verified (e.g., a selection or placement). It will be called with `*args` and `**kwargs`.
        region (tuple): Screen region used for pre- and post-action captures, typically (left, top, width, height).
        threshold (float): Percentage difference threshold required by `confirm_fn` to consider the action successful.
        max_attempts (int): Maximum number of attempts to perform the action and confirm it.
        delay (float): Seconds to wait after performing the action before taking the post-action capture.
        confirm_fn (callable): Function that compares pre- and post-action images and returns a tuple `(success: bool, percent_diff: float)`.
        *args: Positional arguments forwarded to `action_fn`.
        **kwargs: Keyword arguments forwarded to `action_fn`.

    Returns:
        bool: `True` if the action was confirmed successful within the allotted attempts, `False` otherwise.
    """
    operation_id = _DEBUG_MANAGER.start_performance_tracking("retry_action")
    _DEBUG_MANAGER.log_detailed(
        "Vision",
        "Starting retry action sequence",
        max_attempts=max_attempts,
        threshold=threshold,
        region=region,
        delay=delay,
        action_fn=action_fn.__name__ if hasattr(action_fn, "__name__") else str(action_fn),
    )

    for attempt in range(1, max_attempts + 1):
        _DEBUG_MANAGER.add_checkpoint(operation_id, f"attempt_{attempt}")
        _DEBUG_MANAGER.log_detailed(
            "Vision",
            f"Retry action attempt {attempt}/{max_attempts}",
            attempt=attempt,
            max_attempts=max_attempts,
        )

        pre_capture_id = _DEBUG_MANAGER.start_performance_tracking("pre_capture")
        pre_img = capture_region(region)
        _DEBUG_MANAGER.finish_performance_tracking(pre_capture_id)

        if pre_img is None:
            _DEBUG_MANAGER.log_basic(
                "Vision", f"Attempt {attempt}: pre_img capture failed", "warning"
            )
            logging.warning(f"Attempt {attempt}: pre_img capture failed")
            continue

        action_start = time.time()
        action_fn(*args, **kwargs)
        action_time = time.time() - action_start
        _DEBUG_MANAGER.log_verbose(
            "Vision", "Action executed", data={"attempt": attempt, "action_time": action_time}
        )

        time.sleep(delay)

        post_capture_id = _DEBUG_MANAGER.start_performance_tracking("post_capture")
        post_img = capture_region(region)
        _DEBUG_MANAGER.finish_performance_tracking(post_capture_id)

        if post_img is None:
            _DEBUG_MANAGER.log_basic(
                "Vision", f"Attempt {attempt}: post_img capture failed", "warning"
            )
            logging.warning(f"Attempt {attempt}: post_img capture failed")
            continue

        verification_id = _DEBUG_MANAGER.start_performance_tracking("action_verification")
        success, percent_diff = confirm_fn(pre_img, post_img, threshold)
        verification_time = _DEBUG_MANAGER.finish_performance_tracking(verification_id)

        _DEBUG_MANAGER.log_vision_result(
            f"retry_action_attempt_{attempt}",
            success,
            confidence=percent_diff,
            processing_time=verification_time,
            match_info={
                "attempt": attempt,
                "threshold": threshold,
                "percent_diff": percent_diff,
                "action_fn": action_fn.__name__
                if hasattr(action_fn, "__name__")
                else str(action_fn),
            },
        )

        logging.info(f"Attempt {attempt}: diff={percent_diff:.2f}% success={success}")

        if success:
            _DEBUG_MANAGER.finish_performance_tracking(operation_id)
            _DEBUG_MANAGER.log_action(
                "retry_action",
                f"{action_fn.__name__ if hasattr(action_fn, '__name__') else 'unknown'}",
                True,
                details={"attempts": attempt, "percent_diff": percent_diff},
            )
            return True

    total_time = _DEBUG_MANAGER.finish_performance_tracking(operation_id)
    error_msg = f"Action failed after {max_attempts} attempts."
    _DEBUG_MANAGER.log_error(
        "Vision",
        Exception(error_msg),
        context={
            "max_attempts": max_attempts,
            "threshold": threshold,
            "region": region,
            "total_time": total_time,
            "action_fn": action_fn.__name__
            if hasattr(action_fn, "__name__")
            else str(action_fn),
        },
    )
    logging.error(error_msg)
    return False


def handle_vision_error():
    """
    Terminate the process after a critical vision failure.

    Logs a critical message and exits the process immediately.
    """
    logging.critical("Max retries reached. Exiting automation.")
    # Add any cleanup logic here
    os._exit(1)


try:
    _GLOBAL_CONFIG = ConfigLoader.load_global_config()
    _CAPTURE_RETRIES = _GLOBAL_CONFIG.get("image_recognition", {}).get(
        "capture_screen_retry", 2
    )
    _CAPTURE_DELAY = _GLOBAL_CONFIG.get("image_recognition", {}).get(
        "capture_screen_delay", 1.0
    )

except Exception as e:
    logging.warning(f"Failed to load global config via ConfigLoader: {e}")
    raise

# Module-level BetterCam instance
# This is a hard requirement for baseline functionality, we cannot function without it
_CAMERA = bettercam.create()

# Module-level debug manager for vision operations
_DEBUG_MANAGER = DebugManager(_GLOBAL_CONFIG.get("debug", {}))


def _find_in_region(template_path: str, region: tuple) -> bool:
    """
    Check if a template image is present in a given screen region using OpenCV template matching.

    Parameters:
        template_path (str): Path to the template image file.
        region (tuple): (left, top, right, bottom) coordinates of the region to search.

    Returns:
        bool: True if the template is found with sufficient confidence, False otherwise.
    """
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        logging.error(f"Template image not found: {template_path}")
        return False
    left, top, right, bottom = region
    width, height = right - left, bottom - top
    _, screen_gray = capture_screen(region=(left, top, width, height))
    if screen_gray is None:
        return False
    res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    threshold = 0.75
    return max_val >= threshold


def set_round_state(
    state: str,
    region: tuple = (1768, 947, 1900, 1069),
    max_retries: int = None,
    delay: float = None,
    find_in_region=None,
) -> bool:
    """
    Ensure the game's visual round state ("fast", "slow", or "start") is active, toggling speed as needed.

    Parameters:
        state (str): Desired state; one of "fast", "slow", or "start".
        region (tuple): (left, top, right, bottom) coordinates defining the search region for state indicators.
        max_retries (int, optional): Maximum number of attempts to verify/set the state. If None, a default is read from global configuration.
        delay (float, optional): Seconds to wait between attempts. If None, a default is read from global configuration.
        find_in_region (callable, optional): Optional injected function for template detection (used for testing or mocking). Expected to accept a template path and region and to return either a boolean or a tuple `(found, confidence)`; various call signatures `(template_path, region, threshold)`, `(template_path, region)`, or `(template_path, threshold)` are supported by the adapter.

    Returns:
        bool: `True` if the requested state was detected or set within the allowed attempts, `False` otherwise.
    """
    # Load retry config from global config if not provided
    try:
        global_config = ConfigLoader.load_global_config()
        retries_cfg = global_config.get("automation", {}).get("retries", {})
        default_max_retries = retries_cfg.get("max_retries", 3)
        default_delay = retries_cfg.get("retry_delay", 0.2)
    except Exception:
        default_max_retries = 3
        default_delay = 0.2
    if max_retries is None:
        max_retries = default_max_retries
    if delay is None:
        delay = default_delay

    def _find_in_region_adapter(template_path, threshold=0.75):
        # Adapts test/mocked find_in_region to always accept threshold and return (found, max_val)
        if find_in_region is None:
            # Use the default implementation
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                logging.error(f"Template image not found: {template_path}")
                return False, None
            left, top, right, bottom = region
            width, height = right - left, bottom - top
            _, screen_gray = capture_screen(region=(left, top, width, height))
            if screen_gray is None:
                return False, None
            res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            return max_val >= threshold, max_val
        else:
            # Try to call injected find_in_region with region and threshold if possible
            try:
                result = find_in_region(template_path, region, threshold)
            except TypeError:
                try:
                    result = find_in_region(template_path, region)
                except TypeError:
                    try:
                        result = find_in_region(template_path, threshold)
                    except TypeError:
                        result = find_in_region(template_path)
            if isinstance(result, tuple):
                return result
            return result, None

    # Map state to image filename
    image_map = {
        "fast": "map_fast1080p.png",
        "slow": "map_slow1080p.png",
        "start": "map_start1080p.png",
    }
    if state not in image_map:
        logging.error(f"Invalid state '{state}' for set_round_state.")
        return False

    images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "images")
    img_fast = os.path.join(images_dir, image_map["fast"])
    img_slow = os.path.join(images_dir, image_map["slow"])
    img_start = os.path.join(images_dir, image_map["start"])

    for attempt in range(1, max_retries + 1):
        logging.info(f"[set_round_state] Attempt {attempt} for state '{state}'")
        if state == "fast":
            # we need higher threshold for fast due to high similarity for images
            found, max_val = _find_in_region_adapter(img_fast, threshold=0.93)
            logging.info(f"[set_round_state] FAST: max_val={max_val}")
            if found:
                logging.info("Speed is already FAST.")
                return True
            keyboard.press_and_release("space")
            time.sleep(delay)
        elif state == "slow":
            found, max_val = _find_in_region_adapter(img_slow)
            logging.info(f"[set_round_state] SLOW: max_val={max_val}")
            if found:
                logging.info("Speed is already SLOW.")
                return True
            keyboard.press_and_release("space")
            time.sleep(delay)
        elif state == "start":
            found, max_val = _find_in_region_adapter(img_start)
            logging.info(f"[set_round_state] START: max_val={max_val}")
            # Wait for start button, then ensure speed is fast
            if found:
                logging.info("Start button detected. Ensuring speed is FAST.")
                # Try to set speed to fast
                for _ in range(max_retries):
                    found_fast, max_val_fast = _find_in_region_adapter(
                        img_fast, threshold=0.93
                    )
                    logging.info(
                        f"[set_round_state] FAST (after START): max_val={max_val_fast}"
                    )
                    if found_fast:
                        return True
                    keyboard.press_and_release("space")
                    time.sleep(delay)
                # If unable to set fast, still return True (start is visible)
                return True
            time.sleep(delay)
    logging.warning(
        f"[set_round_state] Failed to set state '{state}' after {max_retries} attempts."
    )
    return False


def _to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Convert an image to grayscale robustly, handling 3-channel (BGR/RGB), 4-channel (BGRA/RGBA), or already grayscale images.
    Parameters:
        image (np.ndarray): Input image.
    Returns:
        np.ndarray: Grayscale image.
    """
    if image is None:
        return None
    if image.ndim == 3:
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        elif image.shape[2] == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def read_currency_amount(region: tuple, debug: bool = False) -> int:
    """
    Reads the currency amount from the defined screen region using OCR.

    Parameters:
        region (tuple): (left, top, right, bottom) coordinates of the region.
        debug (bool): If True, logs the detected value and optionally shows the processed image.

    Returns:
        int: Parsed currency value, or 0 if not found or error.

    Notes:
        - Returns 0 if OCR or camera initialization fails.
        - Handles KeyboardInterrupt gracefully.
        - If OCR result is malformed, returns 0 and logs a warning.
    """

    try:
        # Convert region to capture_region format (left, top, width, height)
        left, top, right, bottom = region
        width = right - left
        height = bottom - top
        capture_region_coords = (left, top, width, height)

        # Use capture_region to get the frame (this applies debug mode optimizations)
        frame = None
        for attempt in range(3):
            frame = capture_region(capture_region_coords)
            if frame is not None:
                break
            logging.info(
                f"No frame captured for currency region (attempt {attempt + 1}/3). Retrying..."
            )
            time.sleep(0.2)

        if frame is None:
            logging.warning("No frame captured for currency region after 3 attempts.")
            return 0

        # Preprocess for OCR
        try:
            cv2.setUseOptimized(True)
            cv2.setNumThreads(1)
            frame_scaled = cv2.resize(
                frame, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC
            )
            gray = _to_grayscale(frame_scaled)
            if gray is None:
                logging.warning("Frame conversion to grayscale failed.")
                return 0
            # Use Otsu's thresholding for robust binarization
            ret, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            ret2, thresh2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # Invert thresholded image
            inverted2 = cv2.bitwise_not(gray)
            # Make black and white from gray
            bw1 = cv2.bilateralFilter(gray, 7, 50, 50)
            kernel = np.ones((2, 2), np.uint8)
            bw1_clean = cv2.morphologyEx(bw1, cv2.MORPH_OPEN, kernel)
            # Convert to RGB for pytesseract
            rgb_bw1 = cv2.cvtColor(bw1, cv2.COLOR_GRAY2RGB)
            rgb_bw1_clean = cv2.cvtColor(bw1_clean, cv2.COLOR_GRAY2RGB)
            rgb_inverted2 = cv2.cvtColor(inverted2, cv2.COLOR_GRAY2RGB)
            rgb_gray = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
            rgb_thresh2 = cv2.cvtColor(thresh2, cv2.COLOR_GRAY2RGB)
            # Create PIL images for pytesseract
            pil_img1 = Image.fromarray(rgb_bw1)
            pil_img2 = Image.fromarray(rgb_bw1_clean)
            pil_img3 = Image.fromarray(rgb_inverted2)
            pil_img4 = Image.fromarray(rgb_gray)
            pil_img5 = Image.fromarray(rgb_thresh2)
        except Exception:
            logging.exception("Preprocessing error")
            return 0

        # OCR with pytesseract
        raw_text = ""
        values = []  # Collect all OCR results for comparison
        try:
            # Only allow digits, dollarsign and commas, use --psm 7 for single line
            # custom_config = r"--psm 7 -c tessedit_char_whitelist=0123456789$,"
            custom_config = r"--oem 1 --psm 7 -c user_defined_dpi=300"
            for pil_img in [pil_img1, pil_img2, pil_img3, pil_img4, pil_img5]:
                raw_text = pytesseract.image_to_string(
                    pil_img, lang="digits", config=custom_config
                )
                raw_text = raw_text.strip()
                digits = "".join(filter(str.isdigit, raw_text))
                value = int(digits) if digits.isdigit() else 0
                values.append(value)
            # Use the minimum value as the final result as we have issues with reading too high (robust to OCR errors)
            value = min(values) if values else 0
            if debug:
                logging.info(f"[OCR] All parsed values: {values}")
                value_digits = int(math.log10(value)) + 1 if value > 0 else 0
                # adding some debug code to save images to run external OCR to find best settings
                if value_digits > 4:
                    logging.info(f"[OCR] value: {value} (digits: {value_digits})")
                    cv2.imwrite(make_unique_filename("currency_bw1"), bw1)
                    cv2.imwrite(make_unique_filename("currency_bw1_clean"), bw1_clean)
                    cv2.imwrite(make_unique_filename("currency_gray"), gray)
                    cv2.imwrite(make_unique_filename("currency_inverted2"), inverted2)
                    cv2.imwrite(make_unique_filename("currency_rgb_thresh2"), rgb_thresh2)
        except Exception:
            logging.exception("OCR error")
            value = 0

        if debug:
            logging.debug(f"[OCR] raw: {raw_text} | parsed: {value}")

    except KeyboardInterrupt:
        logging.info("[OCR] Stopped by user.")
        value = 0
    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
    return value


def is_mostly_black(image: np.ndarray, threshold: float = 0.9, black_level: int = 30) -> bool:
    """
    Determine if the given image is mostly black.

    Parameters:
        image (np.ndarray): Input image (BGR or grayscale).
        threshold (float): Proportion of pixels that must be black (default: 0.9).
        black_level (int): Pixel intensity below which a pixel is considered black (default: 30).

    Returns:
        bool: True if the proportion of black pixels exceeds the threshold, False otherwise.

    Edge Cases:
        - Returns False and logs a warning if image is None or empty.
    """
    if image is None or image.size == 0:
        logging.warning("is_mostly_black: Received None or empty image.")
        return False
    # Convert to grayscale if needed
    image_gray = _to_grayscale(image)
    total_pixels = image_gray.size
    black_pixels = np.sum(image_gray < black_level)
    proportion_black = black_pixels / total_pixels
    logging.info(
        f"is_mostly_black: {proportion_black:.3f} black pixels (threshold={threshold})"
    )
    return proportion_black >= threshold


def capture_screen(region=None) -> np.ndarray:
    """
    Capture a screenshot of the specified region using the module-level BetterCam instance.
    Retries if no new frame is available, up to _CAPTURE_RETRIES times, waiting _CAPTURE_DELAY seconds between attempts.
    Parameters:
        region (tuple or None): (left, top, width, height) or None for full screen.
    Returns:
        tuple: (img_bgr, img_gray) OpenCV images (numpy arrays)
    """
    try:
        # Use capture_region to benefit from debug mode optimizations
        if region is not None:
            img_bgr = capture_region(region)
            if img_bgr is None:
                logging.warning(
                    f"capture_screen: No frame captured after {_CAPTURE_RETRIES} attempts."
                )
                return None, None
            img_gray = _to_grayscale(img_bgr)
            return img_bgr, img_gray
        else:
            # For full screen capture, use the original logic
            cam = _CAMERA
            img = None
            for attempt in range(_CAPTURE_RETRIES):
                try:
                    img = cam.grab(region=None)
                except Exception:
                    logging.exception("BetterCam grab error")
                    img = None
                if img is not None:
                    break
                logging.info(
                    f"capture_screen: No new frame, retrying ({attempt + 1}/{_CAPTURE_RETRIES}) after {_CAPTURE_DELAY}s..."
                )
                time.sleep(_CAPTURE_DELAY)
            if img is None:
                logging.warning(
                    f"capture_screen: No frame captured after {_CAPTURE_RETRIES} attempts."
                )
                return None, None

            # Convert to BGR if needed
            if img.ndim == 3 and img.shape[2] == 4:
                img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            elif img.ndim == 3 and img.shape[2] == 3:
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            else:
                img_bgr = img

            img_gray = _to_grayscale(img_bgr)
            return img_bgr, img_gray
    except Exception:
        logging.exception(f"Failed to capture screen region {region}")
        return None, None


def find_element_on_screen(element_image):
    """
    Locate the center coordinates of a template image on the current screen.

    Parameters:
        element_image (str): Filesystem path to the template image to search for.

    Returns:
        (x, y) tuple: Center coordinates of the matched region if a sufficiently strong match is found, `None` otherwise.
    """
    start_time = time.time()
    screen_bgr, screen_gray = capture_screen()
    if screen_gray is None:
        return None
    # Debug: Save screenshot with timestamp and sanitized element name
    try:
        screenshots_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "screenshots"
        )
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        element_base = os.path.basename(element_image)
        element_name = os.path.splitext(element_base)[0]
        element_name = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in element_name
        )
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # screenshot_filename = f"{timestamp}_{element_name}.png"
        # screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
        # cv2.imwrite(screenshot_path, screen_bgr)
        # logging.info(f"Saved screenshot for debug: {screenshot_path}")
    except Exception:
        logging.exception("Failed to save debug screenshot.")

    try:
        template = cv2.imread(element_image, cv2.IMREAD_GRAYSCALE)
        if template is None:
            logging.error(f"Template image not found: {element_image}")
            return None
        match_start = time.time()
        res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        match_end = time.time()
        threshold = 0.75  # Adjust as needed for reliability
        logging.info(
            f"Template matching for {element_image} took {match_end - match_start:.3f}s (max_val={max_val:.2f})"
        )
        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            total_time = time.time() - start_time
            logging.info(f"find_element_on_screen total time: {total_time:.3f}s")
            return (center_x, center_y)
        else:
            logging.info(f"No match for {element_image} (max_val={max_val:.2f})")
            return None
    except Exception:
        logging.exception("Error in find_element_on_screen")
        return None
