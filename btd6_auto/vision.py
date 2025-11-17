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
import keyboard
import bettercam

# Use ConfigLoader for config loading
from .config_loader import ConfigLoader


def rect_to_region(rect):
    """
    Convert a rectangle from (left, top, right, bottom) to (left, top, width, height).
    Args:
        rect (tuple/list): (left, top, right, bottom)
    Returns:
        tuple: (left, top, width, height)
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
    Capture a screenshot of a region using BetterCam (consistent with module).
    region: (left, top, width, height)
    Returns: numpy array (BGR)
    """
    left, top, width, height = region
    right = left + width
    bottom = top + height
    bettercam_region = (left, top, right, bottom)
    # Validate region bounds for 1920x1080 screen
    if not (0 <= left < right <= 1920 and 0 <= top < bottom <= 1080):
        logging.error(
            f"capture_region: Invalid region {bettercam_region} (must be within 1920x1080)"
        )
        return None
    cam = _CAMERA
    img = None
    for attempt in range(_CAPTURE_RETRIES):
        try:
            img = cam.grab(region=bettercam_region)
        except Exception:
            logging.exception("BetterCam grab error in capture_region")
            img = None
        if img is not None:
            break
        logging.info(
            f"capture_region: No new frame, retrying ({attempt + 1}/{_CAPTURE_RETRIES}) after {_CAPTURE_DELAY}s..."
        )
        time.sleep(_CAPTURE_DELAY)
    if img is None:
        logging.warning(
            f"capture_region: No frame captured after {_CAPTURE_RETRIES} attempts."
        )
        return None
    # Handle BGRA/RGBA images and convert to BGR
    if img.ndim == 3 and img.shape[2] == 4:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    elif img.ndim == 3 and img.shape[2] == 3:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img
    return img_bgr


def calculate_image_difference(img1, img2):
    """
    Calculate the percentage difference between two images.
    Returns: float (0-100)
    """
    if img1.shape != img2.shape:
        logging.error("Image shapes do not match for comparison.")
        return 100.0
    diff = cv2.absdiff(img1, img2)
    nonzero = np.count_nonzero(diff)
    total = diff.size
    percent_diff = (nonzero / total) * 100
    return percent_diff


def verify_placement_change(pre_img, post_img, threshold=85.0):
    """
    Compare pre and post images for placement confirmation.
    Returns: (bool, float) -> (success, percent_diff)
    """
    percent_diff = calculate_image_difference(pre_img, post_img)
    logging.debug(
        f"Placement diff: {percent_diff:.2f}% (threshold: {threshold})"
    )
    return percent_diff >= threshold, percent_diff


def confirm_selection(pre_img, post_img, threshold=40.0):
    """
    Compare pre and post images for selection confirmation.
    Returns: (bool, float) -> (success, percent_diff)
    """
    percent_diff = calculate_image_difference(pre_img, post_img)
    logging.info(
        f"Selection diff: {percent_diff:.2f}% (threshold: {threshold})"
    )
    return percent_diff >= threshold, percent_diff


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
    Retry an action (selection/placement) with vision confirmation.
    action_fn: function to perform (e.g., select_monkey, place_monkey)
    region: region tuple for capture
    threshold: float, percent difference required
    max_attempts: int
    delay: float, seconds between attempts
    confirm_fn: function to confirm (e.g., confirm_selection, verify_placement_change)
    args, kwargs: passed to action_fn
    Returns: bool (success)
    """
    for attempt in range(1, max_attempts + 1):
        pre_img = capture_region(region)
        action_fn(*args, **kwargs)
        time.sleep(delay)
        post_img = capture_region(region)
        success, percent_diff = confirm_fn(pre_img, post_img, threshold)
        logging.info(
            f"Attempt {attempt}: diff={percent_diff:.2f}% success={success}"
        )
        if success:
            return True
    logging.error(f"Action failed after {max_attempts} attempts.")
    return False


def handle_vision_error():
    """
    Generic error handler for repeated vision failures.
    Cleans up and exits.
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
    Set the round state by ensuring the correct speed or start button is active.

    This function uses image recognition to detect the current round state ("fast", "slow", or "start")
    and simulates pressing the Spacebar to toggle speed as needed. For the "start" state, it ensures
    the start button is visible and the speed is set to fast. The function retries up to max_retries
    times, waiting delay seconds between attempts. Defaults are loaded from global config.

    Parameters:
        state (str): One of "fast", "slow", or "start".
        region (tuple): (left, top, right, bottom) coordinates to search for the state image.
        max_retries (int, optional): Maximum number of attempts to set the state. Defaults to global config.
        delay (float, optional): Delay in seconds between attempts. Defaults to global config.
        find_in_region (callable, optional): Function to check for template in region (for testing/mocking).

    Returns:
        bool: True if the requested state was set successfully, False otherwise.
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
            res = cv2.matchTemplate(
                screen_gray, template, cv2.TM_CCOEFF_NORMED
            )
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

    images_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "images"
    )
    img_fast = os.path.join(images_dir, image_map["fast"])
    img_slow = os.path.join(images_dir, image_map["slow"])
    img_start = os.path.join(images_dir, image_map["start"])

    for attempt in range(1, max_retries + 1):
        logging.info(
            f"[set_round_state] Attempt {attempt} for state '{state}'"
        )
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


