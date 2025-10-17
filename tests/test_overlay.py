"""
Unit tests for overlay.py overlay functionality.
Note: These tests only check import, function signature, and thread launch.
Actual overlay display cannot be tested in headless or CI environments.
"""
import sys
import threading
import time
import pytest

if sys.platform.startswith("win"):
    from btd6_auto import overlay
else:
    overlay = None

def test_import_overlay():
    if sys.platform.startswith("win"):
        assert overlay is not None
    else:
        assert overlay is None

def test_show_overlay_text_runs_thread(monkeypatch):
    if not sys.platform.startswith("win"):
        pytest.skip("Windows-only test")
    started = threading.Event()
    def fake_overlay_thread():
        started.set()
    monkeypatch.setattr(overlay, "overlay_thread", fake_overlay_thread)
    overlay.show_overlay_text("Test", 1)
    assert started.wait(timeout=2)

def test_show_overlay_text_signature():
    if sys.platform.startswith("win"):
        assert callable(overlay.show_overlay_text)
        import inspect
        sig = inspect.signature(overlay.show_overlay_text)
        assert "overlay_text" in sig.parameters
        assert "seconds" in sig.parameters
