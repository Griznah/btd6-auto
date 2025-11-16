import os
import sys
import pytest
import numpy as np
import cv2

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("win"),
    reason="BetterCam/COM only available on Windows",
)


def test_to_grayscale(monkeypatch):
    """
    Test that _to_grayscale correctly handles 3-channel, 4-channel, and grayscale images.
    """
    from btd6_auto import vision

    # 3-channel BGR
    bgr_img = np.ones((10, 10, 3), dtype=np.uint8) * 50
    # 4-channel BGRA
    bgra_img = np.ones((10, 10, 4), dtype=np.uint8) * 100
    # Grayscale
    gray_img = np.ones((10, 10), dtype=np.uint8) * 150

    # Patch cv2.cvtColor to check correct code usage
    def fake_cvtColor(img, code):
        if code == cv2.COLOR_BGRA2GRAY:
            return np.ones(img.shape[:2], dtype=np.uint8) * 200
        elif code == cv2.COLOR_BGR2GRAY:
            return np.ones(img.shape[:2], dtype=np.uint8) * 100
        return img

    monkeypatch.setattr("cv2.cvtColor", fake_cvtColor)

    out1 = vision._to_grayscale(bgr_img)
    out2 = vision._to_grayscale(bgra_img)
    out3 = vision._to_grayscale(gray_img)

    assert out1.shape == (10, 10), (
        "3-channel BGR should convert to grayscale shape"
    )
    assert np.all(out1 == 100), "3-channel BGR should yield value 100"
    assert out2.shape == (10, 10), (
        "4-channel BGRA should convert to grayscale shape"
    )
    assert np.all(out2 == 200), "4-channel BGRA should yield value 200"
    assert out3.shape == (10, 10), "Grayscale should remain unchanged"
    assert np.all(out3 == 150), "Grayscale should yield value 150"


pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("win"),
    reason="BetterCam/COM only available on Windows",
)


def fake_bettercam_grab(region=None):
    """
    Return a dummy image for testing purposes using BetterCam conventions.
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
    Test that full screen capture returns correct shapes and types using BetterCam mocks.
    Ensures that the capture_screen function returns both BGR and grayscale images
    with expected dimensions and types when no region is specified.
    """
    from btd6_auto import vision

    class FakeCamera:
        def grab(self, region=None):
            return fake_bettercam_grab(region)

        def release(self):
            pass

    def fake_cvtColor(img, code):
        """
        Fake cv2.cvtColor for testing. Returns a grayscale image for code 6.
        """
        if code == 6:
            return np.ones((100, 100), dtype=np.uint8) * 127
        return img

    import bettercam

    monkeypatch.setattr(bettercam, "create", lambda: FakeCamera())
    monkeypatch.setattr("cv2.cvtColor", fake_cvtColor)
    img_bgr, img_gray = vision.capture_screen(camera=FakeCamera())
    assert img_bgr is not None, "BGR image should not be None"
    assert img_gray is not None, "Grayscale image should not be None"
    assert isinstance(img_bgr, np.ndarray), "BGR image should be ndarray"
    assert isinstance(img_gray, np.ndarray), (
        "Grayscale image should be ndarray"
    )
    assert img_bgr.shape == (100, 100, 3), "BGR image shape mismatch"
    assert img_gray.shape == (100, 100), "Grayscale image shape mismatch"


def test_capture_screen_region(monkeypatch):
    """
    Test that region capture returns correct shapes and types for the specified region size using BetterCam mocks.
    Ensures that the capture_screen function returns images with dimensions matching the region.
    """
    from btd6_auto import vision

    class FakeCamera:
        def grab(self, region=None):
            return fake_bettercam_grab(region)

        def release(self):
            pass

    # bettercam.create patch is not needed since camera=FakeCamera() is passed directly

    def fake_cvtColor(img, code):
        if code == cv2.COLOR_BGR2GRAY:
            h, w = img.shape[:2]
            return np.ones((h, w), dtype=np.uint8) * 127
        return img

    monkeypatch.setattr("cv2.cvtColor", fake_cvtColor)

    @pytest.mark.parametrize(
        "region", [(10, 10, 40, 30), (0, 0, 20, 20), (5, 5, 10, 15)]
    )
    def run_region_test(region):
        img_bgr, img_gray = vision.capture_screen(
            region=region, camera=FakeCamera()
        )
        assert img_bgr is not None, "BGR image should not be None"
        assert img_gray is not None, "Grayscale image should not be None"
        assert isinstance(img_bgr, np.ndarray), "BGR image should be ndarray"
        assert isinstance(img_gray, np.ndarray), (
            "Grayscale image should be ndarray"
        )
        h, w = region[3], region[2]
        assert img_bgr.shape == (h, w, 3), (
            f"BGR image shape mismatch for region {region}"
        )
        assert img_gray.shape == (h, w), (
            f"Grayscale image shape mismatch for region {region}"
        )

    for region in [(10, 10, 40, 30), (0, 0, 20, 20), (5, 5, 10, 15)]:
        run_region_test(region)


def test_capture_screen_error(monkeypatch):
    """
    Test that an error in BetterCam returns None outputs and handles cv2 dependency gracefully.
    Ensures that capture_screen returns (None, None) when BetterCam raises an exception.
    """
    from btd6_auto import vision

    class FakeCamera:
        def grab(self, region=None):
            raise RuntimeError("BetterCam error")

        def release(self):
            pass

    # bettercam.create patch is not needed since camera=FakeCamera() is passed directly

    def fake_cvtColor(img, code):
        """
        Fake cv2.cvtColor for error test. Returns a grayscale image for code 6.
        """
        if code == 6:
            return np.ones((100, 100), dtype=np.uint8) * 127
        return img

    monkeypatch.setattr("cv2.cvtColor", fake_cvtColor)
    img_bgr, img_gray = vision.capture_screen(camera=FakeCamera())
    assert img_bgr is None, "BGR image should be None on error"
    assert img_gray is None, "Grayscale image should be None on error"