def read_currency_amount(
    region: tuple = (370, 26, 515, 60), debug: bool = False
) -> int:
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

    camera = _CAMERA

    try:
        frame = None
        for attempt in range(3):
            try:
                left, top, right, bottom = region
                frame = camera.grab(region=(left, top, right, bottom))
            except Exception:
                logging.exception("Camera grab error")
            if frame is not None:
                break
            logging.info(
                f"No frame captured for currency region (attempt {attempt + 1}/3). Retrying..."
            )
            time.sleep(0.2)
        if frame is None:
            logging.warning(
                "No frame captured for currency region after 3 attempts."
            )
            return 0

        # Preprocess for OCR
        try:
            cv2.setUseOptimized(True)
            cv2.setNumThreads(1)
            gray = _to_grayscale(frame)
            if gray is None:
                logging.warning("Frame conversion to grayscale failed.")
                return 0
            # Use Otsu's thresholding for robust binarization
            _, thresh = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            # Invert so white text becomes black (Tesseract prefers black text on white)
            inverted = cv2.bitwise_not(thresh)
            # Convert to RGB for pytesseract
            rgb = cv2.cvtColor(inverted, cv2.COLOR_GRAY2RGB)
            pil_img = Image.fromarray(rgb)
        except Exception:
            logging.exception("Preprocessing error")
            return 0

        # OCR with pytesseract
        try:
            # Only allow digits and commas, use --psm 7 for single line
            custom_config = r"--psm 7 -c tessedit_char_whitelist=0123456789,"
            raw_text = pytesseract.image_to_string(
                pil_img, config=custom_config
            )
            # Remove commas and non-digit characters
            digits = "".join([c for c in raw_text if c.isdigit()])
            value = int(digits) if digits else 0
        except Exception:
            logging.exception("OCR error")
            value = 0

        if debug:
            logging.debug(f"[OCR] Currency: {value}")

    except KeyboardInterrupt:
        logging.info("[OCR] Stopped by user.")
        value = 0
    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
    return value


def is_mostly_black(
    image: np.ndarray, threshold: float = 0.9, black_level: int = 30
) -> bool:
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
    cam = _CAMERA
    try:
        if region is not None:
            left, top, width, height = region
            right = left + width
            bottom = top + height
            bettercam_region = (left, top, right, bottom)
        else:
            bettercam_region = None
        img = None
        for attempt in range(_CAPTURE_RETRIES):
            try:
                img = cam.grab(region=bettercam_region)
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
        # Handle BGRA/RGBA images and convert to BGR
        if img.ndim == 3 and img.shape[2] == 4:
            # BGRA or RGBA to BGR
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif img.ndim == 3 and img.shape[2] == 3:
            # Already BGR or RGB, assume RGB from BetterCam
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
    except Exception as e:
        logging.error(f"Failed to save debug screenshot: {e}")

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
            logging.info(
                f"find_element_on_screen total time: {total_time:.3f}s"
            )
            return (center_x, center_y)
        else:
            logging.info(
                f"No match for {element_image} (max_val={max_val:.2f})"
            )
            return None
    except Exception as e:
        logging.error(f"Error in find_element_on_screen: {e}")
    except Exception:
        logging.exception("Error in find_element_on_screen")
        return None
