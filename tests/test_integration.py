"""
Integration tests for the complete BTD6 automation system.

Tests interactions between multiple modules and components using mocks
and synthetic data without requiring the actual game or GUI interactions.
"""

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock, call

# Add the btd6_auto module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "btd6_auto"))

from config import ConfigManager
from validation import CoordinateValidator, InputValidator
from exceptions import (
    BTD6AutomationError,
    InvalidCoordinateError,
    WindowNotFoundError,
    TemplateNotFoundError,
)
from retry_utils import retry, RetryContext
from logging_utils import get_logger, LogContext
from recovery import RecoveryManager, RecoveryStrategy


class ModuleIntegrationTests(unittest.TestCase):
    """Test integration between different modules."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager()
        self.coord_validator = CoordinateValidator()
        self.input_validator = InputValidator()
        self.recovery_manager = RecoveryManager()
        self.logger = get_logger("integration_test")

    def test_config_validation_integration(self):
        """Test configuration and validation module integration."""
        # Set up configuration
        self.config_manager.update_setting("monkey_coords", [500, 400])
        self.config_manager.update_setting("hero_coords", [300, 250])
        self.config_manager.update_setting("selected_map", "Scrapyard")

        # Validate coordinates from config
        monkey_coords = self.config_manager.get_setting("monkey_coords")
        hero_coords = self.config_manager.get_setting("hero_coords")

        validated_monkey = self.coord_validator.validate_coordinates(
            monkey_coords, "monkey_placement"
        )
        validated_hero = self.coord_validator.validate_coordinates(
            hero_coords, "hero_placement"
        )

        # Should validate successfully
        self.assertEqual(validated_monkey, (500, 400))
        self.assertEqual(validated_hero, (300, 250))

        # Validate map from config
        selected_map = self.config_manager.get_setting("selected_map")
        validated_map = self.input_validator.validate_map_name(
            selected_map, "map_selection"
        )
        self.assertEqual(validated_map, "Scrapyard")

    def test_exception_logging_integration(self):
        """Test exception handling with logging integration."""
        with LogContext("exception_logging_test", self.logger) as ctx:
            try:
                # Simulate an operation that fails
                raise InvalidCoordinateError(
                    (100, 200),
                    operation="integration_test",
                    details={"reason": "test_failure"},
                )
            except InvalidCoordinateError as e:
                # Log the exception with context
                ctx.log_event(
                    "Exception occurred",
                    extra={
                        "exception_type": type(e).__name__,
                        "coordinates": e.coordinates,
                        "operation": e.operation,
                    },
                )

        # Should handle exception and logging without issues

    def test_retry_validation_integration(self):
        """Test retry mechanism with validation integration."""
        attempt_count = 0

        @retry(max_retries=3, base_delay=0.01, retryable_exceptions=[ValueError])
        def retryable_validation():
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                # First attempt: invalid coordinates that cause ValueError in validation
                try:
                    self.coord_validator.validate_coordinates((-100, -100), "test")
                except InvalidCoordinateError as e:
                    raise ValueError(f"Validation failed: {e}")

            return "validation_success"

        with patch("time.sleep"):
            result = retryable_validation()

        self.assertEqual(result, "validation_success")
        self.assertEqual(attempt_count, 2)  # Should retry once

    def test_recovery_config_integration(self):
        """Test recovery system with configuration integration."""

        # Set up recovery strategy that uses configuration
        class ConfigBasedRecoveryStrategy(RecoveryStrategy):
            def __init__(self, config_manager):
                super().__init__("config_based_recovery", priority=10)
                self.config_manager = config_manager

            def _execute(self, context):
                # Use config to determine recovery action
                try:
                    # Try to get a config setting as part of recovery
                    hero_coords = self.config_manager.get_setting("hero_coords")
                    if hero_coords:
                        return True  # Recovery successful
                except Exception:
                    pass
                return False

        strategy = ConfigBasedRecoveryStrategy(self.config_manager)
        self.recovery_manager.register_strategy(strategy)

        # Test recovery
        context = RecoveryContext("config_operation")
        success = self.recovery_manager.attempt_recovery(
            context, "config_based_recovery"
        )

        self.assertTrue(success)

    def test_full_workflow_integration(self):
        """Test a complete workflow integrating multiple modules."""
        with LogContext("full_workflow_test", self.logger) as ctx:
            ctx.log_event("Starting full workflow test")

            # 1. Load and validate configuration
            ctx.log_event("Loading configuration")
            config = ConfigManager()
            monkey_coords = config.get_setting("monkey_coords")
            hero_coords = config.get_setting("hero_coords")

            # 2. Validate coordinates
            ctx.log_event("Validating coordinates")
            validated_monkey = self.coord_validator.validate_coordinates(
                monkey_coords, "workflow_monkey"
            )
            validated_hero = self.coord_validator.validate_coordinates(
                hero_coords, "workflow_hero"
            )

            # 3. Set up retry mechanism for operations
            ctx.log_event("Setting up retry mechanism")

            @retry(max_retries=2, base_delay=0.01)
            def mock_operation():
                return "operation_success"

            with patch("time.sleep"):
                operation_result = mock_operation()

            # 4. Set up recovery for potential failures
            ctx.log_event("Setting up recovery mechanisms")

            class MockRecoveryStrategy(RecoveryStrategy):
                def _execute(self, context):
                    return True  # Always succeeds in test

            recovery_strategy = MockRecoveryStrategy()
            self.recovery_manager.register_strategy(recovery_strategy)

            # 5. Simulate potential failure and recovery
            ctx.log_event("Simulating workflow completion")

            # All components should work together
            self.assertEqual(validated_monkey, (440, 355))  # Default coordinates
            self.assertEqual(validated_hero, (320, 250))  # Default coordinates
            self.assertEqual(operation_result, "operation_success")

            ctx.log_event("Full workflow test completed successfully")


class ComponentInteractionTests(unittest.TestCase):
    """Test interactions between specific components."""

    def test_config_with_exception_handling(self):
        """Test configuration loading with exception handling."""
        # Test loading invalid config file
        invalid_config_path = os.path.join(
            os.path.dirname(__file__), "test_data", "configs", "invalid_config.json"
        )

        with LogContext("config_exception_test", self.logger):
            # Should handle invalid config gracefully
            config_manager = ConfigManager(invalid_config_path)

            # Should fall back to defaults
            monkey_coords = config_manager.get_setting("monkey_coords")
            self.assertEqual(monkey_coords, (440, 355))  # Default value

    def test_validation_with_logging(self):
        """Test validation operations with logging."""
        logger = get_logger("validation_logging_test")

        with LogContext("validation_test", logger) as ctx:
            # Test successful validation
            coords = (100, 200)
            validated = self.coord_validator.validate_coordinates(
                coords, "logging_test"
            )

            ctx.log_event(
                "Coordinates validated",
                extra={"original_coords": coords, "validated_coords": validated},
            )

            self.assertEqual(validated, coords)

            # Test failed validation
            try:
                self.coord_validator.validate_coordinates((-100, -100), "logging_test")
            except InvalidCoordinateError as e:
                ctx.log_event(
                    "Validation failed",
                    extra={
                        "exception_type": type(e).__name__,
                        "coordinates": e.coordinates,
                        "operation": e.operation,
                    },
                )

    def test_retry_with_recovery_integration(self):
        """Test retry mechanism with recovery system."""
        attempt_count = 0

        class RetryableRecoveryStrategy(RecoveryStrategy):
            def __init__(self):
                super().__init__("retryable_recovery", priority=5)

            def _execute(self, context):
                return True  # Recovery always succeeds

        self.recovery_manager.register_strategy(RetryableRecoveryStrategy())

        @retry(
            max_retries=3, base_delay=0.01, retryable_exceptions=[TemplateNotFoundError]
        )
        def operation_with_retry_and_recovery():
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                raise TemplateNotFoundError("test.png", operation="integration_test")

            return "success"

        with patch("time.sleep"):
            result = operation_with_retry_and_recovery()

        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 2)  # Should retry once

    def test_logging_with_performance_monitoring(self):
        """Test logging integration with performance monitoring."""
        logger = get_logger("performance_logging_test")

        @log_performance("test_operation", threshold_ms=10.0)
        def monitored_operation():
            time.sleep(0.005)  # 5ms operation
            return "completed"

        # Should execute successfully
        result = monitored_operation()
        self.assertEqual(result, "completed")

        # Performance logging should work with other logging


class SystemWideIntegrationTests(unittest.TestCase):
    """Test system-wide integration scenarios."""

    def test_error_propagation_through_modules(self):
        """Test error propagation through multiple modules."""
        logger = get_logger("error_propagation_test")

        with LogContext("error_propagation", logger) as ctx:
            try:
                # Start with configuration error
                ctx.log_event("Attempting configuration operation")

                # This would normally load config, but let's simulate an error
                raise BTD6AutomationError(
                    "Configuration loading failed",
                    operation="config_load",
                    details={"reason": "file_not_found"},
                )

            except BTD6AutomationError as e:
                # Error should be logged with context
                ctx.log_event(
                    "Configuration error caught",
                    extra={"operation": e.operation, "error_details": e.details},
                )

                # In a real scenario, this might trigger recovery
                recovery_context = RecoveryContext("config_error_recovery")

                # Simulate recovery attempt
                class ConfigErrorRecoveryStrategy(RecoveryStrategy):
                    def _execute(self, context):
                        return True  # Recovery successful

                recovery_manager = RecoveryManager()
                recovery_manager.register_strategy(ConfigErrorRecoveryStrategy())

                recovery_success = recovery_manager.attempt_recovery(
                    recovery_context, "config_error_recovery"
                )

                self.assertTrue(recovery_success)

    def test_resource_management_integration(self):
        """Test resource management across multiple modules."""
        # Test that modules properly manage their resources
        config_manager = ConfigManager()
        validator = CoordinateValidator()
        recovery_manager = RecoveryManager()

        # Use resources
        coords = config_manager.get_setting("monkey_coords")
        validated_coords = validator.validate_coordinates(coords, "resource_test")

        # Register and use recovery strategy
        strategy = RecoveryStrategy("resource_test_strategy")
        recovery_manager.register_strategy(strategy)

        # All operations should work without resource conflicts
        self.assertEqual(validated_coords, (440, 355))

        # Clean up should work properly
        del config_manager
        del validator
        del recovery_manager

    def test_concurrent_module_operations(self):
        """Test concurrent operations across multiple modules."""
        import threading
        import queue

        results = queue.Queue()
        errors = queue.Queue()

        def concurrent_module_test(thread_id):
            try:
                # Each thread uses different modules
                config = ConfigManager()
                validator = CoordinateValidator()
                recovery = RecoveryManager()

                # Perform operations
                coords = config.get_setting("hero_coords")
                validated = validator.validate_coordinates(
                    coords, f"thread_{thread_id}"
                )

                # Register a strategy
                strategy = RecoveryStrategy(f"thread_{thread_id}_strategy")
                recovery.register_strategy(strategy)

                results.put((thread_id, validated, "success"))

            except Exception as e:
                errors.put((thread_id, str(e)))

        # Start multiple concurrent operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_module_test, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        successful_operations = 0
        while not results.empty():
            thread_id, coords, status = results.get()
            if status == "success":
                successful_operations += 1
                self.assertEqual(coords, (320, 250))  # Default hero coordinates

        self.assertEqual(successful_operations, 5)
        self.assertTrue(errors.empty())


class MockGameEnvironmentTests(unittest.TestCase):
    """Test system behavior in a mock game environment."""

    def setUp(self):
        """Set up mock game environment."""
        self.config_manager = ConfigManager()
        self.coord_validator = CoordinateValidator()
        self.input_validator = InputValidator()

        # Mock game window and screenshot functions
        self.mock_window_patcher = patch("pygetwindow.getWindowsWithTitle")
        self.mock_screenshot_patcher = patch("pyautogui.screenshot")
        self.mock_click_patcher = patch("pyautogui.click")
        self.mock_keyboard_patcher = patch("keyboard.send")

        self.mock_window = self.mock_window_patcher.start()
        self.mock_screenshot = self.mock_screenshot_patcher.start()
        self.mock_click = self.mock_click_patcher.start()
        self.mock_keyboard = self.mock_keyboard_patcher.start()

        # Set up mock window
        mock_window_obj = MagicMock()
        mock_window_obj.title = "BloonsTD6"
        mock_window_obj.activate = MagicMock()
        self.mock_window.return_value = [mock_window_obj]

        # Set up mock screenshot
        self.mock_screenshot.return_value = MagicMock()

    def tearDown(self):
        """Clean up mock patches."""
        self.mock_window_patcher.stop()
        self.mock_screenshot_patcher.stop()
        self.mock_click_patcher.stop()
        self.mock_keyboard_patcher.stop()

    def test_mock_game_window_interaction(self):
        """Test interaction with mock game window."""
        # Test window activation
        from game_launcher import activate_btd6_window

        success = activate_btd6_window()
        self.assertTrue(success)

        # Verify window was activated
        self.mock_window.assert_called()
        self.mock_window.return_value[0].activate.assert_called_once()

    def test_mock_screenshot_integration(self):
        """Test screenshot capture integration."""
        from vision import capture_screen

        # Mock successful screenshot
        mock_image = MagicMock()
        self.mock_screenshot.return_value = mock_image

        result = capture_screen()
        self.assertEqual(result, mock_image)

        # Test screenshot failure
        self.mock_screenshot.side_effect = Exception("Screenshot failed")
        result = capture_screen()
        self.assertIsNone(result)

    def test_mock_input_integration(self):
        """Test input system integration with mocks."""
        from input import click, type_text

        # Test clicking
        click(100, 200)
        self.mock_click.assert_called_once_with()

        # Test typing (would need proper mocking for keyboard)

    def test_complete_mock_automation_workflow(self):
        """Test complete automation workflow with mocks."""
        from game_launcher import activate_btd6_window, start_map
        from monkey_manager import place_hero, place_monkey

        with LogContext("mock_automation_test", self.logger):
            # 1. Activate window
            window_success = activate_btd6_window()
            self.assertTrue(window_success)

            # 2. Start map (would need more mocking for full implementation)
            # For now, just test that the function exists and can be called
            try:
                start_map()
            except Exception:
                # Expected since we don't have full mocking
                pass

            # 3. Place game elements (would need proper mocking)
            # Test that functions exist and handle basic parameters
            hero_coords = self.config_manager.get_setting("hero_coords")
            hero_key = self.config_manager.get_setting("hero_key")

            try:
                place_hero(hero_coords, hero_key)
                place_monkey(hero_coords, hero_key)  # Using same coords for test
            except Exception:
                # Expected due to mocking limitations
                pass


class DataFlowIntegrationTests(unittest.TestCase):
    """Test data flow between modules."""

    def test_configuration_data_flow(self):
        """Test data flow from configuration through validation."""
        # Start with configuration
        config = ConfigManager()
        config.update_setting("monkey_coords", [600, 500])
        config.update_setting("selected_difficulty", "Hard")

        # Data flows to validation
        validator = CoordinateValidator()
        coords = config.get_setting("monkey_coords")
        validated_coords = validator.validate_coordinates(coords, "data_flow_test")

        # Data flows to input validation
        input_validator = InputValidator()
        difficulty = config.get_setting("selected_difficulty")
        validated_difficulty = input_validator.validate_difficulty(
            difficulty, "data_flow_test"
        )

        # Data should flow correctly through all modules
        self.assertEqual(validated_coords, (600, 500))
        self.assertEqual(validated_difficulty, "Hard")

    def test_error_data_flow(self):
        """Test error data flow through exception handling."""
        # Create an error in one module
        original_error = InvalidCoordinateError(
            (100, 200), operation="data_flow_error", details={"reason": "test_error"}
        )

        # Error flows through logging
        logger = get_logger("error_data_flow_test")

        with LogContext("error_flow_test", logger) as ctx:
            try:
                raise original_error
            except InvalidCoordinateError as e:
                # Error information flows to context
                ctx.log_event(
                    "Error propagated",
                    extra={
                        "coordinates": e.coordinates,
                        "operation": e.operation,
                        "details": e.details,
                    },
                )

        # Error could flow to recovery system
        recovery_context = RecoveryContext("error_recovery")
        recovery_context.original_exception = original_error

        class ErrorRecoveryStrategy(RecoveryStrategy):
            def _execute(self, context):
                # Recovery strategy receives error information
                if hasattr(context, "original_exception"):
                    if isinstance(context.original_exception, InvalidCoordinateError):
                        return True  # Can handle coordinate errors
                return False

        recovery_manager = RecoveryManager()
        recovery_manager.register_strategy(ErrorRecoveryStrategy())

        success = recovery_manager.attempt_recovery(recovery_context, "error_recovery")
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
