"""
Screen capture and image recognition (OpenCV).
"""

import cv2
import numpy as np
import logging
import os
import sys
import time

# EasyOCR import
try:
    import easyocr
except ImportError:
    easyocr = None

easyocr_available = easyocr is not None
def read_currency_amount(
    region: tuple = (370, 26, 515, 60),
    debug: bool = False
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
    if not easyocr_available:
        logging.error("EasyOCR not installed. Cannot perform OCR.")
        return 0

    # Static initialization for camera and OCR
    if not hasattr(read_currency_amount, "_ocr") or not hasattr(read_currency_amount, "_camera"):
        try:
            import dxcam
            # Pre-allocate EasyOCR Reader with English language and GPU
            read_currency_amount._ocr = easyocr.Reader(['en'], gpu=True)
            read_currency_amount._camera = dxcam.create(output_idx=0)
        except Exception as e:
            logging.error(f"OCR/camera init failed: {e}")
            return 0
    ocr = read_currency_amount._ocr
    camera = read_currency_amount._camera

    try:
        frame = camera.grab(region=region)
        if frame is None:
            logging.warning("No frame captured for currency region.")
            return 0

        # Preprocess
        try:
            cv2.setUseOptimized(True)
            cv2.setNumThreads(1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
            norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
            _, thresh = cv2.threshold(norm, 180, 255, cv2.THRESH_BINARY)
        except Exception as e:
            logging.error(f"Preprocessing error: {e}")
            return 0

        try:
            results = ocr.readtext(thresh, allowlist='0123456789', detail=1)
            digits = "".join([text for _, text, conf in results if isinstance(text, str) and text.isdigit()])
            gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
            norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
            _, thresh = cv2.threshold(norm, 180, 255, cv2.THRESH_BINARY)
        except Exception as e:
            logging.error(f"Preprocessing error: {e}")
            return 0

        # OCR
        try:
            # EasyOCR returns a list of (bbox, text, confidence)
            results = ocr.readtext(thresh, allowlist='0123456789', detail=1)
            digits = "".join([
                text for _, text, conf in results if isinstance(text, str) and text.isdigit()
            ])
            value = int(digits) if digits else 0
        except Exception as e:
            logging.error(f"OCR error: {e}")
            value = 0

        if debug:
            logging.info(f"[OCR] Currency: {value}")
            cv2.imshow("Currency Region", thresh)
            cv2.waitKey(1000)  # Show for 1 second
            cv2.destroyAllWindows()

    except KeyboardInterrupt:
        logging.info("[OCR] Stopped by user.")
        value = 0
    finally:
        try:
            camera.stop()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
    return value

from datetime import datetime

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
    if len(image.shape) == 3 and image.shape[2] == 3:
        image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        image_gray = image
    total_pixels = image_gray.size
    black_pixels = np.sum(image_gray < black_level)
    proportion_black = black_pixels / total_pixels
    logging.info(f"is_mostly_black: {proportion_black:.3f} black pixels (threshold={threshold})")
    return proportion_black >= threshold

def capture_screen(region=None) -> np.ndarray:
    """
    Capture a screenshot of the specified region using dxcam (Windows-only).
    On non-Windows platforms, always returns (None, None) and logs a warning.
    Args:
        region (tuple or None): (left, top, width, height) or None for full screen.
    Returns:
        tuple: (img_bgr, img_gray) OpenCV images (numpy arrays)
    """
    if not sys.platform.startswith("win"):
        logging.warning("capture_screen: dxcam is only supported on Windows. Returning (None, None).")
        return None, None
    try:
        import dxcam
        # dxcam expects region as (left, top, right, bottom)
        cam = dxcam.create()
        if region is not None:
            left, top, width, height = region
            right = left + width
            bottom = top + height
            dxcam_region = (left, top, right, bottom)
        else:
            dxcam_region = None
        img = cam.grab(region=dxcam_region)
        if img is None:
            raise RuntimeError("dxcam returned None image")
        # dxcam returns BGRA, convert to BGR
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        return img_bgr, img_gray
    except Exception as e:
        logging.error(f"Failed to capture screen region {region}: {e}")
        return None, None

def find_element_on_screen(element_image):
    """
    Find the given element on the current screen using template matching.
    Args:
        element_image (str): Path to the template image file.
    Returns:
        tuple: (x, y) coordinates of the center of the matched region, or None if not found.
    Additionally, saves the screenshot to the screenshots folder for debugging.
    """
    import time
    start_time = time.time()
    screen_bgr, screen_gray = capture_screen()
    if screen_gray is None:
        return None
    # Debug: Save screenshot with timestamp and sanitized element name
    try:
        screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'screenshots')
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        element_base = os.path.basename(element_image)
        element_name = os.path.splitext(element_base)[0]
        element_name = ''.join(c if c.isalnum() or c in ('-', '_') else '_' for c in element_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_filename = f"{timestamp}_{element_name}.png"
        screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
        #cv2.imwrite(screenshot_path, screen_bgr)
        #logging.info(f"Saved screenshot for debug: {screenshot_path}")
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
        logging.info(f"Template matching for {element_image} took {match_end - match_start:.3f}s (max_val={max_val:.2f})")
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
    except Exception as e:
        logging.error(f"Error in find_element_on_screen: {e}")
        return None
