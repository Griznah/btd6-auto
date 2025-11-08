import sys
import os
import numpy as np

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)


def fake_capture_screen_found(*args, **kwargs):
    """
    Simulate capture_screen returning a dummy image (bgr, gray).

    Returns:
        Tuple[np.ndarray, np.ndarray]: Dummy BGR and grayscale images.
    """
    img = np.ones((100, 100), dtype=np.uint8) * 127
    return (img, img)


def fake_capture_screen_none(*args, **kwargs):
    """
    Simulate capture_screen returning None for both images.

    Returns:
        Tuple[None, None]: No images captured.
    """
    return (None, None)


def fake_cv2_imread(path, flags):
    """
    Simulate cv2.imread returning a dummy template image.

    Args:
        path (str): Path to image file.
        flags (int): cv2 read flags.
    Returns:
        np.ndarray: Dummy template image.
    """
    return np.ones((10, 10), dtype=np.uint8) * 127


def fake_cv2_matchTemplate(img, template, method):
    """
    Simulate cv2.matchTemplate returning a result with a clear max match.

    Args:
        img (np.ndarray): Source image.
        template (np.ndarray): Template image.
        method (int): Matching method.
    Returns:
        np.ndarray: Result matrix with a strong match at (50, 50).
    """
    res = np.zeros((91, 91), dtype=np.float32)
    res[50, 50] = 1.0  # Simulate a strong match
    return res


def fake_cv2_minMaxLoc(res):
    """
    Simulate cv2.minMaxLoc returning a max location at (50, 50).

    Args:
        res (np.ndarray): Result matrix from matchTemplate.
    Returns:
        tuple: (min_val, max_val, min_loc, max_loc)
    """
    return (0, 1.0, (0, 0), (50, 50))


def test_find_element_on_screen_found(monkeypatch):
    """
    Test find_element_on_screen returns correct coordinates when element is found.
    Mocks capture_screen, cv2.imread, matchTemplate, and minMaxLoc for a strong match.
    """
    from btd6_auto import vision

    monkeypatch.setattr(vision, "capture_screen", fake_capture_screen_found)
    monkeypatch.setattr("cv2.imread", fake_cv2_imread)
    monkeypatch.setattr("cv2.matchTemplate", fake_cv2_matchTemplate)
    monkeypatch.setattr("cv2.minMaxLoc", fake_cv2_minMaxLoc)
    coords = vision.find_element_on_screen("dummy_path.png")
    assert coords == (55, 55)  # 50 + 10//2


def test_find_element_on_screen_not_found(monkeypatch):
    """
    Test find_element_on_screen returns None when no strong match is found.
    Mocks matchTemplate to return no match and minMaxLoc to return low max value.
    """
    from btd6_auto import vision

    monkeypatch.setattr(vision, "capture_screen", fake_capture_screen_found)
    monkeypatch.setattr("cv2.imread", fake_cv2_imread)

    def matchTemplate_no_match(img, template, method):
        return np.zeros((91, 91), dtype=np.float32)

    monkeypatch.setattr("cv2.matchTemplate", matchTemplate_no_match)
    monkeypatch.setattr(
        "cv2.minMaxLoc", lambda res: (0, 0.5, (0, 0), (10, 10))
    )
    coords = vision.find_element_on_screen("dummy_path.png")
    assert coords is None


def test_find_element_on_screen_error(monkeypatch):
    """
    Test find_element_on_screen returns None when capture_screen returns None.
    Simulates error or missing screen capture.
    """
    from btd6_auto import vision

    monkeypatch.setattr(vision, "capture_screen", fake_capture_screen_none)
    coords = vision.find_element_on_screen("dummy_path.png")
    assert coords is None
