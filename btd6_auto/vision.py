"""
Screen capture and image recognition (OpenCV).
"""

import pyautogui
import cv2
import numpy as np
import logging
import os
from datetime import datetime

def capture_screen(region=None) -> np.ndarray:
    """
    Capture a screenshot of the specified region (Windows-only).
    Args:
        region (tuple or None): (left, top, width, height) or None for full screen.
    Returns:
        np.ndarray: OpenCV image (numpy array)
    """
    try:
        screenshot = pyautogui.screenshot(region=region)
        img = np.array(screenshot)
        # Return both color and grayscale for flexibility
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
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
        threshold = 0.85  # Adjust as needed for reliability
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
