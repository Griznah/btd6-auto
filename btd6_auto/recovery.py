"""
Operation recovery mechanisms for BTD6 automation.

This module provides recovery strategies for common failure scenarios,
allowing the bot to automatically recover from transient issues.
"""

import logging
import time
from typing import Callable, Any, Dict, List, Optional, Tuple, Union

from .exceptions import (
    WindowNotFoundError, WindowActivationError, GameStateError,
    ClickFailedError, OperationTimeoutError, BTD6AutomationError
)
from .config import _get_config_manager
from .retry_utils import retry


class RecoveryManager:
    """
    Manages operation recovery strategies for BTD6 automation.

    This class provides various recovery mechanisms that can be applied
    when operations fail, allowing the bot to automatically recover
    from common transient issues.
    """

    def __init__(self):
        """Initialize recovery manager."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = _get_config_manager()
        self.recovery_attempts = {}

    def recover_window_focus(self) -> bool:
        """
        Attempt to recover window focus if lost.

        Returns:
            bool: True if recovery successful, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from .game_launcher import activate_btd6_window

            self.logger.info("Attempting to recover window focus...")
            return activate_btd6_window()

        except Exception as e:
            self.logger.error(f"Window focus recovery failed: {e}")
            return False

    def recover_game_state(self) -> bool:
        """
        Attempt to recover game state by restarting map.

        Returns:
            bool: True if recovery successful, False otherwise
        """
        try:
            self.logger.info("Attempting to recover game state...")

            # Import here to avoid circular imports
            from .game_launcher import activate_btd6_window, start_map

            if not self.recover_window_focus():
                return False

            time.sleep(2)  # Give window time to activate

            return start_map()

        except Exception as e:
            self.logger.error(f"Game state recovery failed: {e}")
            return False

    def recover_with_alternative_coordinates(
        self,
        primary_coords: Tuple[int, int],
        alternative_coords: List[Tuple[int, int]],
        click_function: Callable,
        *args,
        **kwargs
    ) -> bool:
        """
        Attempt operation with alternative coordinates if primary fails.

        Args:
            primary_coords: Primary coordinates to try first
            alternative_coords: List of alternative coordinates to try
            click_function: Function to call for clicking
            *args, **kwargs: Additional arguments for click_function

        Returns:
            bool: True if any coordinate attempt succeeded
        """
        all_coords = [primary_coords] + alternative_coords

        for i, coords in enumerate(all_coords):
            try:
                self.logger.info(f"Trying coordinates {coords} (attempt {i + 1}/{len(all_coords)})")

                # Call with explicit x, y; additional args/kwargs are forwarded
                click_function(coords[0], coords[1], *args, **kwargs)
                self.logger.info(f"Click succeeded with coordinates {coords}")
                return True

            except Exception as e:
                self.logger.warning(f"Click failed with coordinates {coords}: {e}")
                if i < len(all_coords) - 1:
                    time.sleep(0.5)  # Brief pause before trying next coordinates
                continue

        self.logger.error("All coordinate attempts failed")
        return False

    def recover_with_timing_adjustment(
        self,
        operation: Callable,
        timing_adjustments: List[float] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Attempt operation with different timing delays if initial attempt fails.

        Args:
            operation: Function to execute
            timing_adjustments: List of delay adjustments to try (seconds)
            *args, **kwargs: Arguments for the operation

        Returns:
            Operation result if successful, None otherwise
        """
        if timing_adjustments is None:
            timing_adjustments = [0.1, 0.5, 1.0, 2.0]

        for delay in timing_adjustments:
            try:
                self.logger.info(f"Trying operation with {delay}s delay")

                if 'delay' in kwargs:
                    kwargs['delay'] = delay
                else:
                    kwargs['delay'] = delay

                result = operation(*args, **kwargs)
                self.logger.info(f"Operation succeeded with {delay}s delay")
                return result

            except Exception as e:
                self.logger.warning(f"Operation failed with {delay}s delay: {e}")
                continue

        self.logger.error("All timing adjustments failed")
        return None

    @retry(max_retries=3, base_delay=1.0)
    def robust_click(self, x: int, y: int, button: str = 'left', clicks: int = 1) -> bool:
        """
        Perform a robust click operation with automatic retry and recovery.

        Args:
            x, y: Click coordinates
            button: Mouse button to use
            clicks: Number of clicks

        Returns:
            bool: True if click succeeded
        """
        try:
            import pyautogui


            # Ensure coordinates are valid
            if not isinstance(x, int) or not isinstance(y, int):
                raise ValueError(f"Invalid coordinates: ({x}, {y}) must be integers.")
            if x < 0 or y < 0:
                raise ValueError(f"Invalid coordinates: ({x}, {y}) must be non-negative.")

            # Move to position and click
            pyautogui.click(x, y, button=button, clicks=clicks)

            # Verify the click was registered (basic check)
            time.sleep(0.1)  # Brief pause for system to register

            return True

        except Exception as e:
            # Only wrap unexpected exceptions as ClickFailedError
            raise ClickFailedError((x, y)) from e

    @retry(max_retries=3, base_delay=1.0)
    def robust_key_press(self, key: str, presses: int = 1) -> bool:
        """
        Perform a robust key press operation with automatic retry and recovery.

        Args:
            key: Key to press
            presses: Number of times to press the key

        Returns:
            bool: True if key press succeeded
        """
        try:
            import pyautogui

            # Ensure key is valid
            if not isinstance(key, str):
                raise ValueError(f"Invalid key type: {key} (must be str)")
            allowed_keys = set(getattr(pyautogui, "KEYBOARD_KEYS", []))
            if key not in allowed_keys:
                raise ValueError(f"Invalid key: '{key}' not in allowed keys: {allowed_keys}")

            # Press the key
            try:
                pyautogui.press(key, presses=presses)
            except Exception as e:
                self.logger.error(f"pyautogui.press failed for key '{key}': {e}")
                raise

            # Verify the key press was registered (basic check)
            time.sleep(0.1)

            return True

        except Exception as e:
            # Only wrap unexpected exceptions for retry
            raise

    def execute_with_fallbacks(
        self,
        primary_operation: Callable,
        fallback_operations: List[Callable],
        operation_name: str = "operation",
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with fallback strategies.

        Args:
            primary_operation: Primary operation to attempt
            fallback_operations: List of fallback operations to try
            operation_name: Name for logging
            *args, **kwargs: Arguments for operations

        Returns:
            Result of first successful operation, None if all fail
        """
        all_operations = [primary_operation] + fallback_operations

        for i, operation in enumerate(all_operations):
            try:
                op_name = f"{operation_name}_fallback_{i+1}" if i > 0 else operation_name
                self.logger.info(f"Attempting {op_name}")

                result = operation(*args, **kwargs)

                if i > 0:
                    self.logger.info(f"Fallback {op_name} succeeded")
                else:
                    self.logger.info(f"Primary operation {operation_name} succeeded")

                return result

            except Exception as e:
                self.logger.warning(f"{op_name} failed: {e}")
                if i < len(all_operations) - 1:
                    time.sleep(1.0)  # Brief pause before trying next operation
                continue

        self.logger.error(f"All operations failed for {operation_name}")
        return None

    def reset_game_if_necessary(self) -> bool:
        """
        Reset game state if it appears to be in an invalid state.

        This is a last-resort recovery mechanism that should be used
        sparingly to avoid disrupting user gameplay.

        Returns:
            bool: True if reset was attempted (regardless of success)
        """
        try:
            self.logger.warning("Attempting emergency game reset...")

            # This would need to be implemented based on specific game mechanics
            # For now, we'll try to restart the map
            return self.recover_game_state()

        except Exception as e:
            self.logger.error(f"Emergency game reset failed: {e}")
            return False


# Global recovery manager instance
_recovery_manager = None


def get_recovery_manager() -> RecoveryManager:
    """Get or create global recovery manager instance."""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = RecoveryManager()
    return _recovery_manager


def with_window_recovery(operation: Callable) -> Callable:
    """
    Decorator that adds window focus recovery to any operation.

    Args:
        operation: Function to decorate

    Returns:
        Decorated function with window recovery
    """
    def decorated(*args, **kwargs):
        recovery_manager = get_recovery_manager()

        try:
            return operation(*args, **kwargs)
        except (WindowNotFoundError, WindowActivationError):
            if recovery_manager.recover_window_focus():
                # Retry the operation once after window recovery
                return operation(*args, **kwargs)
            else:
                raise

    return decorated


def with_game_state_recovery(operation: Callable) -> Callable:
    """
    Decorator that adds game state recovery to any operation.

    Args:
        operation: Function to decorate

    Returns:
        Decorated function with game state recovery
    """
    def decorated(*args, **kwargs):
        recovery_manager = get_recovery_manager()

        try:
            return operation(*args, **kwargs)
        except GameStateError:
            if recovery_manager.recover_game_state():
                # Retry the operation once after game state recovery
                return operation(*args, **kwargs)
            else:
                raise

    return decorated


def with_full_recovery(operation: Callable) -> Callable:
    """
    Decorator that adds comprehensive recovery mechanisms to any operation.

    This includes window recovery, game state recovery, and retry logic.

    Args:
        operation: Function to decorate

    Returns:
        Decorated function with full recovery capabilities
    """
    @with_game_state_recovery
    @with_window_recovery
    @retry(max_retries=3, base_delay=1.0)
    def decorated(*args, **kwargs):
        return operation(*args, **kwargs)

    return decorated
