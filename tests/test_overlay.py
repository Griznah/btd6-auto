"""
Unit tests for overlay.py overlay functionality.
Note: These tests only check import, function signature, and thread launch.
Actual overlay display cannot be tested in headless or CI environments.
"""

import sys
import os
import threading

# ...existing code...
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

if sys.platform.startswith("win"):
    from btd6_auto import overlay
else:
    overlay = None


def test_import_overlay():
    """
    Test that the overlay module is imported correctly on Windows.
    On non-Windows platforms, overlay should be None.
    """
    if sys.platform.startswith("win"):
        assert overlay is not None
    else:
        assert overlay is None


def test_show_overlay_text_runs_thread(monkeypatch):
    """
    Test that show_overlay_text launches a thread on Windows.
    Uses monkeypatch to replace threading.Thread and checks that it is called.
    Skips test on non-Windows platforms.
    """
    if not sys.platform.startswith("win"):
        pytest.skip("Windows-only test")
    started = threading.Event()

    def fake_thread(*args, **kwargs):
        started.set()

        class DummyThread:
            def start(self_inner):
                pass

        return DummyThread()

    monkeypatch.setattr(threading, "Thread", fake_thread)
    overlay.show_overlay_text("Test", 1)
    assert started.is_set()


def test_show_overlay_text_signature():
    """
    Test that show_overlay_text has the correct function signature on Windows.
    Checks that the function is callable and has expected parameters.
    """
    if sys.platform.startswith("win"):
        assert callable(overlay.show_overlay_text)
        import inspect

        sig = inspect.signature(overlay.show_overlay_text)
        assert "overlay_text" in sig.parameters
        assert "seconds" in sig.parameters
