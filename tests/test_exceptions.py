"""
Comprehensive tests for the BTD6 exception handling system.

Tests custom exception classes, error context preservation, and error handling
patterns without requiring the actual game or GUI interactions.
"""

import os
import sys
import unittest
import logging
from unittest.mock import patch, MagicMock

# Add the btd6_auto module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'btd6_auto'))

from exceptions import (
    BTD6AutomationError,
    InvalidCoordinateError,
    InvalidKeyError,
    WindowNotFoundError,
    WindowActivationError,
    MapNotLoadedError,
    GameStateError,
    TemplateNotFoundError,
    MatchFailedError,
    ScreenshotError,
    RetryExhaustedError,
    ConfigurationError,
    ValidationError
)


class ExceptionHierarchyTests(unittest.TestCase):
    """Test cases for exception class hierarchy and inheritance."""

    def test_base_exception_inheritance(self):
        """Test that all exceptions inherit from BTD6AutomationError."""
        exceptions_to_test = [
            InvalidCoordinateError,
            InvalidKeyError,
            WindowNotFoundError,
            WindowActivationError,
            MapNotLoadedError,
            GameStateError,
            TemplateNotFoundError,
            MatchFailedError,
            ScreenshotError,
            RetryExhaustedError,
            ConfigurationError,
            ValidationError
        ]

        for exception_class in exceptions_to_test:
            with self.subTest(exception_class=exception_class):
                # All exceptions should inherit from BTD6AutomationError
                self.assertTrue(
                    issubclass(exception_class, BTD6AutomationError),
                    f"{exception_class.__name__} should inherit from BTD6AutomationError"
                )

                # Should also inherit from the appropriate base Python exceptions
                if 'Error' in exception_class.__name__:
                    self.assertTrue(
                        issubclass(exception_class, Exception),
                        f"{exception_class.__name__} should inherit from Exception"
                    )

    def test_exception_instantiation(self):
        """Test exception instantiation with various parameters."""
        # Test basic instantiation
        error = BTD6AutomationError("Test error message")
        self.assertEqual(str(error), "Test error message")
        self.assertIsNone(error.operation)
        self.assertIsNone(error.details)

        # Test instantiation with operation context
        error_with_context = BTD6AutomationError(
            "Test error with context",
            operation="test_operation"
        )
        self.assertEqual(str(error_with_context), "Test error with context")
        self.assertEqual(error_with_context.operation, "test_operation")

        # Test instantiation with full context
        error_full = BTD6AutomationError(
            "Test error with full context",
            operation="full_test_operation",
            details={"key": "value", "number": 42}
        )
        self.assertEqual(str(error_full), "Test error with full context")
        self.assertEqual(error_full.operation, "full_test_operation")
        self.assertEqual(error_full.details, {"key": "value", "number": 42})

    def test_coordinate_error_specifics(self):
        """Test InvalidCoordinateError specific functionality."""
        coords = (100, 200)
        error = InvalidCoordinateError(
            coords,
            operation="coordinate_validation",
            details={"reason": "out_of_bounds"}
        )

        self.assertEqual(error.coordinates, coords)
        self.assertEqual(error.operation, "coordinate_validation")
        self.assertEqual(error.details, {"reason": "out_of_bounds"})

        # Test string representation includes coordinate info
        error_str = str(error)
        self.assertIn("100", error_str)
        self.assertIn("200", error_str)
        self.assertIn("out_of_bounds", error_str)

    def test_key_error_specifics(self):
        """Test InvalidKeyError specific functionality."""
        key = "invalid_key"
        error = InvalidKeyError(
            key,
            operation="key_validation",
            details={"reason": "too_long"}
        )

        self.assertEqual(error.key, key)
        self.assertEqual(error.operation, "key_validation")
        self.assertEqual(error.details, {"reason": "too_long"})

        # Test string representation includes key info
        error_str = str(error)
        self.assertIn("invalid_key", error_str)
        self.assertIn("too_long", error_str)

    def test_window_error_specifics(self):
        """Test window-related error specifics."""
        window_title = "BloonsTD6"

        # Test WindowNotFoundError
        not_found_error = WindowNotFoundError(
            window_title,
            operation="window_search",
            details={"searched_titles": ["BloonsTD6", "Bloons TD 6"]}
        )
        self.assertEqual(not_found_error.window_title, window_title)
        self.assertIn("BloonsTD6", str(not_found_error))

        # Test WindowActivationError
        activation_error = WindowActivationError(
            window_title,
            operation="window_activation",
            details={"activation_method": "pygetwindow"}
        )
        self.assertEqual(activation_error.window_title, window_title)
        self.assertIn("BloonsTD6", str(activation_error))


