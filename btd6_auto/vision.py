"""
Screen capture and image recognition (OpenCV).
"""

import pyautogui
import cv2
import numpy as np
from config import TOWER_POSITIONS
import logging

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
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return img
    except Exception as e:
        logging.error(f"Failed to capture screen region {region}: {e}")
        return None

def find_element_on_screen(element_image):
    """
    Find the given element on the current screen using template matching.
    Args:
        element_image (str): Path to the template image file.
    Returns:
        tuple: (x, y) coordinates of the center of the matched region, or None if not found.
    """
    screen = capture_screen()
    if screen is None:
        return None
    try:
        template = cv2.imread(element_image, cv2.IMREAD_COLOR)
        if template is None:
            logging.error(f"Template image not found: {element_image}")
            return None
        res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        threshold = 0.85  # Adjust as needed for reliability
        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y)
        else:
            logging.info(f"No match for {element_image} (max_val={max_val:.2f})")
            return None
    except Exception as e:
        logging.error(f"Error in find_element_on_screen: {e}")
        return None
