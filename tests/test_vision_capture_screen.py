import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import numpy as np
from unittest import mock

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("win"),
    reason="dxcam/COM only available on Windows"
)

# Patch dxcam and cv2 for Linux compatibility
def fake_dxcam_grab(region=None):
    # Return a dummy image sized to region if provided, else 100x100 RGB
    if region:
        x1, y1, x2, y2 = region
        h, w = y2 - y1, x2 - x1
        return np.ones((h, w, 3), dtype=np.uint8) * 127
    return np.ones((100, 100, 3), dtype=np.uint8) * 127

def test_capture_screen_full(monkeypatch):
    """Test full screen capture returns correct shapes and types."""
    from btd6_auto import vision
    monkeypatch.setattr("dxcam.Camera.grab", lambda self, region=None: fake_dxcam_grab(region))
    monkeypatch.setattr("dxcam.Camera", mock.MagicMock())
    # Patch cv2.cvtColor to just return the input for test simplicity
    def fake_cvtColor(img, code):
        # cv2.COLOR_BGR2GRAY is usually 6
        if code == 6:
            # Return a 2D grayscale image
            return np.ones((100, 100), dtype=np.uint8) * 127
        return img
    monkeypatch.setattr("cv2.cvtColor", fake_cvtColor)
    img_bgr, img_gray = vision.capture_screen()
    assert img_bgr is not None
    assert img_gray is not None
    assert isinstance(img_bgr, np.ndarray)
    assert isinstance(img_gray, np.ndarray)
    assert img_bgr.shape == (100, 100, 3)
    assert img_gray.shape == (100, 100)

def test_capture_screen_region(monkeypatch):
    from btd6_auto import vision
    monkeypatch.setattr("dxcam.Camera.grab", lambda self, region=None: fake_dxcam_grab(region))
    monkeypatch.setattr("dxcam.Camera", mock.MagicMock())
    def fake_cvtColor(img, code):
        import cv2
        if code == cv2.COLOR_BGR2GRAY:
            # Return a 2D grayscale image
            h, w = img.shape[:2]
            return np.ones((h, w), dtype=np.uint8) * 127
        return img
    monkeypatch.setattr("cv2.cvtColor", fake_cvtColor)
    """Test region capture returns correct shapes and types for region size."""
    region = (10, 10, 40, 30)  # (left, top, width, height)
    img_bgr, img_gray = vision.capture_screen(region=region)
    assert img_bgr is not None
    assert img_gray is not None
    assert isinstance(img_bgr, np.ndarray)
    assert isinstance(img_gray, np.ndarray)
    h, w = region[3], region[2]
    assert img_bgr.shape == (h, w, 3)
    assert img_gray.shape == (h, w)

def test_capture_screen_error(monkeypatch):
    from btd6_auto import vision
    def raise_error(*args, **kwargs):
        raise RuntimeError("dxcam error")
    monkeypatch.setattr("dxcam.Camera.grab", raise_error)
    monkeypatch.setattr("dxcam.Camera", mock.MagicMock())
    """Test error in dxcam returns None outputs and handles cv2 dependency."""
    def fake_cvtColor(img, code):
        if code == 6:
            return np.ones((100, 100), dtype=np.uint8) * 127
        return img
    monkeypatch.setattr("cv2.cvtColor", fake_cvtColor)
    img_bgr, img_gray = vision.capture_screen()
    assert img_bgr is None
    assert img_gray is None