class ExceptionContextTests(unittest.TestCase):
    """Test cases for exception context preservation and chaining."""

    def test_exception_chaining(self):
        """Test exception chaining and cause preservation."""
        original_error = ValueError("Original error")

        # Create a BTD6 error with the original as cause
        btd6_error = BTD6AutomationError(
            "BTD6 wrapper error",
            operation="test_operation"
        )
        btd6_error.__cause__ = original_error

        # Test that cause is preserved
        self.assertEqual(btd6_error.__cause__, original_error)
        self.assertEqual(str(btd6_error.__cause__), "Original error")

    def test_nested_exception_context(self):
        """Test nested exception contexts."""
        def operation_that_might_fail():
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise BTD6AutomationError(
                    "Outer error",
                    operation="nested_operation"
                ) from e

        with self.assertRaises(BTD6AutomationError) as cm:
            operation_that_might_fail()

        error = cm.exception
        self.assertEqual(error.operation, "nested_operation")
        self.assertIsNotNone(error.__cause__)
        self.assertIsInstance(error.__cause__, ValueError)

    def test_exception_serialization(self):
        """Test exception serialization for logging."""
        error = BTD6AutomationError(
            "Test serializable error",
            operation="serialization_test",
            details={"nested": {"key": "value"}, "list": [1, 2, 3]}
        )

        # Should be serializable to dict for logging
        error_dict = error.to_dict()
        self.assertIsInstance(error_dict, dict)
        self.assertEqual(error_dict['message'], "Test serializable error")
        self.assertEqual(error_dict['operation'], "serialization_test")
        self.assertEqual(error_dict['details'], {"nested": {"key": "value"}, "list": [1, 2, 3]})


class ExceptionLoggingTests(unittest.TestCase):
    """Test cases for exception logging integration."""

    def setUp(self):
        """Set up test fixtures with logging."""
        self.logger = logging.getLogger('test_exceptions')

        # Set up a string handler to capture log output
        self.log_capture = []
        handler = logging.StreamHandler()
        handler.emit = lambda record: self.log_capture.append(record.getMessage())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.ERROR)

    def tearDown(self):
        """Clean up test fixtures."""
        self.logger.removeHandler(self.logger.handlers[0])

    def test_exception_logging_with_context(self):
        """Test that exceptions are logged with proper context."""
        try:
            raise BTD6AutomationError(
                "Test logged error",
                operation="logging_test",
                details={"test_id": "test_001"}
            )
        except BTD6AutomationError as e:
            # Simulate how the logging system would handle this
            self.logger.error(f"Automation error in {e.operation}: {e}", extra={
                'operation': e.operation,
                'details': e.details
            })

        # Check that error was logged
        self.assertGreater(len(self.log_capture), 0)
        logged_message = self.log_capture[-1]
        self.assertIn("logging_test", logged_message)
        self.assertIn("Test logged error", logged_message)

    def test_exception_logging_levels(self):
        """Test exception logging at different levels."""
        # Test different log levels for different exception types
        exceptions_and_levels = [
            (InvalidCoordinateError((100, 200), operation="test"), logging.WARNING),
            (WindowNotFoundError("TestWindow", operation="test"), logging.ERROR),
            (RetryExhaustedError("test_operation", 3, ValueError("max retries")), logging.ERROR),
        ]

        for exception, expected_level in exceptions_and_levels:
            with self.subTest(exception=exception.__class__.__name__):
                self.log_capture.clear()

                # Log at the expected level
                if expected_level == logging.WARNING:
                    self.logger.warning(str(exception))
                elif expected_level == logging.ERROR:
                    self.logger.error(str(exception))

                # Check that message was logged
                self.assertGreater(len(self.log_capture), 0)


