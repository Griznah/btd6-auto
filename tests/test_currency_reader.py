import sys
import os
import time
import glob
import pytest
import pytesseract
from PIL import Image

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
import numpy as np
import cv2
from btd6_auto.currency_reader import CurrencyReader


class DummyCamera:
    """
    Dummy camera class for simulating BetterCam camera behavior in tests.
    Returns a dummy image with digits '12345' drawn for currency reading.
    """

    def __init__(self):
        self.calls = 0

    def grab(self, region=None):
        """
        Simulate grabbing a screen region and return a dummy image.
        """
        self.calls += 1
        img = np.ones((45, 165, 4), dtype=np.uint8) * 255
        cv2.putText(
            img,
            "12345",
            (10, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 0, 0, 255),
            2,
        )
        return img

    def release(self):
        """
        Dummy release method for camera.
        """
        pass


class DummyOCR:
    """
    Dummy OCR class for simulating EasyOCR behavior in tests.
    Always returns '12345' as detected text.
    """

    def __init__(self, *args, **kwargs):
        pass

    def readtext(self, img, allowlist=None, detail=1):
        """
        Simulate reading text from an image and return a fixed result.
        """
        return [((0, 0, 0, 0), "12345", 0.99)]


def patch_vision(monkeypatch):
    """
    Make OCR-based currency reads deterministic for tests by patching CurrencyReader.
    
    Replaces btd6_auto.currency_reader.read_currency_amount with a stub that accepts the usual
    (region, debug) parameters and always returns 12345, so tests relying on currency reads get
    a consistent value.
    """
    import btd6_auto.currency_reader as currency_reader

    monkeypatch.setattr(
        currency_reader,
        "read_currency_amount",
        lambda region=(370, 26, 515, 60), debug=False: 12345,
    )


def test_currency_reader_thread(monkeypatch):
    """
    Test that CurrencyReader thread starts, reads currency, and stops correctly.
    Ensures the thread updates currency value and can be stopped using BetterCam mocks.
    """
    patch_vision(monkeypatch)
    reader = CurrencyReader(poll_interval=0.1)
    reader.start()
    time.sleep(0.2)  # Allow thread to run at least once
    value = reader.get_currency()
    assert value == 12345
    reader.stop()
    assert not reader.is_running()


def test_currency_reader_multiple_reads(monkeypatch):
    """
    Test that CurrencyReader returns consistent values across multiple reads.
    Ensures repeated polling returns the expected currency value using BetterCam mocks.
    """
    patch_vision(monkeypatch)
    reader = CurrencyReader(poll_interval=0.05)
    reader.start()
    time.sleep(0.15)
    v1 = reader.get_currency()
    time.sleep(0.1)
    v2 = reader.get_currency()
    assert v1 == 12345 and v2 == 12345
    reader.stop()


def test_currency_reader_stop_idempotent(monkeypatch):
    """
    Test that stopping CurrencyReader multiple times is idempotent and safe.
    Ensures no error is raised when stop() is called repeatedly using BetterCam mocks.
    """
    patch_vision(monkeypatch)
    reader = CurrencyReader(poll_interval=0.05)
    reader.start()
    time.sleep(0.1)
    reader.stop()
    reader.stop()  # Should not error
    assert not reader.is_running()


def read_currency_amount_from_image(img, debug=False):
    """
    Extracts an integer currency amount from an image using OCR.
    
    Parameters:
        img (np.ndarray): Input image expected as grayscale, BGR/RGB (3-channel), or BGRA/RGBA (4-channel).
        debug (bool): If True, prints the detected integer and the raw OCR text for debugging.
    
    Returns:
        int: Parsed currency value, or 0 if no digits are found or an error occurs.
    """
    try:
        cv2.setUseOptimized(True)
        cv2.setNumThreads(1)
        # Handle grayscale, 3-channel, and 4-channel images explicitly
        if img.ndim == 2:
            # Already grayscale
            gray = img
        elif img.ndim == 3:
            if img.shape[2] == 4:
                # BGRA/RGBA to BGR/RGB first, then to grayscale
                bgr_img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
            elif img.shape[2] == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                # Unexpected channel count, fallback
                gray = img
        else:
            # Unexpected shape, fallback
            gray = img
        _, thresh = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        inverted = cv2.bitwise_not(thresh)
        rgb = cv2.cvtColor(inverted, cv2.COLOR_GRAY2RGB)
        pil_img = Image.fromarray(rgb)
        custom_config = r"--psm 7 -c tessedit_char_whitelist=0123456789,"
        raw_text = pytesseract.image_to_string(pil_img, config=custom_config)
        digits = "".join([c for c in raw_text if c.isdigit()])
        value = int(digits) if digits else 0
        if debug:
            print(f"[OCR] Currency: {value} (raw: {raw_text})")
        return value
    except Exception as e:  # noqa: BLE001  # intentional fallback for test semantics
        print(f"Preprocessing/OCR error: {e}")
        return 0


def get_image_param_list():
    """
    Collect PNG test images from the tests/images directory and pair each file path with the integer parsed from its filename.
    
    Files whose basenames cannot be parsed as an integer are skipped.
    
    Returns:
        list: A list of (path, expected) tuples where `path` is the image file path and `expected` is the integer obtained from the filename.
    """
    param_list = []
    for path in glob.glob(
        os.path.join(os.path.dirname(__file__), "images", "*.png")
    ):
        basename = os.path.splitext(os.path.basename(path))[0]
        try:
            expected = int(basename)
            param_list.append((path, expected))
        except ValueError:
            continue
    return param_list


@pytest.mark.parametrize("img_path,expected", get_image_param_list())
def test_currency_reader_on_images(img_path, expected):
    """
    Test OCR currency reading on actual PNG images in tests/images.
    Each image is named after the currency value it shows (e.g., 12345.png).
    """
    img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
    assert img is not None, f"Failed to read test image: {img_path}"
    result = read_currency_amount_from_image(img)
    assert result == expected, (
        f"OCR result {result} != expected {expected} for {img_path}"
    )