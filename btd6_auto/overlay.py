"""
Overlay utility for displaying click-through, always-on-top text overlays (Windows-only).
"""

import sys
import threading
import time

if sys.platform.startswith("win"):
    import win32con
    import win32gui
    import win32api
else:
    raise ImportError("overlay.py only works on Windows platforms.")

def show_overlay_text(overlay_text: str, seconds: int):
    """
    Display a transparent, always-on-top, click-through overlay with the given text for a specified duration.

    Parameters:
        overlay_text (str): The text to display.
        seconds (int): How many seconds to show the overlay.
    """
    def overlay_thread():
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
                    # Set transparent background for text
                    win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
                    # Set text color to red
                    win32gui.SetTextColor(hdc, win32api.RGB(255, 0, 0))
                    # Create a large font
                    lf = win32gui.LOGFONT()
                    lf.lfHeight = 36  # Large font size
                    lf.lfWeight = win32con.FW_BOLD
                    lf.lfFaceName = "Arial"
                    hfont = win32gui.CreateFontIndirect(lf)
                    oldfont = win32gui.SelectObject(hdc, hfont)
                    # Draw text, left aligned, vertically centered
                    win32gui.DrawText(
                        hdc, self.text, -1, rect,
                        win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE
                    )
                    win32gui.SelectObject(hdc, oldfont)
                    win32gui.DeleteObject(hfont)
                    win32gui.EndPaint(hwnd, paintStruct)
                    return 0
                elif msg == win32con.WM_DESTROY:
                    win32gui.PostQuitMessage(0)
                    return 0
                else:
                    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

            def run(self, x, y, width, height, duration):
                wndclass = win32gui.WNDCLASS()
                wndclass.lpfnWndProc = self.wnd_proc
                wndclass.hInstance = self.hInstance
                wndclass.lpszClassName = self.className
                wndclass.hCursor = win32gui.LoadCursor(None, win32con.IDC_ARROW)
                wndclass.hbrBackground = 0  # No background brush for full transparency
                try:
                    atom = win32gui.RegisterClass(wndclass)
                except win32gui.error as e:
                    if hasattr(e, 'winerror') and e.winerror == 1410:  # Class already exists
                        atom = win32gui.GetClassInfo(wndclass.hInstance, wndclass.lpszClassName)
                    else:
                        raise

                exStyle = (win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST |
                           win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOOLWINDOW)
                style = win32con.WS_POPUP

                self.hwnd = win32gui.CreateWindowEx(
                    exStyle,
                    atom,
                    None,
                    style,
                    x, y, width, height,
                    0, 0, self.hInstance, None
                )

                # Set color key to black for full transparency
                win32gui.SetLayeredWindowAttributes(self.hwnd, 0x000000, 255, win32con.LWA_COLORKEY)
                win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNORMAL)

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

        # Window size and position
        x, y = 200, 800
        width, height = 600, 60
        OverlayWindow(overlay_text).run(x, y, width, height, seconds)

    t = threading.Thread(target=overlay_thread, daemon=True)
    t.start()
