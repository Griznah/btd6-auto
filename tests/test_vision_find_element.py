import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import numpy as np
from unittest import mock

def fake_capture_screen_found(*args, **kwargs):
    # Return a dummy image (bgr, gray)
    img = np.ones((100, 100), dtype=np.uint8) * 127
    return (img, img)

def fake_capture_screen_none(*args, **kwargs):
    return (None, None)

def fake_cv2_imread(path, flags):
    # Return a dummy template
    return np.ones((10, 10), dtype=np.uint8) * 127

def fake_cv2_matchTemplate(img, template, method):
    # Return a result with a clear max
    res = np.zeros((91, 91), dtype=np.float32)
    res[50, 50] = 1.0  # Simulate a strong match
    return res

def fake_cv2_minMaxLoc(res):
    return (0, 1.0, (0, 0), (50, 50))

def test_find_element_on_screen_found(monkeypatch):
    from btd6_auto import vision
    monkeypatch.setattr(vision, "capture_screen", fake_capture_screen_found)
    monkeypatch.setattr("cv2.imread", fake_cv2_imread)
    monkeypatch.setattr("cv2.matchTemplate", fake_cv2_matchTemplate)
    monkeypatch.setattr("cv2.minMaxLoc", fake_cv2_minMaxLoc)
    coords = vision.find_element_on_screen("dummy_path.png")
    assert coords == (55, 55)  # 50 + 10//2

def test_find_element_on_screen_not_found(monkeypatch):
    from btd6_auto import vision
    monkeypatch.setattr(vision, "capture_screen", fake_capture_screen_found)
    monkeypatch.setattr("cv2.imread", fake_cv2_imread)
    def matchTemplate_no_match(img, template, method):
        return np.zeros((91, 91), dtype=np.float32)
    monkeypatch.setattr("cv2.matchTemplate", matchTemplate_no_match)
    monkeypatch.setattr("cv2.minMaxLoc", lambda res: (0, 0.5, (0, 0), (10, 10)))
    coords = vision.find_element_on_screen("dummy_path.png")
    assert coords is None

def test_find_element_on_screen_error(monkeypatch):
    from btd6_auto import vision
    monkeypatch.setattr(vision, "capture_screen", fake_capture_screen_none)
    coords = vision.find_element_on_screen("dummy_path.png")
    assert coords is None
