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
            self.calls = 0
        def grab(self, region=None):
            self.calls += 1
            if self.calls > 1:
                raise KeyboardInterrupt()
            # Create a dummy image with digits '12345' drawn
            img = np.ones((45, 165, 4), dtype=np.uint8) * 255
            cv2.putText(img, '12345', (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,0,255), 2)
            return img
        def stop(self):
            pass
    class DummyOCR:
        def __init__(self, *args, **kwargs):
            pass
        def readtext(self, img, allowlist=None, detail=1):
            # Simulate EasyOCR output: [(bbox, text, confidence)]
            return [((0,0,0,0), '12345', 0.99)]
    monkeypatch.setattr(vision, 'easyocr_available', True)
    # Patch easyocr.Reader to return an instance of DummyOCR
    class DummyEasyOCR:
        @staticmethod
        def Reader(langs, gpu):
            return DummyOCR()
    monkeypatch.setattr(vision, 'easyocr', DummyEasyOCR)
    monkeypatch.setattr(__import__('dxcam'), 'create', lambda output_idx=0: DummyCamera())
    # Run the function (debug off, should return 12345)
    value = vision.read_currency_amount(debug=False)
    assert value == 12345
