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
    pass