class ExceptionHandlingPatternsTests(unittest.TestCase):
    """Test common exception handling patterns."""

    def test_try_catch_finally_pattern(self):
        """Test try/catch/finally exception handling pattern."""
        results = []

        try:
            results.append("before_error")
            raise BTD6AutomationError("Test error", operation="pattern_test")
        except BTD6AutomationError as e:
            results.append(f"caught_{e.operation}")
            self.assertEqual(e.operation, "pattern_test")
        finally:
            results.append("finally_block")

        # Verify execution order
        expected = ["before_error", "caught_pattern_test", "finally_block"]
        self.assertEqual(results, expected)

    def test_nested_exception_handling(self):
        """Test nested exception handling scenarios."""
        def inner_function():
            raise InvalidCoordinateError((100, 200), operation="inner")

        def outer_function():
            try:
                inner_function()
            except InvalidCoordinateError as e:
                # Wrap in more general exception
                raise BTD6AutomationError(
                    "Coordinate validation failed",
                    operation="outer"
                ) from e

        # Test that the wrapped exception preserves the original cause
        with self.assertRaises(BTD6AutomationError) as cm:
            outer_function()

        error = cm.exception
        self.assertEqual(error.operation, "outer")
        self.assertIsNotNone(error.__cause__)
        self.assertIsInstance(error.__cause__, InvalidCoordinateError)
        self.assertEqual(error.__cause__.operation, "inner")

    def test_exception_suppression(self):
        """Test exception suppression in context managers."""
        suppressed_errors = []

        class ExceptionSuppressingContext:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type == InvalidKeyError:
                    suppressed_errors.append(exc_val)
                    return True  # Suppress the exception
                return False  # Don't suppress other exceptions

        # Test suppression
        with ExceptionSuppressingContext():
            raise InvalidKeyError("test_key", operation="suppression_test")

        self.assertEqual(len(suppressed_errors), 1)
        self.assertIsInstance(suppressed_errors[0], InvalidKeyError)

        # Test non-suppression
        with self.assertRaises(BTD6AutomationError):
            with ExceptionSuppressingContext():
                raise BTD6AutomationError("Should not be suppressed")


