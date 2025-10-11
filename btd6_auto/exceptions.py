"""
Custom exception classes for BTD6 automation errors.

This module defines a hierarchy of exceptions specific to BTD6 automation,
providing better error categorization and handling capabilities.
"""


class BTD6AutomationError(Exception):
    """
    Base exception class for all BTD6 automation errors.

    This serves as the root exception for all automation-specific errors,
    allowing for easy catching of any automation-related issues.
    """

    def __init__(self, message: str, operation: str = None, details: dict = None):
        """
        Initialize BTD6 automation error.

        Args:
            message: Human-readable error description
            operation: Name of the operation that failed
            details: Additional context information about the error
        """
        self.operation = operation
        self.details = details or {}
        if operation:
            full_message = f"[{operation}] {message}"
        else:
            full_message = message
        super().__init__(full_message)


class WindowError(BTD6AutomationError):
    """
    Exception raised when window-related operations fail.

    This includes errors with finding, activating, or interacting
    with the BTD6 game window.
    """

    def __init__(self, message: str, window_title: str = None, **kwargs):
        """
        Initialize window error.

        Args:
            message: Error description
            window_title: Title of the window that caused the error
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.window_title = window_title


class WindowNotFoundError(WindowError):
    """
    Exception raised when the BTD6 game window cannot be found.

    This typically occurs when the game is not running or the
    window title doesn't match the expected pattern.
    """

    def __init__(self, window_title: str = "BloonsTD6", **kwargs):
        message = f"Game window '{window_title}' not found. Please ensure BTD6 is running."
        super().__init__(message, window_title=window_title, operation="window_detection", **kwargs)


class WindowActivationError(WindowError):
    """
    Exception raised when the BTD6 game window cannot be activated.

    This occurs when the window is found but cannot be brought to foreground
    or made the active window.
    """

    def __init__(self, window_title: str = "BloonsTD6", **kwargs):
        message = f"Failed to activate game window '{window_title}'."
        super().__init__(message, window_title=window_title, operation="window_activation", **kwargs)


class ImageMatchError(BTD6AutomationError):
    """
    Exception raised when image matching operations fail.

    This includes errors with template images, screenshot capture,
    or template matching algorithms.
    """

    def __init__(self, message: str, template_path: str = None, confidence: float = None, **kwargs):
        """
        Initialize image match error.

        Args:
            message: Error description
            template_path: Path to the template image that failed
            confidence: Confidence score if matching was attempted
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.template_path = template_path
        self.confidence = confidence


class TemplateNotFoundError(ImageMatchError):
    """
    Exception raised when a template image file cannot be found.

    This occurs when the specified template image doesn't exist
    at the expected path.
    """

    def __init__(self, template_path: str, **kwargs):
        message = f"Template image not found: {template_path}"
        super().__init__(message, template_path=template_path, operation="template_loading", **kwargs)


class MatchFailedError(ImageMatchError):
    """
    Exception raised when image matching fails to find the target.

    This occurs when template matching runs successfully but doesn't
    find the target image within acceptable confidence thresholds.
    """

    def __init__(self, template_path: str, confidence: float = None, threshold: float = 0.8, **kwargs):
        if confidence is not None:
            message = f"Image match failed for {template_path}: confidence {confidence:.3f} < threshold {threshold:.3f}"
        else:
            message = f"Image match failed for {template_path}: no match found"
        super().__init__(message, template_path=template_path, confidence=confidence,
                        operation="image_matching", **kwargs)
        self.threshold = threshold


class ScreenshotError(ImageMatchError):
    """
    Exception raised when screenshot capture fails.

    This occurs when the system cannot capture screenshots,
    usually due to permission issues or display problems.
    """

    def __init__(self, region: tuple = None, **kwargs):
        if region:
            message = f"Failed to capture screenshot of region {region}"
        else:
            message = "Failed to capture screenshot"
        super().__init__(message, operation="screenshot_capture", **kwargs)
        self.region = region


