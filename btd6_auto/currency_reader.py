"""
Currency reading module for BTD6 Automation Bot.
Runs currency OCR in a background thread for non-blocking access.
"""

import threading
import time
import logging

from btd6_auto.vision import read_currency_amount


class CurrencyReader:
    """
    Continuously reads the in-game currency in a background thread.
    Provides thread-safe access to the latest value.
    """

    def __init__(self, region: tuple = (367, 15, 515, 70), poll_interval: float = 0.5):
        """
        Initialize the currency reader.
        Parameters:
            region (tuple): Screen region for OCR.
            poll_interval (float): Time between reads in seconds.
        """
        self.region = region
        self.poll_interval = poll_interval
        self._currency = 0
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the background currency reading thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logging.info("CurrencyReader thread started.")

    def stop(self) -> None:
        """Stop the background thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            logging.info("CurrencyReader thread stopped.")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            value = read_currency_amount(region=self.region, debug=False)
            logging.debug(f"CurrencyReader OCR value: {value}")
            with self._lock:
                self._currency = value
            time.sleep(self.poll_interval)

    def get_currency(self) -> int:
        """Get the latest currency value (thread-safe)."""
        with self._lock:
            return self._currency

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
