import sys
import os
import cv2
import numpy as np
import time
import pytest
import pygetwindow as gw

# Import capture_screen from vision.py
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'btd6_auto'))
from vision import capture_screen

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("win"),
    reason="Actual automation only available on Windows"
)

DATA_IMAGE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'images')
print(f"[INFO] Data image path: {DATA_IMAGE_PATH}")

# Actual implementation for window activation (Windows-only)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from config import BTD6_WINDOW_TITLE
except ImportError:
    BTD6_WINDOW_TITLE = "BloonsTD6"  # Fallback default

def activate_btd6_window() -> bool:
    """
    Activate the BTD6 game window before automation (Windows-only).
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        windows = gw.getWindowsWithTitle(BTD6_WINDOW_TITLE)
        if not windows:
            print(f"[ERROR] Could not find window with title '{BTD6_WINDOW_TITLE}'. (Windows-only)")
            return False
        win = windows[0]
        win.activate()
        time.sleep(0.5)  # Wait for the window to come to the foreground
        print(f"[INFO] Activated window: {win.title}")
        return True
    except Exception as e:
        print(f"[ERROR] Exception during window activation: {e}")
        return False


def verbose_template_match(screenshot, template, threshold=0.8):
    print(f"[DEBUG] Screenshot shape: {screenshot.shape}")
    print(f"[DEBUG] Template shape: {template.shape}")
    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    print(f"[DEBUG] Result matrix shape: {result.shape}")
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    print(f"[DEBUG] Min val: {min_val}, Max val: {max_val}")
    print(f"[DEBUG] Min loc: {min_loc}, Max loc: {max_loc}")
    loc = np.where(result >= threshold)
    print(f"[DEBUG] Number of matches above threshold ({threshold}): {len(loc[0])}")
    return result, loc, max_val, max_loc


def draw_matches(screenshot, template, loc):
    h, w = template.shape[:2]
    for pt in zip(*loc[::-1]):
        cv2.rectangle(screenshot, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)
    return screenshot


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <template_image_filename>")
        sys.exit(1)
    template_filename = sys.argv[1]
    template_path = os.path.join(DATA_IMAGE_PATH, template_filename)
    if not os.path.exists(template_path):
        print(f"[ERROR] Template image not found: {template_path}")
        sys.exit(1)

    activate_btd6_window()
    print("[INFO] Taking screenshot...")
    screenshot = capture_screen()
    if screenshot is None:
        print("[ERROR] Screenshot failed.")
        sys.exit(1)
    print(f"[INFO] Loading template: {template_path}")
    template = cv2.imread(template_path)
    if template is None:
        print("[ERROR] Failed to load template image.")
        sys.exit(1)

    print("[INFO] Performing template matching...")
    result, loc, max_val, max_loc = verbose_template_match(screenshot, template)
    print(f"[RESULT] Best match value: {max_val} at location {max_loc}")
    print(f"[RESULT] Matches above threshold: {len(loc[0])}")

    print("[INFO] Drawing rectangles around matches...")
    matched_img = draw_matches(screenshot.copy(), template, loc)
    output_path = os.path.join(os.path.dirname(__file__), 'output_match.png')
    cv2.imwrite(output_path, matched_img)
    print(f"[INFO] Output image saved to: {output_path}")

if __name__ == "__main__":
    main()
