"""
Screen capture and image recognition (OpenCV).
"""
import pyautogui
import cv2
import numpy as np

def capture_screen(region=None) -> np.ndarray:
    """
    Capture a screenshot of the specified region (Windows-only).
    region: (left, top, width, height) or None for full screen
    Returns: OpenCV image (numpy array)
    """
    screenshot = pyautogui.screenshot(region=region)
    # Convert PIL image to OpenCV format
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    return img

def find_element_on_screen(element_image):
    pass