class GameStateError(BTD6AutomationError):
    """
    Exception raised when game state validation fails.

    This includes errors where the game is in an unexpected state
    or required game elements are not present.
    """

    def __init__(self, message: str, expected_state: str = None, current_state: str = None, **kwargs):
        """
        Initialize game state error.

        Args:
            message: Error description
            expected_state: What state was expected
            current_state: What state was actually detected
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.expected_state = expected_state
        self.current_state = current_state


class MapNotLoadedError(GameStateError):
    """
    Exception raised when the expected map is not loaded.

    This occurs when the bot tries to interact with game elements
    before the map has finished loading.
    """

    def __init__(self, expected_map: str = None, **kwargs):
        if expected_map:
            message = f"Map '{expected_map}' not loaded or not ready"
        else:
            message = "Map not loaded or not ready"
        super().__init__(message, expected_state="map_loaded", **kwargs)
        self.expected_map = expected_map


class GameNotStartedError(GameStateError):
    """
    Exception raised when the game appears not to be started.

    This occurs when the bot cannot find expected game UI elements
    that should be present in a running game.
    """

    def __init__(self, **kwargs):
        message = "Game does not appear to be started or is in an invalid state"
        super().__init__(message, expected_state="game_started", **kwargs)


class InputError(BTD6AutomationError):
    """
    Exception raised when input automation operations fail.

    This includes errors with mouse clicks, keyboard input,
    or other automation actions.
    """

    def __init__(self, message: str, coordinates: tuple = None, key: str = None, **kwargs):
        """
        Initialize input error.

        Args:
            message: Error description
            coordinates: Coordinates where click was attempted
            key: Key that was pressed
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.coordinates = coordinates
        self.key = key


class ClickFailedError(InputError):
    """
    Exception raised when a mouse click operation fails.

    This occurs when the bot cannot perform a mouse click at
    the specified coordinates.
    """

    def __init__(self, coordinates: tuple, **kwargs):
        message = f"Mouse click failed at coordinates {coordinates}"
        super().__init__(message, coordinates=coordinates, operation="mouse_click", **kwargs)


class KeyPressFailedError(InputError):
    """
    Exception raised when a keyboard input operation fails.

    This occurs when the bot cannot send keyboard input to
    the target application.
    """

    def __init__(self, key: str, **kwargs):
        message = f"Key press failed for key '{key}'"
        super().__init__(message, key=key, operation="key_press", **kwargs)


class ConfigurationError(BTD6AutomationError):
    """
    Exception raised when configuration validation fails.

    This includes errors with invalid configuration values,
    missing required settings, or type mismatches.
    """

    def __init__(self, message: str, setting_name: str = None, setting_value: any = None, **kwargs):
        """
        Initialize configuration error.

        Args:
            message: Error description
            setting_name: Name of the invalid setting
            setting_value: Value that caused the error
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.setting_name = setting_name
        self.setting_value = setting_value


class InvalidCoordinateError(ConfigurationError):
    """
    Exception raised when coordinate values are invalid.

    This occurs when coordinates are not tuples, contain non-integers,
    or have negative values.
    """

    def __init__(self, coordinates: tuple, **kwargs):
        message = f"Invalid coordinates {coordinates}: must be (x, y) tuple with non-negative integers"
        super().__init__(message, setting_value=coordinates, **kwargs)


class InvalidKeyError(ConfigurationError):
    """
    Exception raised when keyboard key values are invalid.

    This occurs when keys are not single characters or contain
    invalid characters.
    """

    def __init__(self, key: str, **kwargs):
        message = f"Invalid key '{key}': must be a single character"
        super().__init__(message, setting_name="key", setting_value=key, **kwargs)


class AutomationTimeoutError(BTD6AutomationError):
    """
    Exception raised when an operation times out.

    This occurs when an operation takes longer than the configured
    timeout period to complete.
    """

    def __init__(self, message: str, timeout_seconds: float = None, **kwargs):
        """
        Initialize timeout error.

        Args:
            message: Error description
            timeout_seconds: How long the operation was allowed to run
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds


class OperationTimeoutError(AutomationTimeoutError):
    """
    Exception raised when a specific operation exceeds its timeout.

    This is a more specific timeout error for individual operations
    rather than overall automation timeouts.
    """

    def __init__(self, operation: str, timeout_seconds: float, **kwargs):
        message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        super().__init__(message, timeout_seconds=timeout_seconds, operation=operation, **kwargs)


class RetryExhaustedError(BTD6AutomationError):
    """
    Exception raised when all retry attempts for an operation are exhausted.

    This occurs when an operation fails repeatedly despite retry attempts,
    indicating a persistent problem that requires manual intervention.
    """

    def __init__(self, message: str, attempts: int, last_error: Exception = None, **kwargs):
        """
        Initialize retry exhausted error.

        Args:
            message: Error description
            attempts: Number of retry attempts made
            last_error: The last exception that caused the failure
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, **kwargs)
        self.attempts = attempts
        self.last_error = last_error
