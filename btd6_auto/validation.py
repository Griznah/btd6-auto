"""
Input validation and bounds checking utilities for BTD6 automation.

This module provides validation functions for coordinates, inputs, and game state
to prevent runtime errors and ensure reliable automation.
"""

import logging
import platform
from typing import Any, Dict, List, Tuple, Optional

try:
    import tkinter as tk
except ModuleNotFoundError:
    tk = None
from .exceptions import (
    InvalidCoordinateError,
    InvalidKeyError,
    BTD6AutomationError,
    WindowNotFoundError,
    WindowActivationError,
    MapNotLoadedError,
    GameStateError,
)
from .config import _get_config_manager
from screeninfo import get_monitors



class CoordinateValidator:
    """
    Validates screen coordinates and provides coordinate utilities.

    This class handles coordinate validation, bounds checking, and
    coordinate transformation for reliable automation.
    """

    def __init__(self):
        """Initialize coordinate validator."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = _get_config_manager()
        self._screen_bounds = self._get_screen_bounds()

    def _get_screen_bounds(self) -> Dict[str, Tuple[int, int]]:
        """
        Get the bounds of all available screens.

        Returns:
            Dict mapping screen identifiers to (width, height) tuples
        """
        try:
            bounds = {}

            # Try to get screen info using screeninfo library
            monitors = get_monitors()
            for i, monitor in enumerate(monitors):
                bounds[f"monitor_{i}"] = (monitor.width, monitor.height)
                if i == 0:  # Primary monitor
                    bounds["primary"] = (monitor.width, monitor.height)

            # Fallback to tkinter if screeninfo fails
            if not bounds:
                if tk is not None:
                    root = tk.Tk()
                    root.withdraw()  # Hide the window
                    screen_width = root.winfo_screenwidth()
                    screen_height = root.winfo_screenheight()
                    bounds["primary"] = (screen_width, screen_height)
                    root.destroy()
                else:
                    # Final fallback
                    bounds["primary"] = (1920, 1080)
            self.logger.info(f"Detected screen bounds: {bounds}")
            return bounds

        except Exception as e:
            self.logger.warning(f"Failed to get screen bounds: {e}")
            # Fallback to common resolutions
            return {"primary": (1920, 1080)}

    def validate_coordinates(self, coordinates: Tuple[int, int], context: str = "operation") -> Tuple[int, int]:
        """
        Validate that coordinates are within screen bounds.

        Args:
            coordinates: (x, y) coordinate tuple to validate
            context: Description of where coordinates are used for error messages

        Returns:
            Validated coordinates tuple

        Raises:
            InvalidCoordinateError: If coordinates are invalid
        """
        if not isinstance(coordinates, tuple) or len(coordinates) != 2:
            raise InvalidCoordinateError(
                coordinates,
                operation=f"coordinate_validation_{context}",
                details={"reason": "must be (x, y) tuple"}
            )

        x, y = coordinates

        if not isinstance(x, int) or not isinstance(y, int):
            raise InvalidCoordinateError(
                coordinates,
                operation=f"coordinate_validation_{context}",
                details={"reason": "coordinates must be integers"}
            )

        if x < 0 or y < 0:
            raise InvalidCoordinateError(
                coordinates,
                operation=f"coordinate_validation_{context}",
                details={"reason": "coordinates must be non-negative"}
            )

        # Check against screen bounds
        max_x, max_y = self._screen_bounds.get("primary", (1920, 1080))

        if x > max_x - 1 or y > max_y - 1:
            raise InvalidCoordinateError(
                coordinates,
                operation=f"coordinate_validation_{context}",
                details={
                    "reason": f"coordinates must be within [0, {max_x - 1}] for x and [0, {max_y - 1}] for y",
                    "screen_bounds": (max_x, max_y)
                }
            )

        return coordinates

    def validate_coordinate_range(self, coordinates: List[Tuple[int, int]], context: str = "batch") -> List[Tuple[int, int]]:
        """
        Validate a list of coordinates.

        Args:
            coordinates: List of (x, y) coordinate tuples
            context: Description for error messages

        Returns:
            List of validated coordinates

        Raises:
            InvalidCoordinateError: If any coordinates are invalid
        """
        validated = []
        for i, coords in enumerate(coordinates):
            try:
                validated_coords = self.validate_coordinates(coords, f"{context}_item_{i}")
                validated.append(validated_coords)
            except InvalidCoordinateError as e:
                e.details = {**e.details, "index": i}
                raise

        return validated

    def check_coordinate_conflicts(self, coordinates: List[Tuple[int, int]], min_distance: int = 10) -> List[Tuple[int, int]]:
        """
        Check for potential coordinate conflicts (coordinates too close together).

        Args:
            coordinates: List of coordinates to check
            min_distance: Minimum distance required between coordinates

        Returns:
            List of coordinates that have conflicts (coordinates too close)

        Raises:
            BTD6AutomationError: If severe conflicts are found
        """
        conflicts = []

        for i, coord1 in enumerate(coordinates):
            for j, coord2 in enumerate(coordinates[i+1:], i+1):
                distance = self._calculate_distance(coord1, coord2)
                if distance < min_distance:
                    conflicts.append((coord1, coord2, distance))
                    self.logger.warning(
                        f"Potential coordinate conflict between {coord1} and {coord2}: "
                        f"distance {distance}px < minimum {min_distance}px"
                    )

        if conflicts and len(conflicts) > len(coordinates) * 0.5:  # More than 50% conflicts
            raise BTD6AutomationError(
                f"Too many coordinate conflicts detected ({len(conflicts)} conflicts)",
                operation="coordinate_conflict_check",
                details={"conflicts": conflicts, "min_distance": min_distance}
            )

        return [(c1, c2, dist) for c1, c2, dist in conflicts]

    def _calculate_distance(self, coord1: Tuple[int, int], coord2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two coordinates."""
        x1, y1 = coord1
        x2, y2 = coord2
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    def get_optimal_coordinates(self, target_coords: Tuple[int, int], constraints: Dict[str, Any] = None) -> Tuple[int, int]:
        """
        Get optimal coordinates based on constraints and screen layout.

        Args:
            target_coords: Target coordinates
            constraints: Optional constraints (e.g., {'max_x': 1000, 'max_y': 800})

        Returns:
            Optimized coordinates tuple
        """
        x, y = target_coords

        if constraints:
            if 'max_x' in constraints and x > constraints['max_x']:
                x = constraints['max_x']
            if 'max_y' in constraints and y > constraints['max_y']:
                y = constraints['max_y']
            if 'min_x' in constraints and x < constraints['min_x']:
                x = constraints['min_x']
            if 'min_y' in constraints and y < constraints['min_y']:
                y = constraints['min_y']

        # Ensure coordinates are still within screen bounds
        max_x, max_y = self._screen_bounds.get("primary", (1920, 1080))
        x = max(0, min(x, max_x - 1))
        y = max(0, min(y, max_y - 1))

        return (x, y)

    def transform_coordinates(self, coordinates: Tuple[int, int], transformation: str, **kwargs) -> Tuple[int, int]:
        """
        Transform coordinates based on specified transformation.

        Args:
            coordinates: Base coordinates
            transformation: Type of transformation ('offset', 'scale', 'center', etc.)
            **kwargs: Transformation parameters

        Returns:
            Transformed coordinates
        """
        x, y = coordinates

        if transformation == 'offset':
            offset_x = kwargs.get('offset_x', 0)
            offset_y = kwargs.get('offset_y', 0)
            x += offset_x
            y += offset_y

        elif transformation == 'scale':
            scale_x = kwargs.get('scale_x', 1.0)
            scale_y = kwargs.get('scale_y', 1.0)
            x = int(x * scale_x)
            y = int(y * scale_y)

        elif transformation == 'center':
            # Center coordinates on screen or specified bounds
            center_x = kwargs.get('center_x', self._screen_bounds["primary"][0] // 2)
            center_y = kwargs.get('center_y', self._screen_bounds["primary"][1] // 2)
            x = center_x + kwargs.get('offset_x', 0)
            y = center_y + kwargs.get('offset_y', 0)

        else:
            self.logger.warning(f"Unknown transformation: {transformation}")

        return self.validate_coordinates((x, y))


class InputValidator:
    """
    Validates input parameters and provides input utilities.

    This class handles validation of keyboard inputs, mouse parameters,
    and other automation inputs.
    """

    def __init__(self):
        """Initialize input validator."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = _get_config_manager()

    def validate_key(self, key: str, context: str = "input") -> str:
        """
        Validate keyboard key input.

        Args:
            key: Key string to validate
            context: Description for error messages

        Returns:
            Validated key string

        Raises:
            InvalidKeyError: If key is invalid
        """
        if not isinstance(key, str):
            raise InvalidKeyError(str(key), operation=f"key_validation_{context}")

        if len(key) != 1:
            raise InvalidKeyError(key, operation=f"key_validation_{context}")

        # Basic validation - could be extended with pyautogui key validation
        valid_key_chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        if key.lower() not in valid_key_chars and key not in " \t\n\r":
            self.logger.warning(f"Unusual key character: '{key}'")

        return key

    def validate_click_parameters(self, x: int, y: int, button: str = 'left', clicks: int = 1) -> Dict[str, Any]:
        """
        Validate mouse click parameters.

        Args:
            x, y: Click coordinates
            button: Mouse button ('left', 'right', 'middle')
            clicks: Number of clicks

        Returns:
            Validated parameters dict

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate coordinates
        validator = CoordinateValidator()
        validator.validate_coordinates((x, y), "click")

        # Validate button
        valid_buttons = ['left', 'right', 'middle']
        if button not in valid_buttons:
            raise ValueError(f"Invalid button '{button}', must be one of {valid_buttons}")

        # Validate clicks
        if not isinstance(clicks, int) or clicks < 1 or clicks > 5:
            raise ValueError(f"Invalid clicks {clicks}, must be integer between 1 and 5")

        return {
            'x': x,
            'y': y,
            'button': button,
            'clicks': clicks
        }

    def validate_delay(self, delay: float, context: str = "operation") -> float:
        """
        Validate delay/timing parameters.

        Args:
            delay: Delay in seconds
            context: Description for error messages

        Returns:
            Validated delay value

        Raises:
            ValueError: If delay is invalid
        """
        if not isinstance(delay, (int, float)):
            raise ValueError(f"Delay must be number, got {type(delay)}")

        if delay < 0:
            raise ValueError(f"Delay cannot be negative, got {delay}")

        if delay > 30.0:
            self.logger.warning(f"Very long delay {delay}s for {context}")

        return float(delay)


class GameStateValidator:
    """
    Validates game state and provides game state checking utilities.

    This class handles validation of game window state, map loading,
    and other game-specific conditions.
    """

    def __init__(self):
        """Initialize game state validator."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = _get_config_manager()

    def validate_game_window(self) -> bool:
        """
        Validate that the BTD6 game window is active and available.

        Returns:
            True if window is valid and active

        Raises:
            WindowNotFoundError: If window cannot be found
            WindowActivationError: If window cannot be activated
        """
        try:
            # Import here to avoid circular imports
            from .game_launcher import activate_btd6_window

            if not activate_btd6_window():
                window_title = self.config_manager.get_setting('window_title') or "BloonsTD6"
                raise WindowNotFoundError(window_title, operation="game_window_validation")

            return True

        except Exception as e:
            if isinstance(e, (WindowNotFoundError, WindowActivationError)):
                raise
            window_title = self.config_manager.get_setting('window_title') or "BloonsTD6"
            raise WindowActivationError(
                window_title,
                details={"context": "game_window_validation", "original_exception": str(e)}
            ) from e

    def validate_map_loaded(self, expected_map: str = None) -> bool:
        """
        Validate that the expected map is loaded and ready.

        Args:
            expected_map: Name of expected map (uses config if None)

        Returns:
            True if map is loaded

        Raises:
            MapNotLoadedError: If map is not loaded
        """
        if expected_map is None:
            expected_map = self.config_manager.get_setting('selected_map')

        # This would need to be implemented with actual image recognition
        # For now, we'll use a placeholder that assumes map is loaded
        # after window activation and a delay
        try:
            import time
            time.sleep(2)  # Simulate map loading check

            # TODO: Implement actual map detection using image recognition
            self.logger.info(f"Assuming map '{expected_map}' is loaded")

            return True

        except Exception as e:
            raise MapNotLoadedError(expected_map, operation="map_validation") from e

    def validate_game_mode(self) -> bool:
        """
        Validate that the game is in the expected mode.

        Returns:
            True if game mode is correct

        Raises:
            GameStateError: If game mode is incorrect
        """
        expected_difficulty = self.config_manager.get_setting('selected_difficulty')
        expected_mode = self.config_manager.get_setting('selected_mode')

        # This would need to be implemented with actual game state detection
        # For now, we'll use a placeholder
        try:
            # TODO: Implement actual game mode detection
            self.logger.info(f"Assuming game mode is {expected_difficulty} - {expected_mode}")

            return True

        except Exception as e:
            raise GameStateError(
                f"Game mode validation failed: expected {expected_difficulty} - {expected_mode}",
                operation="game_mode_validation"
            ) from e


# Global validator instances
_coordinate_validator = None
_input_validator = None
_game_state_validator = None


def get_coordinate_validator() -> CoordinateValidator:
    """Get or create global coordinate validator instance."""
    global _coordinate_validator
    if _coordinate_validator is None:
        _coordinate_validator = CoordinateValidator()
    return _coordinate_validator


def get_input_validator() -> InputValidator:
    """Get or create global input validator instance."""
    global _input_validator
    if _input_validator is None:
        _input_validator = InputValidator()
    return _input_validator


def get_game_state_validator() -> GameStateValidator:
    """Get or create global game state validator instance."""
    global _game_state_validator
    if _game_state_validator is None:
        _game_state_validator = GameStateValidator()
    return _game_state_validator


def validate_coordinates(coordinates: Tuple[int, int], context: str = "operation") -> Tuple[int, int]:
    """
    Convenience function to validate coordinates.

    Args:
        coordinates: (x, y) coordinates to validate
        context: Description for error messages

    Returns:
        Validated coordinates
    """
    return get_coordinate_validator().validate_coordinates(coordinates, context)


def validate_key(key: str, context: str = "input") -> str:
    """
    Convenience function to validate key input.

    Args:
        key: Key to validate
        context: Description for error messages

    Returns:
        Validated key
    """
    return get_input_validator().validate_key(key, context)


def validate_game_window() -> bool:
    """
    Convenience function to validate game window state.

    Returns:
        True if window is valid
    """
    return get_game_state_validator().validate_game_window()


def validate_map_loaded(expected_map: str = None) -> bool:
    """
    Convenience function to validate map loading.

    Args:
        expected_map: Expected map name (uses config if None)

    Returns:
        True if map is loaded
    """
    return get_game_state_validator().validate_map_loaded(expected_map)
