import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import numpy as np
import cv2
from btd6_auto import vision

def test_read_currency_amount_mock(monkeypatch):
    # Mock dxcam and EasyOCR for unit test
    class DummyCamera:
        def __init__(self):
            """
            Initialize the DummyCamera instance.
            
            Sets up an internal `calls` counter (starting at 0) used to track how many times `grab` has been invoked.
            """
            self.calls = 0
        def grab(self, region=None):
            """
            Return a synthetic RGBA image containing the digits "12345" and simulate a single successful capture.
            
            Parameters:
                region (optional): Ignored in this dummy implementation; present for API compatibility.
            
            Returns:
                np.ndarray: A uint8 RGBA image of shape (45, 165, 4) with a white background and the text "12345" drawn in black.
            
            Notes:
                Each call increments the instance's `calls` counter; on the second and subsequent calls this method raises KeyboardInterrupt to simulate camera interruption.
            """
            self.calls += 1
            if self.calls > 1:
                raise KeyboardInterrupt()
            # Create a dummy image with digits '12345' drawn
            img = np.ones((45, 165, 4), dtype=np.uint8) * 255
            cv2.putText(img, '12345', (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,0,255), 2)
            return img
        def stop(self):
            """
            Stop the camera capture.
            
            No-op for the dummy camera implementation; present to satisfy the camera interface.
            """
            pass
    class DummyOCR:
        def __init__(self, *args, **kwargs):
            """
            Create a dummy object that accepts and ignores any constructor arguments.
            
            Parameters:
                *args: Positional arguments that are accepted and ignored.
                **kwargs: Keyword arguments that are accepted and ignored.
            """
            pass
        def readtext(self, img, allowlist=None, detail=1):
            # Simulate EasyOCR output: [(bbox, text, confidence)]
            """
            Return a simulated EasyOCR `readtext` output for testing.
            
            Parameters:
                img: Image input (ignored) used to mimic OCR processing.
                allowlist (str|None): Characters to limit recognition to (ignored).
                detail (int): Level of detail requested (ignored).
            
            Returns:
                list: A single-item list containing a tuple (bbox, text, confidence), where
                    bbox is (0, 0, 0, 0), text is '12345', and confidence is 0.99.
            """
            return [((0,0,0,0), '12345', 0.99)]
    monkeypatch.setattr(vision, 'easyocr_available', True)
    # Patch easyocr.Reader to return an instance of DummyOCR
    class DummyEasyOCR:
        @staticmethod
        def Reader(langs, gpu):
            """
            Create a mock OCR reader compatible with EasyOCR's Reader interface for tests.
            
            Parameters:
                langs (sequence): Languages requested for the OCR reader (ignored).
                gpu (bool): Whether GPU acceleration is requested (ignored).
            
            Returns:
                DummyOCR: A mock OCR reader instance that implements `readtext`.
            """
            return DummyOCR()
    monkeypatch.setattr(vision, 'easyocr', DummyEasyOCR)
    monkeypatch.setattr(__import__('dxcam'), 'create', lambda output_idx=0: DummyCamera())
    # Run the function (debug off, should return 12345)
    value = vision.read_currency_amount(debug=False)
    assert value == 12345