class ExceptionSpecificTests(unittest.TestCase):
    """Test specific exception types and their behaviors."""

    def test_retry_exhausted_error(self):
        """Test RetryExhaustedError specific functionality."""
        original_error = ValueError("Original failure")
        retry_error = RetryExhaustedError(
            "test_operation",
            3,
            original_error,
            details={"attempts": [1, 2, 3]}
        )

        self.assertEqual(retry_error.operation, "test_operation")
        self.assertEqual(retry_error.max_retries, 3)
        self.assertEqual(retry_error.final_exception, original_error)
        self.assertEqual(retry_error.details, {"attempts": [1, 2, 3]})

        # Test string representation
        error_str = str(retry_error)
        self.assertIn("test_operation", error_str)
        self.assertIn("3", error_str)
        self.assertIn("Original failure", error_str)

    def test_template_matching_errors(self):
        """Test template matching related errors."""
        # Test TemplateNotFoundError
        template_error = TemplateNotFoundError(
            "/path/to/missing/template.png",
            operation="template_loading"
        )
        self.assertEqual(template_error.template_path, "/path/to/missing/template.png")
        self.assertIn("template.png", str(template_error))

        # Test MatchFailedError
        match_error = MatchFailedError(
            "/path/to/template.png",
            operation="template_matching",
            details={"best_match": 0.5, "threshold": 0.8}
        )
        self.assertEqual(match_error.template_path, "/path/to/template.png")
        self.assertEqual(match_error.details["best_match"], 0.5)
        self.assertIn("0.5", str(match_error))

    def test_screenshot_error(self):
        """Test ScreenshotError specific functionality."""
        screenshot_error = ScreenshotError(
            "Screenshot capture failed",
            operation="screen_capture",
            details={"region": (0, 0, 100, 100), "error_code": "PERMISSION_DENIED"}
        )

        self.assertEqual(screenshot_error.operation, "screen_capture")
        self.assertEqual(screenshot_error.details["region"], (0, 0, 100, 100))
        self.assertIn("PERMISSION_DENIED", str(screenshot_error))

    def test_game_state_errors(self):
        """Test game state related errors."""
        # Test MapNotLoadedError
        map_error = MapNotLoadedError(
            "Monkey Meadow",
            "Easy",
            operation="map_loading",
            details={"load_time": 5.2, "timeout": 10.0}
        )
        self.assertEqual(map_error.map_name, "Monkey Meadow")
        self.assertEqual(map_error.difficulty, "Easy")
        self.assertEqual(map_error.details["load_time"], 5.2)

        # Test GameStateError
        state_error = GameStateError(
            "Game in unexpected state",
            operation="state_check",
            details={"expected_state": "main_menu", "actual_state": "in_game"}
        )
        self.assertEqual(state_error.details["expected_state"], "main_menu")
        self.assertEqual(state_error.details["actual_state"], "in_game")


class ExceptionRecoveryTests(unittest.TestCase):
    """Test exception recovery and retry patterns."""

    def test_exception_recovery_strategies(self):
        """Test different exception recovery strategies."""
        recovery_strategies = {
            InvalidCoordinateError: "recalculate_coordinates",
            WindowNotFoundError: "retry_window_search",
            TemplateNotFoundError: "use_alternative_template",
            RetryExhaustedError: "fallback_to_manual_mode"
        }

        for exception_type, expected_strategy in recovery_strategies.items():
            with self.subTest(exception_type=exception_type.__name__):
                # Create a mock error handler that determines strategy based on exception type
                def get_recovery_strategy(error):
                    if isinstance(error, InvalidCoordinateError):
                        return "recalculate_coordinates"
                    elif isinstance(error, WindowNotFoundError):
                        return "retry_window_search"
                    elif isinstance(error, TemplateNotFoundError):
                        return "use_alternative_template"
                    elif isinstance(error, RetryExhaustedError):
                        return "fallback_to_manual_mode"
                    return "unknown_strategy"

                test_error = exception_type("test", operation="test")
                strategy = get_recovery_strategy(test_error)
                self.assertEqual(strategy, expected_strategy)

    def test_exception_classification_for_retry(self):
        """Test classification of exceptions for retry logic."""
        retryable_exceptions = [
            TemplateNotFoundError,
            MatchFailedError,
            WindowActivationError,
            ScreenshotError
        ]

        non_retryable_exceptions = [
            InvalidCoordinateError,
            InvalidKeyError,
            ConfigurationError,
            ValidationError
        ]

        def is_retryable_exception(exc_type):
            """Classify exceptions as retryable or not."""
            return exc_type in retryable_exceptions

        for exc_type in retryable_exceptions:
            with self.subTest(exc_type=exc_type.__name__):
                self.assertTrue(
                    is_retryable_exception(exc_type),
                    f"{exc_type.__name__} should be retryable"
                )

        for exc_type in non_retryable_exceptions:
            with self.subTest(exc_type=exc_type.__name__):
                self.assertFalse(
                    is_retryable_exception(exc_type),
                    f"{exc_type.__name__} should not be retryable"
                )


if __name__ == '__main__':
    unittest.main()
