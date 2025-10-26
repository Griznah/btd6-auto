import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import numpy as np
import cv2
from btd6_auto.currency_reader import CurrencyReader

class DummyCamera:
    def __init__(self):
        self.calls = 0
    def grab(self, region=None):
        self.calls += 1
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
        return [((0,0,0,0), '12345', 0.99)]

def patch_vision(monkeypatch):
    import btd6_auto.vision as vision
    monkeypatch.setattr(vision, 'easyocr_available', True)
    class DummyEasyOCR:
        @staticmethod
        def Reader(langs, gpu):
            return DummyOCR()
    monkeypatch.setattr(vision, 'easyocr', DummyEasyOCR)
    monkeypatch.setattr(__import__('dxcam'), 'create', lambda output_idx=0: DummyCamera())
    # Patch vision.read_currency_amount to use dummy camera/ocr
    def dummy_read_currency_amount(region=(370, 26, 515, 60), debug=False):
        return 12345
    monkeypatch.setattr(vision, 'read_currency_amount', dummy_read_currency_amount)


def test_currency_reader_thread(monkeypatch):
    patch_vision(monkeypatch)
    reader = CurrencyReader(poll_interval=0.1)
    reader.start()
    time.sleep(0.2)  # Allow thread to run at least once
    value = reader.get_currency()
    assert value == 12345
    reader.stop()
    assert not reader.is_running()


def test_currency_reader_multiple_reads(monkeypatch):
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
    patch_vision(monkeypatch)
    reader = CurrencyReader(poll_interval=0.05)
    reader.start()
    time.sleep(0.1)
    reader.stop()
    reader.stop()  # Should not error
    assert not reader.is_running()
