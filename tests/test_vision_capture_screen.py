import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
import pytest
import numpy as np
# ...existing code...

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("win"),
    reason="dxcam/COM only available on Windows",
)


# Patch dxcam and cv2 for Linux compatibility
def fake_dxcam_grab(region=None):
    """
    Return a dummy image for testing purposes.
    If region is provided, returns an image sized to the region.
    Otherwise, returns a 100x100 RGB image filled with 127.
    Parameters:
        region (tuple, optional): (x1, y1, x2, y2) coordinates.
    Returns:
        np.ndarray: Dummy image array.
    """
    if region:
        x1, y1, x2, y2 = region
        h, w = y2 - y1, x2 - x1
        return np.ones((h, w, 3), dtype=np.uint8) * 127
    return np.ones((100, 100, 3), dtype=np.uint8) * 127


def test_capture_screen_full(monkeypatch):
    """
    Test that full screen capture returns correct shapes and types.
    Ensures that the capture_screen function returns both BGR and grayscale images
    with expected dimensions and types when no region is specified.
    """
    from btd6_auto import vision

    class FakeCamera:
        def grab(self, region=None):
            return fake_dxcam_grab(region)

    class FakeDxcam:
        @staticmethod
        def create():
            return FakeCamera()

    monkeypatch.setitem(sys.modules, "dxcam", FakeDxcam)

    def fake_cvtColor(img, code):
        """
        Fake cv2.cvtColor for testing. Returns a grayscale image for code 6.
        """
        if code == 6:
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
    """
    Test that region capture returns correct shapes and types for the specified region size.
    Ensures that the capture_screen function returns images with dimensions matching the region.
    """
    from btd6_auto import vision

    class FakeCamera:
        def grab(self, region=None):
            return fake_dxcam_grab(region)

    class FakeDxcam:
        @staticmethod
        def create():
            return FakeCamera()

    monkeypatch.setitem(sys.modules, "dxcam", FakeDxcam)

    def fake_cvtColor(img, code):
        """
        Fake cv2.cvtColor for testing. Returns a grayscale image for COLOR_BGR2GRAY.
        """
        import cv2

        if code == cv2.COLOR_BGR2GRAY:
            h, w = img.shape[:2]
            return np.ones((h, w), dtype=np.uint8) * 127
        return img

    monkeypatch.setattr("cv2.cvtColor", fake_cvtColor)
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
    """
    Test that an error in dxcam returns None outputs and handles cv2 dependency gracefully.
    Ensures that capture_screen returns (None, None) when dxcam raises an exception.
    """
    from btd6_auto import vision

    class FakeCamera:
        def grab(self, region=None):
            raise RuntimeError("dxcam error")

    class FakeDxcam:
        @staticmethod
        def create():
            return FakeCamera()

    monkeypatch.setitem(sys.modules, "dxcam", FakeDxcam)

    def fake_cvtColor(img, code):
        """
        Fake cv2.cvtColor for error test. Returns a grayscale image for code 6.
        """
        if code == 6:
            return np.ones((100, 100), dtype=np.uint8) * 127
        return img

    monkeypatch.setattr("cv2.cvtColor", fake_cvtColor)
    img_bgr, img_gray = vision.capture_screen()
    assert img_bgr is None
    assert img_gray is None
