"""
Overlay utility for displaying click-through, always-on-top text overlays (Windows-only).

Features:
- True transparent overlay using color key (black)
- Large, left-aligned red text
- Robust window class registration
- Thread-safe overlay creation
- Resource management and logging
"""

import sys
import threading
import time
import logging
from typing import Optional


if sys.platform.startswith("win"):
    import win32con
    import win32gui
    import win32api
    _class_lock = threading.Lock()
else:
    raise ImportError("overlay.py only works on Windows platforms.")

# Singleton overlay management
_current_overlay_thread: Optional[threading.Thread] = None
_current_overlay_hwnd: Optional[int] = None
_overlay_lock = threading.Lock()


class OverlayWindow:
    def __init__(self, text):
        self.text = text
        self.hInstance = win32api.GetModuleHandle(None)
        self.className = "OverlayWindowClass"
        self.hwnd = None

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_PAINT:
            hdc, paintStruct = win32gui.BeginPaint(hwnd)
            rect = win32gui.GetClientRect(hwnd)
            # Fill background with black (color key for transparency)
            brush = win32gui.GetStockObject(win32con.BLACK_BRUSH)
            win32gui.FillRect(hdc, rect, brush)
            win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
            win32gui.SetTextColor(hdc, win32api.RGB(255, 0, 0))
            # Create a large, bold Arial font
            try:
                lf = win32gui.LOGFONT()
                lf.lfHeight = 36  # Large font size
                lf.lfWeight = win32con.FW_BOLD
                lf.lfFaceName = "Arial"
                hfont = win32gui.CreateFontIndirect(lf)
                oldfont = win32gui.SelectObject(hdc, hfont)
            except Exception as e:
                logging.exception("Overlay font creation failed:")
                hfont = None
                oldfont = None
            # Draw text, left aligned, vertically centered
            win32gui.DrawText(
                hdc, self.text, -1, rect,
                win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE
            )
            # Cleanup font resources
            if oldfont:
                win32gui.SelectObject(hdc, oldfont)
            if hfont:
                win32gui.DeleteObject(hfont)
            win32gui.EndPaint(hwnd, paintStruct)
            return 0
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            logging.info("Overlay closed.")
            return 0
        else:
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def run(self, x, y, width, height, duration):
        """
        Create and show the overlay window. Handles window class registration and resource management.
        """
        with _class_lock:
            wndclass = win32gui.WNDCLASS()
            wndclass.lpfnWndProc = self.wnd_proc
            wndclass.hInstance = self.hInstance
            wndclass.lpszClassName = self.className
            wndclass.hCursor = win32gui.LoadCursor(None, win32con.IDC_ARROW)
            wndclass.hbrBackground = 0  # No background brush for full transparency
            try:
                # Register window class if not already registered
                win32gui.RegisterClass(wndclass)
                logging.info("Overlay window class registered.")
            except win32gui.error as e:
                if hasattr(e, 'winerror') and e.winerror == 1410:  # Class already exists
                    logging.info("Overlay window class already registered.")
                else:
                    logging.exception("Overlay window class registration failed:")
                    raise
        # Always use class name for CreateWindowEx (works for both new and existing classes)
        atom = self.className

        exStyle = (win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST |
                   win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOOLWINDOW)
        style = win32con.WS_POPUP

        try:
            self.hwnd = win32gui.CreateWindowEx(
                exStyle,
                atom,
                None,
                style,
                x, y, width, height,
                0, 0, self.hInstance, None
            )
        except Exception as e:
            logging.exception("Overlay window creation failed:")
            return

        # Set color key to black for full transparency
        win32gui.SetLayeredWindowAttributes(self.hwnd, 0x000000, 255, win32con.LWA_COLORKEY)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNORMAL)
        logging.info(f"Overlay shown: '{self.text}' at ({x},{y}) for {duration}s.")

        # Store hwnd for singleton management
        global _current_overlay_hwnd
        with _overlay_lock:
            _current_overlay_hwnd = self.hwnd

        # Timer to close window after duration
        def close_after_delay():
            time.sleep(duration)
            if self.hwnd:
                win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
        threading.Thread(target=close_after_delay, daemon=True).start()

        # Message loop
        while True:
            msg_tuple = win32gui.GetMessage(self.hwnd, 0, 0)
            if not msg_tuple:
                break
            msg = msg_tuple[1]
            win32gui.TranslateMessage(msg)
            win32gui.DispatchMessage(msg)

        # Cleanup hwnd after window closes
        with _overlay_lock:
            if _current_overlay_hwnd == self.hwnd:
                _current_overlay_hwnd = None

def show_overlay_text(overlay_text: str, seconds: int):
    """
    Display a transparent, always-on-top, click-through overlay with the given text for a specified duration.
    Now supports updating the overlay text between calls (singleton overlay window).

    Parameters:
        overlay_text (str): The text to display.
        seconds (int): How many seconds to show the overlay.

    Platform:
        Windows only. Uses Win32 API via pywin32.

    Overlay:
        - Large, bold, left-aligned red text
        - Fully transparent background (no gray box)
        - Click-through, always-on-top
    """
    global _current_overlay_thread, _current_overlay_hwnd
    with _overlay_lock:
        # If an overlay is running, close it
        if _current_overlay_hwnd:
            try:
                win32gui.PostMessage(_current_overlay_hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass
            _current_overlay_hwnd = None
        # Optionally join previous thread (not strictly necessary)
        if _current_overlay_thread and _current_overlay_thread.is_alive():
            # Let the thread exit naturally
            pass

        def overlay_thread():
            x, y = 200, 800
            width, height = 600, 60
            OverlayWindow(overlay_text).run(x, y, width, height, seconds)

        t = threading.Thread(target=overlay_thread, daemon=True)
        _current_overlay_thread = t
        t.start()
