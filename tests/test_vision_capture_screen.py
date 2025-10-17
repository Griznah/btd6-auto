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
    # Return a dummy image (e.g., 100x100 RGB)
    return np.ones((100, 100, 3), dtype=np.uint8) * 127

def test_capture_screen_full(monkeypatch):
    from btd6_auto import vision
    monkeypatch.setattr("dxcam.Camera.grab", lambda self, region=None: fake_dxcam_grab(region))
    monkeypatch.setattr("dxcam.Camera", mock.MagicMock())
    # Patch cv2.cvtColor to just return the input for test simplicity
    monkeypatch.setattr("cv2.cvtColor", lambda img, code: img)
    img_bgr, img_gray = vision.capture_screen()
    assert img_bgr is not None
    assert img_gray is not None
    assert isinstance(img_bgr, np.ndarray)
    assert isinstance(img_gray, np.ndarray)
    assert img_bgr.shape == (100, 100, 3)
    assert img_gray.shape == (100, 100, 3)

def test_capture_screen_region(monkeypatch):
    from btd6_auto import vision
    monkeypatch.setattr("dxcam.Camera.grab", lambda self, region=None: fake_dxcam_grab(region))
    monkeypatch.setattr("dxcam.Camera", mock.MagicMock())
    monkeypatch.setattr("cv2.cvtColor", lambda img, code: img)
    region = (10, 10, 50, 50)
    img_bgr, img_gray = vision.capture_screen(region=region)
    assert img_bgr is not None
    assert img_gray is not None

def test_capture_screen_error(monkeypatch):
    from btd6_auto import vision
    def raise_error(*args, **kwargs):
        raise RuntimeError("dxcam error")
    monkeypatch.setattr("dxcam.Camera.grab", raise_error)
    monkeypatch.setattr("dxcam.Camera", mock.MagicMock())
    img_bgr, img_gray = vision.capture_screen()
    assert img_bgr is None
    assert img_gray is None
